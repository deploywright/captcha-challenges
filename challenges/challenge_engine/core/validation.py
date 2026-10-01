"""Automated validation suite for generated challenges, data sources, split isolation, and ground-truth answers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import numpy as np
from PIL import Image

from challenge_engine.core.config import load_level_config
from challenge_engine.core.ids import asset_relpath_for_index
from challenge_engine.core.schemas import (
    LEVEL_1_KEY,
    LEVEL_2A_KEY,
    LEVEL_2B_KEY,
    LEVEL_3A_KEY,
    LEVEL_3B_KEY,
    BenchmarkManifest,
    PrivateAnswer,
    PublicChallenge,
)
from challenge_engine.datasets.bdd100k import (
    BDD100KDataset,
    BDD100KStatus,
    inspect_bdd100k_status,
    load_bdd100k_dataset,
)
from challenge_engine.levels.level_1.generator import Level1StreetGridGenerator
from challenge_engine.levels.level_2a.generator import Level2AHardStreetGridGenerator
from challenge_engine.levels.level_2b.generator import (
    Level2BAssetStatus,
    Level2BCheckerShadowGenerator,
    inspect_level_2b_asset_status,
    measure_box_rgb_and_luminance,
)
from challenge_engine.levels.level_3a.generator import Level3ATangledCablesGenerator
from challenge_engine.levels.level_3b.generator import Level3BDegradedVisionGenerator

FORBIDDEN_PUBLIC_KEYS = {
    "correctSelection",
    "correct_tiles",
    "answer",
    "connections",
    "isPositive",
    "tiles",
    "illusion",
    "annotations",
    "sourceImage",
    "source_image",
    "source_image_id",
    "source_path",
    "transformation",
    "degradation",
    "targetClass",
    "target",
}

VARIANT_TO_LEVEL_KEY = {
    "street-grid": LEVEL_1_KEY,
    "hard-street-grid": LEVEL_2A_KEY,
    "checker-shadow": LEVEL_2B_KEY,
    "tangled-cables": LEVEL_3A_KEY,
    "degraded-vision": LEVEL_3B_KEY,
}


@dataclass
class ChallengeValidationResult:
    """Validation outcome for a single challenge directory."""

    challenge_id: str
    directory: Path
    variant: str = "unknown"
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.passed = False
        self.errors.append(msg)


@dataclass
class BatchValidationReport:
    """Summary validation report across a directory of generated challenges and data sources."""

    root_dir: Path
    results: list[ChallengeValidationResult] = field(default_factory=list)
    global_errors: list[str] = field(default_factory=list)
    bdd100k_status: BDD100KStatus | None = None
    level_2b_status: Level2BAssetStatus | None = None

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def is_valid(self) -> bool:
        return not self.global_errors and self.total_count > 0 and self.failed_count == 0


def _contains_train_reference(path_or_id: str) -> bool:
    norm = f"/{path_or_id.strip().lower().replace(chr(92), '/')}/"
    if "/train/" in norm or "/traina/" in norm or "/trainb/" in norm:
        return True
    if "det_train" in norm or "bdd_train" in norm:
        return True
    return False


def validate_single_challenge_dir(
    challenge_dir: Path,
    bdd100k_dataset: BDD100KDataset | None = None,
    check_determinism: bool = True,
) -> ChallengeValidationResult:
    """Validate a single `<challenge-id>` directory against universal, split-isolation, and level rules."""
    res = ChallengeValidationResult(
        challenge_id=challenge_dir.name,
        directory=challenge_dir,
    )

    challenge_json_path = challenge_dir / "challenge.json"
    answer_json_path = challenge_dir / "answer.json"

    if not challenge_json_path.exists():
        res.add_error("Missing challenge.json")
        return res
    if not answer_json_path.exists():
        res.add_error("Missing answer.json")
        return res

    try:
        raw_public = json.loads(challenge_json_path.read_text(encoding="utf-8"))
        raw_private = json.loads(answer_json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        res.add_error(f"Invalid JSON syntax: {exc}")
        return res

    for forbidden in FORBIDDEN_PUBLIC_KEYS:
        if forbidden in raw_public:
            res.add_error(f"Public challenge.json leaked forbidden key '{forbidden}'")

    try:
        pub = PublicChallenge.model_validate(raw_public)
    except Exception as exc:
        res.add_error(f"challenge.json schema validation failed: {exc}")
        return res

    try:
        priv = PrivateAnswer.model_validate(raw_private)
    except Exception as exc:
        res.add_error(f"answer.json schema validation failed: {exc}")
        return res

    res.variant = pub.variant

    if pub.id != challenge_dir.name:
        res.add_error(
            f"Directory name '{challenge_dir.name}' does not match challenge.id '{pub.id}'"
        )
    if priv.challengeId != pub.id:
        res.add_error(
            f"answer.challengeId '{priv.challengeId}' does not match challenge.id '{pub.id}'"
        )

    if not re.match(r"^lvl(1|2a|2b|3a|3b)_[0-9a-z]{6}$", pub.id):
        res.add_error(f"Challenge ID '{pub.id}' does not match neutral ID format")

    loaded_assets: dict[str, Image.Image] = {}
    for idx, rel_asset in enumerate(pub.assets):
        expected_rel = asset_relpath_for_index(idx, ext="webp")
        if rel_asset != expected_rel:
            res.add_error(
                f"Asset path '{rel_asset}' at index {idx} is not neutral (expected '{expected_rel}')"
            )
        asset_file = challenge_dir / rel_asset
        if not asset_file.exists():
            res.add_error(f"Referenced asset '{rel_asset}' does not exist")
            continue
        try:
            with Image.open(asset_file) as img:
                for meta_k, meta_v in (img.info or {}).items():
                    if isinstance(meta_v, (str, bytes)):
                        text_v = (
                            meta_v.decode("utf-8", errors="ignore")
                            if isinstance(meta_v, bytes)
                            else meta_v
                        )
                        if "correctSelection" in text_v or "bdd100k" in text_v.lower():
                            res.add_error(
                                f"Asset '{rel_asset}' metadata key '{meta_k}' leaks private info"
                            )
                loaded_assets[rel_asset] = img.convert("RGB")
        except Exception as exc:
            res.add_error(f"Failed to open asset '{rel_asset}': {exc}")

    if not res.passed:
        return res

    if pub.variant in {"street-grid", "hard-street-grid"}:
        _validate_street_grid_level(res, pub, priv, bdd100k_dataset)
    elif pub.variant == "checker-shadow":
        _validate_checker_shadow_level(res, pub, priv, loaded_assets)
    elif pub.variant == "tangled-cables":
        _validate_tangled_cables_level(res, pub, priv, loaded_assets)
    elif pub.variant == "degraded-vision":
        _validate_degraded_vision_level(res, pub, priv, loaded_assets, bdd100k_dataset)

    if check_determinism and res.passed:
        _validate_determinism(res, pub, priv, bdd100k_dataset)

    return res


def _validate_street_grid_level(
    res: ChallengeValidationResult,
    pub: PublicChallenge,
    priv: PrivateAnswer,
    bdd100k_dataset: BDD100KDataset | None,
) -> None:
    expected_tiles = pub.ui.rows * pub.ui.columns
    if len(pub.assets) != expected_tiles:
        res.add_error(
            f"Asset count ({len(pub.assets)}) != grid dimensions ({pub.ui.rows}x{pub.ui.columns}={expected_tiles})"
        )

    if priv.datasetSource != "bdd100k":
        res.add_error(
            f"Expected datasetSource='bdd100k' for {pub.variant}, got '{priv.datasetSource}'"
        )

    # Enforce strict VAL-only benchmark split
    if priv.source_split is not None and priv.source_split != "val":
        res.add_error(
            f"Data leakage violation: challenge answer has source_split='{priv.source_split}' (must be 'val')"
        )
    if priv.project_role is not None and priv.project_role != "held_out_benchmark":
        res.add_error(
            f"Expected project_role='held_out_benchmark', got '{priv.project_role}'"
        )
    if priv.source_path and _contains_train_reference(priv.source_path):
        res.add_error(
            f"Data leakage violation: challenge source_path '{priv.source_path}' references 'train'"
        )

    if not priv.targetClass:
        res.add_error("Missing targetClass in answer.json")
    else:
        readable_target = priv.targetClass.replace("-", " ").replace("_", " ")
        if readable_target not in pub.instruction.lower():
            res.add_error(
                f"Instruction '{pub.instruction}' does not mention targetClass '{priv.targetClass}'"
            )

    if not priv.tiles or len(priv.tiles) != expected_tiles:
        res.add_error(
            f"answer.tiles count ({len(priv.tiles) if priv.tiles else 0}) != {expected_tiles}"
        )
        return

    pos_indices_from_tiles = [t.tileIndex for t in priv.tiles if t.isPositive]
    if priv.correctSelection != pos_indices_from_tiles:
        res.add_error(
            f"correctSelection {priv.correctSelection} != positive tile indices {pos_indices_from_tiles}"
        )

    if not (1 <= len(priv.correctSelection) < expected_tiles):
        res.add_error(
            f"Invalid positive count {len(priv.correctSelection)} for grid of {expected_tiles} tiles"
        )

    source_ids = [t.sourceId for t in priv.tiles]
    if len(set(source_ids)) != len(source_ids):
        res.add_error(f"Duplicate BDD100K source frames detected in grid: {source_ids}")

    for t in priv.tiles:
        if t.datasetSource != "bdd100k":
            res.add_error(f"Tile {t.tileIndex} has non-BDD100K source '{t.datasetSource}'")
        if t.source_split != "val":
            res.add_error(
                f"Data leakage violation: tile {t.tileIndex} ({t.sourceId}) has source_split='{t.source_split}' (must be 'val')"
            )
        if t.project_role != "held_out_benchmark":
            res.add_error(
                f"Tile {t.tileIndex} has project_role='{t.project_role}' (expected 'held_out_benchmark')"
            )
        if _contains_train_reference(t.source_path) or _contains_train_reference(t.sourceId):
            res.add_error(
                f"Data leakage violation: tile {t.tileIndex} references BDD100K 'train' split ('{t.source_path}')"
            )
        if t.sourceId.startswith("street_"):
            res.add_error(
                f"Tile {t.tileIndex} uses legacy synthetic fixture ID '{t.sourceId}' instead of real BDD100K"
            )
        has_target = priv.targetClass in t.classes
        if t.isPositive != has_target:
            res.add_error(
                f"Tile {t.tileIndex} ({t.sourceId}) has isPositive={t.isPositive} but classes={t.classes}"
            )
        if bdd100k_dataset is not None:
            frame = bdd100k_dataset.get_frame(t.sourceId)
            if frame is None:
                res.add_error(
                    f"Tile {t.tileIndex} source frame '{t.sourceId}' not found in BDD100K val dataset"
                )
            elif frame.categories != set(t.classes):
                res.add_error(
                    f"Tile {t.tileIndex} classes {t.classes} != BDD100K frame annotations {sorted(frame.categories)}"
                )


def _validate_checker_shadow_level(
    res: ChallengeValidationResult,
    pub: PublicChallenge,
    priv: PrivateAnswer,
    loaded_assets: dict[str, Image.Image],
) -> None:
    if str(priv.answer).lower() != "yes":
        res.add_error(f"Expected Level 2B ground-truth answer 'Yes', got '{priv.answer}'")

    if priv.datasetSource != "adelson-static-asset":
        res.add_error(
            f"Level 2B must use 'adelson-static-asset', got datasetSource='{priv.datasetSource}'"
        )

    if not priv.illusion:
        res.add_error("Missing illusion metadata in Level 2B answer.json")
        return

    if priv.illusion.proceduralGenerationUsed:
        res.add_error("Level 2B must NOT use procedural generation")

    if not priv.illusion.source or not priv.illusion.license:
        res.add_error("Level 2B illusion metadata is missing documented source or license")

    img = loaded_assets[pub.assets[0]]
    width, height = img.size

    sq_a = priv.illusion.squareA
    sq_b = priv.illusion.squareB

    for sq in (sq_a, sq_b):
        x1, y1, x2, y2 = sq.safeInteriorBox
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            res.add_error(f"Square {sq.label} safeInteriorBox {sq.safeInteriorBox} is out of bounds")
            return

    rgb_a, lum_a = measure_box_rgb_and_luminance(img, sq_a.safeInteriorBox)
    rgb_b, lum_b = measure_box_rgb_and_luminance(img, sq_b.safeInteriorBox)

    lum_diff = abs(lum_a - lum_b)
    tol = priv.illusion.tolerance
    if lum_diff > tol:
        res.add_error(
            f"Square A luminance ({lum_a:.3f}) != Square B luminance ({lum_b:.3f}), diff={lum_diff:.3f} > tol={tol}"
        )


def _validate_tangled_cables_level(
    res: ChallengeValidationResult,
    pub: PublicChallenge,
    priv: PrivateAnswer,
    loaded_assets: dict[str, Image.Image],
) -> None:
    if not priv.connections or not priv.query or not priv.annotations:
        res.add_error("Level 3A answer.json is missing connections, query, or annotations")
        return

    connections = priv.connections
    sources = list(connections.keys())
    destinations = list(connections.values())
    n_cables = len(sources)

    if n_cables < 2:
        res.add_error(f"Invalid cable count: {n_cables}")
        return

    if len(set(sources)) != n_cables:
        res.add_error("Duplicate source keys in connections")
    if len(set(destinations)) != n_cables:
        res.add_error(
            f"Connections mapping is not one-to-one: {n_cables} sources map to {len(set(destinations))} unique destinations"
        )

    expected_sources = {f"server_{i + 1}" for i in range(n_cables)}
    expected_dests = {f"port_{i + 1}" for i in range(n_cables)}
    if set(sources) != expected_sources:
        res.add_error(f"Sources {set(sources)} != expected {expected_sources}")
    if set(destinations) != expected_dests:
        res.add_error(f"Destinations {set(destinations)} != expected {expected_dests}")

    if priv.query.type in {"find_source", "find-source"}:
        matching_sources = [s for s, d in connections.items() if d == priv.query.target]
        if len(matching_sources) != 1:
            res.add_error(
                f"Query target '{priv.query.target}' matched {len(matching_sources)} sources"
            )
        elif priv.answer != matching_sources[0]:
            res.add_error(
                f"Recorded answer '{priv.answer}' != connected source '{matching_sources[0]}'"
            )
    else:
        if priv.query.target not in connections:
            res.add_error(f"Query target '{priv.query.target}' not found in sources")
        elif priv.answer != connections[priv.query.target]:
            res.add_error(
                f"Recorded answer '{priv.answer}' != connected destination '{connections[priv.query.target]}'"
            )

    if pub.ui.options:
        if priv.answer not in pub.ui.options:
            res.add_error(f"Answer '{priv.answer}' is not in public ui.options")
        else:
            expected_idx = pub.ui.options.index(str(priv.answer))
            if priv.correctSelection != [expected_idx]:
                res.add_error(
                    f"correctSelection {priv.correctSelection} != [{expected_idx}]"
                )

    ann = priv.annotations
    width, height = ann.canvasDimensions
    img = loaded_assets[pub.assets[0]]
    if list(img.size) != [width, height]:
        res.add_error(
            f"Asset image size {list(img.size)} != annotated canvasDimensions {[width, height]}"
        )

    src_ep = ann.endpointPositions.get("sources", {})
    dst_ep = ann.endpointPositions.get("destinations", {})
    for src, dst in connections.items():
        if src not in ann.centerlines:
            res.add_error(f"Missing centerline for cable '{src}'")
            continue
        pts = ann.centerlines[src]
        if len(pts) < 4:
            res.add_error(f"Cable '{src}' centerline has too few vertices ({len(pts)})")
            continue
        s_pos = src_ep[src]
        d_pos = dst_ep[dst]
        if abs(pts[0][0] - s_pos[0]) > 1.0 or abs(pts[0][1] - s_pos[1]) > 1.0:
            res.add_error(f"Cable '{src}' start {pts[0]} != source endpoint {s_pos}")
        if abs(pts[-1][0] - d_pos[0]) > 1.0 or abs(pts[-1][1] - d_pos[1]) > 1.0:
            res.add_error(f"Cable '{src}' end {pts[-1]} != destination endpoint {d_pos}")
        for px, py in pts:
            if not (0.0 <= px <= width and 0.0 <= py <= height):
                res.add_error(
                    f"Cable '{src}' vertex ({px}, {py}) lies outside canvas (0..{width}, 0..{height})"
                )
                break


def _validate_degraded_vision_level(
    res: ChallengeValidationResult,
    pub: PublicChallenge,
    priv: PrivateAnswer,
    loaded_assets: dict[str, Image.Image],
    bdd100k_dataset: BDD100KDataset | None,
) -> None:
    _validate_street_grid_level(res, pub, priv, bdd100k_dataset)
    if not res.passed:
        return

    if not priv.degradation or not priv.transformation:
        res.add_error("Missing degradation or transformation metadata in Level 3B answer.json")
        return

    deg = priv.degradation
    res_w, res_h = deg.downsampleWidth, deg.downsampleHeight
    if res_w != res_h or res_w not in {64, 48, 32, 24, 16, 12, 8}:
        res.add_error(f"Invalid Level 3B downsample resolution: {res_w}x{res_h}")
        return

    assert priv.tiles is not None
    for t in priv.tiles:
        if t.degradation is None or t.transformation is None:
            res.add_error(f"Tile {t.tileIndex} is missing degradation/transformation metadata")
            continue
        if (t.degradation.downsampleWidth, t.degradation.downsampleHeight) != (res_w, res_h):
            res.add_error(f"Tile {t.tileIndex} resolution mismatch")

        img = loaded_assets[t.asset]
        w, h = img.size
        if (
            deg.upscaleMethod == "nearest"
            and deg.partialMaskRatio == 0.0
            and w % res_w == 0
            and h % res_h == 0
        ):
            block_w = w // res_w
            block_h = h // res_h
            arr = np.asarray(img, dtype=np.int32)
            blocks = arr.reshape(res_h, block_h, res_w, block_w, 3)
            max_intra_block_diff = int((blocks.max(axis=(1, 3)) - blocks.min(axis=(1, 3))).max())
            if max_intra_block_diff > 0:
                res.add_error(
                    f"Tile {t.tileIndex} ('{t.asset}') failed {res_w}x{res_h} nearest-neighbor pixel block check (diff={max_intra_block_diff})"
                )


def _validate_determinism(
    res: ChallengeValidationResult,
    pub: PublicChallenge,
    priv: PrivateAnswer,
    bdd100k_dataset: BDD100KDataset | None,
) -> None:
    """Re-generate the challenge in-memory using its seed and verify equivalence."""
    level_key = VARIANT_TO_LEVEL_KEY[pub.variant]
    cfg = load_level_config(level_key)

    if level_key in {LEVEL_1_KEY, LEVEL_2A_KEY, LEVEL_3B_KEY} and bdd100k_dataset is None:
        return

    if level_key == LEVEL_1_KEY:
        gen = Level1StreetGridGenerator(cfg, dataset=bdd100k_dataset)  # type: ignore[arg-type]
        re_bundle = gen.generate_one(pub.seed)
    elif level_key == LEVEL_2A_KEY:
        gen_2a = Level2AHardStreetGridGenerator(cfg, dataset=bdd100k_dataset)  # type: ignore[arg-type]
        re_bundle = gen_2a.generate_one(pub.seed)
    elif level_key == LEVEL_2B_KEY:
        gen_2b = Level2BCheckerShadowGenerator(cfg)  # type: ignore[arg-type]
        re_bundle = gen_2b.generate_one(pub.seed)
    elif level_key == LEVEL_3A_KEY:
        if priv.connections:
            cfg.cableCount = len(priv.connections)  # type: ignore[attr-defined]
        if priv.query:
            cfg.queryType = priv.query.type  # type: ignore[attr-defined]
        gen_3a = Level3ATangledCablesGenerator(cfg)  # type: ignore[arg-type]
        re_bundle = gen_3a.generate_one(pub.seed)
    elif level_key == LEVEL_3B_KEY:
        gen_3b = Level3BDegradedVisionGenerator(cfg, dataset=bdd100k_dataset)  # type: ignore[arg-type]
        res_val = priv.degradation.downsampleWidth if priv.degradation else None
        default_id = gen_3b.generate_one(pub.seed, resolution=res_val).public_challenge.id
        disc = f"res_{res_val}" if pub.id != default_id and res_val is not None else ""
        re_bundle = gen_3b.generate_one(
            pub.seed,
            resolution=res_val,
            extra_id_discriminator=disc,
        )
    else:
        return

    if re_bundle.public_challenge != pub:
        res.add_error("Deterministic regeneration produced a different PublicChallenge")
    if re_bundle.private_answer.correctSelection != priv.correctSelection:
        res.add_error("Deterministic regeneration produced a different correctSelection")
    if re_bundle.private_answer.answer != priv.answer:
        res.add_error("Deterministic regeneration produced a different answer")


def _discover_challenge_dirs(root: Path) -> list[Path]:
    """Find all challenge directories containing `challenge.json` under `root`."""
    if (root / "challenge.json").exists():
        return [root]
    found: list[Path] = []
    for cj in sorted(root.rglob("challenge.json")):
        found.append(cj.parent)
    return found


def validate_generated_directory(
    root_dir: str | Path,
    bdd100k_root: str | Path | None = None,
    check_determinism: bool = True,
) -> BatchValidationReport:
    """Validate all challenge directories inside `root_dir`, verify benchmark manifest, and inspect data sources."""
    root = Path(root_dir)
    bdd_status = inspect_bdd100k_status(bdd100k_root)
    l2b_status = inspect_level_2b_asset_status()

    report = BatchValidationReport(
        root_dir=root,
        bdd100k_status=bdd_status,
        level_2b_status=l2b_status,
    )

    if not root.exists():
        report.global_errors.append(f"Directory does not exist: {root}")
        return report

    candidate_dirs = _discover_challenge_dirs(root)
    if not candidate_dirs:
        report.global_errors.append(f"No challenge directories found under {root}")
        return report

    # Validate benchmark_manifest.json if present
    manifest_file = root / "benchmark_manifest.json"
    if manifest_file.exists():
        try:
            raw_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            bm = BenchmarkManifest.model_validate(raw_manifest)
            if bm.source_split != "val":
                report.global_errors.append(
                    f"benchmark_manifest.json has invalid source_split='{bm.source_split}' (expected 'val')"
                )
            for item in bm.images:
                if item.source_split != "val" or _contains_train_reference(item.source_path):
                    report.global_errors.append(
                        f"benchmark_manifest.json item '{item.source_image_id}' references non-val split '{item.source_path}'"
                    )
        except Exception as exc:
            report.global_errors.append(f"Invalid benchmark_manifest.json: {exc}")

    bdd_ds: BDD100KDataset | None = None
    if bdd_status.available:
        bdd_ds = load_bdd100k_dataset(bdd_status.root_dir, split="val", use_cache=True)

    seen_ids: set[str] = set()
    for c_dir in candidate_dirs:
        res = validate_single_challenge_dir(
            c_dir,
            bdd100k_dataset=bdd_ds,
            check_determinism=check_determinism,
        )
        if res.challenge_id in seen_ids:
            res.add_error(f"Duplicate challenge ID '{res.challenge_id}' across directories")
        seen_ids.add(res.challenge_id)
        report.results.append(res)

    return report
