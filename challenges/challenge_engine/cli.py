"""Command-line interface for the CAPTCHA Challenge Engine."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

from challenge_engine.core.config import PROJECT_ROOT, load_level_config
from challenge_engine.core.exporter import (
    ChallengeBundle,
    export_challenge_bundle,
    write_benchmark_manifest,
)
from challenge_engine.core.schemas import (
    ALL_LEVEL_KEYS,
    LEVEL_1_KEY,
    LEVEL_2A_KEY,
    LEVEL_2B_KEY,
    LEVEL_3A_KEY,
    LEVEL_3B_KEY,
    normalize_level_key,
)
from challenge_engine.core.validation import validate_generated_directory
from challenge_engine.datasets.bdd100k import (
    BDD100KDataSplitError,
    BDD100KNotFoundError,
    inspect_bdd100k_status,
)
from challenge_engine.levels.level_1.generator import Level1StreetGridGenerator
from challenge_engine.levels.level_2a.generator import Level2AHardStreetGridGenerator
from challenge_engine.levels.level_2b.generator import (
    Level2BAssetNotFoundError,
    Level2BCheckerShadowGenerator,
    inspect_level_2b_asset_status,
)
from challenge_engine.levels.level_3a.generator import Level3ARoutingGenerator
from challenge_engine.levels.level_3b.generator import Level3BDegradedVisionGenerator


def _create_generator(level_key: str, config: Any) -> Any:
    if level_key == LEVEL_1_KEY:
        return Level1StreetGridGenerator(config)
    if level_key == LEVEL_2A_KEY:
        return Level2AHardStreetGridGenerator(config)
    if level_key == LEVEL_2B_KEY:
        return Level2BCheckerShadowGenerator(config)
    if level_key == LEVEL_3A_KEY:
        return Level3ARoutingGenerator(config)
    if level_key == LEVEL_3B_KEY:
        return Level3BDegradedVisionGenerator(config)
    raise ValueError(f"Unsupported level key: {level_key}")


def _cmd_generate(args: argparse.Namespace) -> int:
    raw_level: str = args.level
    is_all = raw_level.strip().lower() == "all"
    if is_all:
        target_levels = list(ALL_LEVEL_KEYS)
    else:
        target_levels = [normalize_level_key(raw_level)]

    out_dir = Path(args.output)
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    overrides: dict[str, Any] = {}
    if args.difficulty is not None:
        overrides["difficulty"] = args.difficulty
    if getattr(args, "subtype", None) is not None:
        overrides["subtype"] = args.subtype
    if args.resolution is not None:
        overrides["resolution"] = args.resolution
    if args.resolutions is not None:
        res_list = [int(x.strip()) for x in args.resolutions.split(",") if x.strip()]
        overrides["batchResolutions"] = res_list
    if args.bdd100k_root is not None:
        overrides["bdd100kRoot"] = args.bdd100k_root

    total_exported = 0
    exported_bdd100k = False
    missing_errors: list[str] = []

    for level_key in target_levels:
        level_overrides = dict(overrides)
        if level_key != LEVEL_3B_KEY:
            level_overrides.pop("resolution", None)
            level_overrides.pop("batchResolutions", None)
        if level_key not in {LEVEL_1_KEY, LEVEL_2A_KEY, LEVEL_3B_KEY}:
            level_overrides.pop("bdd100kRoot", None)
        if level_key != LEVEL_3A_KEY:
            level_overrides.pop("difficulty", None)
            level_overrides.pop("subtype", None)

        cfg = load_level_config(level_key, config_path=args.config, overrides=level_overrides)
        try:
            generator = _create_generator(level_key, cfg)
            bundles: list[ChallengeBundle] = generator.generate_batch(
                count=args.count,
                base_seed=args.seed,
            )
        except (BDD100KNotFoundError, BDD100KDataSplitError, Level2BAssetNotFoundError) as exc:
            msg = f"[MISSING / INVALID DATA SOURCE] {level_key}: {exc}"
            print(msg)
            missing_errors.append(msg)
            if not is_all:
                return 2
            continue

        for bundle in bundles:
            export_challenge_bundle(
                bundle,
                output_root=out_dir,
                overwrite=True,
                organize_by_level=not args.flat_output,
                update_manifest=False,
            )
            if bundle.private_answer.datasetSource == "bdd100k":
                exported_bdd100k = True
            total_exported += 1

        print(
            f"[OK] Generated {len(bundles)} challenge(s) for {level_key} "
            f"(seed={args.seed}, output={out_dir})"
        )

    if exported_bdd100k:
        manifest_path = write_benchmark_manifest(out_dir)
        print(f"[OK] Updated benchmark manifest: {manifest_path}")

    print(f"Total exported challenges: {total_exported}")
    return 0 if total_exported > 0 else 2


def _cmd_validate(args: argparse.Namespace) -> int:
    target_dir = Path(args.directory)
    if not target_dir.is_absolute():
        target_dir = (Path.cwd() / target_dir).resolve()

    report = validate_generated_directory(
        target_dir,
        bdd100k_root=args.bdd100k_root,
        check_determinism=not args.skip_determinism,
    )

    print("=" * 72)
    print(f"VALIDATION REPORT: {target_dir}")
    print("=" * 72)

    if report.bdd100k_status is not None:
        bdd_tag = "READY" if report.bdd100k_status.available else "MISSING"
        print(f"Data Source [BDD100K (Lvl 1, 2A, 3B)] : [{bdd_tag}] {report.bdd100k_status.message}")
    if report.level_2b_status is not None:
        l2b_tag = "READY" if report.level_2b_status.available else "MISSING"
        print(f"Data Source [Level 2B Adelson Asset]  : [{l2b_tag}] {report.level_2b_status.message}")
    print("Data Source [Level 3A Tangled Cables] : [READY] Procedural graph-first generator")
    print("-" * 72)

    if report.global_errors:
        for err in report.global_errors:
            print(f"[GLOBAL ERROR] {err}")
        return 1

    by_variant: dict[str, list[bool]] = {}
    for item in report.results:
        by_variant.setdefault(item.variant, []).append(item.passed)
        if not item.passed:
            print(f"[FAIL] {item.challenge_id} ({item.variant}):")
            for err in item.errors:
                print(f"       - {err}")

    print("\nValidated Challenges by Variant:")
    for variant, statuses in sorted(by_variant.items()):
        passed_n = sum(1 for s in statuses if s)
        print(f"  - {variant:18s}: {passed_n}/{len(statuses)} passed")

    print("-" * 72)
    print(
        f"Total: {report.total_count} | Passed: {report.passed_count} | Failed: {report.failed_count}"
    )
    print("=" * 72)

    return 0 if report.is_valid else 1


def _cmd_status(args: argparse.Namespace) -> int:
    bdd_status = inspect_bdd100k_status(args.bdd100k_root)
    l2b_status = inspect_level_2b_asset_status()
    print("=" * 72)
    print("CHALLENGE ENGINE DATA & ASSET STATUS")
    print("=" * 72)
    print(
        f"1. BDD100K (Level 1, Level 2A, Level 3B): "
        f"{'READY' if bdd_status.available else 'MISSING'}\n"
        f"   {bdd_status.message}"
    )
    if bdd_status.available:
        print(f"   - Val image directory    : {bdd_status.image_dir}")
        print(f"   - Val images discovered  : {bdd_status.image_count}")
        print(f"   - Annotation files       : {[str(p) for p in bdd_status.annotation_files]}")
        print(f"   - Annotated val records  : {bdd_status.annotated_frame_count}")
        print(f"   - Source split / role    : {bdd_status.source_split} ({bdd_status.project_role})")
        print(f"   - Class image counts     : {bdd_status.class_image_counts}")
        print(f"   - Class box counts       : {bdd_status.class_box_counts}")
    print(
        f"2. Adelson Checker Shadow Asset (Level 2B): "
        f"{'READY' if l2b_status.available else 'MISSING'}\n"
        f"   {l2b_status.message}"
    )
    print(
        "3. Tangled Cables Procedural Engine (Level 3A): READY\n"
        "   Procedural one-to-one graph-first generator active."
    )
    print("=" * 72)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="challenge_engine",
        description="Generate, validate, and export deterministic visual CAPTCHA challenges.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate subcommand
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate challenges for a level and export public/private bundles.",
    )
    gen_parser.add_argument(
        "--level",
        required=True,
        help="Challenge level: 1, 2a, 2b, 3a, 3b (or 'all').",
    )
    gen_parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of challenges to generate (default: 1).",
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic base integer seed (default: 42).",
    )
    gen_parser.add_argument(
        "--output",
        "-o",
        default=str(PROJECT_ROOT / "generated"),
        help="Output directory for generated challenges (default: generated/).",
    )
    gen_parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="Optional path to custom level config JSON file.",
    )
    gen_parser.add_argument(
        "--bdd100k-root",
        default=None,
        help="Optional path to the shared BDD100K dataset directory.",
    )
    gen_parser.add_argument(
        "--difficulty",
        default=None,
        help="Optional difficulty override for Level 3A (easy, medium, hard, extreme).",
    )
    gen_parser.add_argument(
        "--subtype",
        default=None,
        help="Optional subtype for Level 3A (laser-maze, conveyor-routing, pipe-flow, device-cables, or all).",
    )
    gen_parser.add_argument(
        "--resolution",
        type=int,
        default=None,
        help="Optional single downsample resolution override for Level 3B (e.g., 16).",
    )
    gen_parser.add_argument(
        "--resolutions",
        default=None,
        help="Optional comma-separated resolutions for Level 3B comparison batch (e.g., 64,48,32,24,16,12,8).",
    )
    gen_parser.add_argument(
        "--flat-output",
        action="store_true",
        help="Write challenge folders directly into --output without level subdirectories.",
    )
    gen_parser.set_defaults(func=_cmd_generate)

    # validate subcommand
    val_parser = subparsers.add_parser(
        "validate",
        help="Validate all generated challenges and report dataset readiness.",
    )
    val_parser.add_argument(
        "directory",
        nargs="?",
        default=str(PROJECT_ROOT / "generated"),
        help="Directory containing generated challenges (default: generated/).",
    )
    val_parser.add_argument(
        "--bdd100k-root",
        default=None,
        help="Optional path to the shared BDD100K dataset directory.",
    )
    val_parser.add_argument(
        "--skip-determinism",
        action="store_true",
        help="Skip in-memory regeneration determinism check.",
    )
    val_parser.set_defaults(func=_cmd_validate)

    # status subcommand
    status_parser = subparsers.add_parser(
        "status",
        help="Report availability and status of BDD100K and Level 2B assets.",
    )
    status_parser.add_argument(
        "--bdd100k-root",
        default=None,
        help="Optional path to the shared BDD100K dataset directory.",
    )
    status_parser.set_defaults(func=_cmd_status)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
