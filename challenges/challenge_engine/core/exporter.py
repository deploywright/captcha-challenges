"""Exporter for writing public challenges, private answers, sanitized image assets, and the benchmark manifest."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from PIL import Image

from challenge_engine.core.config import PROJECT_ROOT
from challenge_engine.core.schemas import (
    LEVEL_DIR_NAMES,
    BenchmarkManifest,
    BenchmarkManifestEntry,
    PrivateAnswer,
    PublicChallenge,
)

VARIANT_TO_SUBDIR: dict[str, str] = {
    "street-grid": "level-1",
    "hard-street-grid": "level-2a",
    "checker-shadow": "level-2b",
    "tangled-cables": "level-3a",
    "degraded-vision": "level-3b",
}


@dataclass
class ChallengeBundle:
    """In-memory representation of a generated challenge prior to disk export."""

    public_challenge: PublicChallenge
    private_answer: PrivateAnswer
    assets: dict[str, Image.Image] = field(default_factory=dict)
    lossless_webp: bool = True


def strip_image_metadata(img: Image.Image) -> Image.Image:
    """Return a clean RGB copy of the image with all EXIF/text metadata removed."""
    rgb = img.convert("RGB")
    return Image.frombytes("RGB", rgb.size, rgb.tobytes())


def export_challenge_bundle(
    bundle: ChallengeBundle,
    output_root: str | Path,
    overwrite: bool = True,
    organize_by_level: bool = False,
    update_manifest: bool = True,
) -> Path:
    """Export a single ChallengeBundle to `<output_root>/[<level-dir>/]<challenge_id>/`."""
    challenge_id = bundle.public_challenge.id
    if bundle.private_answer.challengeId != challenge_id:
        raise ValueError(
            f"Mismatched challenge IDs: public={challenge_id} vs private={bundle.private_answer.challengeId}"
        )

    root_path = Path(output_root)
    base_root = root_path
    if organize_by_level:
        level_subdir = None
        if bundle.private_answer.levelKey in LEVEL_DIR_NAMES:
            level_subdir = LEVEL_DIR_NAMES[bundle.private_answer.levelKey]
        else:
            level_subdir = VARIANT_TO_SUBDIR.get(bundle.public_challenge.variant)
        if level_subdir and base_root.name != level_subdir:
            base_root = base_root / level_subdir

    out_dir = base_root / challenge_id
    if out_dir.exists() and not overwrite:
        raise FileExistsError(f"Challenge output directory already exists: {out_dir}")

    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for rel_asset in bundle.public_challenge.assets:
        if not rel_asset.startswith("assets/") or ".." in rel_asset:
            raise ValueError(f"Invalid asset relative path: {rel_asset}")
        if rel_asset not in bundle.assets:
            raise KeyError(f"Asset '{rel_asset}' referenced in challenge.json is missing from bundle")

        clean_img = strip_image_metadata(bundle.assets[rel_asset])
        asset_path = out_dir / rel_asset
        asset_path.parent.mkdir(parents=True, exist_ok=True)

        suffix = asset_path.suffix.lower()
        if suffix == ".webp":
            clean_img.save(
                asset_path,
                format="WEBP",
                lossless=bundle.lossless_webp,
                quality=100 if bundle.lossless_webp else 92,
                method=4,
            )
        elif suffix == ".png":
            clean_img.save(asset_path, format="PNG")
        else:
            clean_img.save(asset_path)

    challenge_json_path = out_dir / "challenge.json"
    public_payload = bundle.public_challenge.model_dump(mode="json", exclude_none=True)
    with challenge_json_path.open("w", encoding="utf-8") as f:
        json.dump(public_payload, f, indent=2)
        f.write("\n")

    answer_json_path = out_dir / "answer.json"
    private_payload = bundle.private_answer.model_dump(mode="json", exclude_none=True)
    with answer_json_path.open("w", encoding="utf-8") as f:
        json.dump(private_payload, f, indent=2)
        f.write("\n")

    if update_manifest and bundle.private_answer.datasetSource == "bdd100k":
        write_benchmark_manifest(root_path)

    return out_dir


def build_benchmark_manifest(output_root: str | Path) -> BenchmarkManifest:
    """Scan all generated challenges under `output_root` and build the BDD100K `val` benchmark manifest."""
    root = Path(output_root)
    entries_by_id: dict[str, dict[str, object]] = {}
    sequences_seen: set[str] = set()

    if root.exists():
        for ans_path in sorted(root.rglob("answer.json")):
            try:
                raw_ans = json.loads(ans_path.read_text(encoding="utf-8"))
                priv = PrivateAnswer.model_validate(raw_ans)
            except Exception:
                continue

            if priv.datasetSource != "bdd100k" or not priv.tiles:
                continue

            level_tag = LEVEL_DIR_NAMES.get(priv.levelKey or "", priv.levelKey or "unknown")
            for tile in priv.tiles:
                if tile.source_split != "val":
                    raise ValueError(
                        f"Benchmark leakage error: tile {tile.tileIndex} in {priv.challengeId} "
                        f"has source_split='{tile.source_split}' (expected 'val')."
                    )
                if "/train/" in tile.source_path.lower() or "\\train\\" in tile.source_path.lower():
                    raise ValueError(
                        f"Benchmark leakage error: tile {tile.tileIndex} in {priv.challengeId} "
                        f"references train path '{tile.source_path}'."
                    )

                img_id = tile.source_image_id or tile.sourceId
                if img_id not in entries_by_id:
                    entries_by_id[img_id] = {
                        "source_image_id": img_id,
                        "source_path": tile.source_path,
                        "source_split": "val",
                        "source_dataset": tile.source_dataset or "BDD100K",
                        "project_role": tile.project_role or "held_out_benchmark",
                        "sequence_id": tile.sequence_id,
                        "used_by": set(),
                        "challenge_ids": set(),
                    }
                rec = entries_by_id[img_id]
                rec["used_by"].add(level_tag)  # type: ignore[attr-defined]
                rec["challenge_ids"].add(priv.challengeId)  # type: ignore[attr-defined]
                if tile.sequence_id:
                    sequences_seen.add(tile.sequence_id)

    manifest_items: list[BenchmarkManifestEntry] = []
    for img_id in sorted(entries_by_id.keys()):
        rec = entries_by_id[img_id]
        manifest_items.append(
            BenchmarkManifestEntry(
                source_image_id=str(rec["source_image_id"]),
                source_path=str(rec["source_path"]),
                source_split="val",
                source_dataset=str(rec["source_dataset"]),
                project_role=str(rec["project_role"]),
                sequence_id=rec["sequence_id"] if isinstance(rec["sequence_id"], str) else None,
                used_by=sorted(rec["used_by"]),  # type: ignore[arg-type]
                challenge_ids=sorted(rec["challenge_ids"]),  # type: ignore[arg-type]
            )
        )

    sorted_seqs = sorted(sequences_seen)
    return BenchmarkManifest(
        dataset="BDD100K",
        source_dataset="BDD100K",
        source_split="val",
        project_role="held_out_benchmark",
        total_unique_images=len(manifest_items),
        total_unique_sequences=len(sorted_seqs),
        sequences=sorted_seqs,
        images=manifest_items,
    )


def write_benchmark_manifest(output_root: str | Path) -> Path:
    """Build and write `benchmark_manifest.json` inside `output_root` (and mirror to `data/bdd100k/` when generating into default `generated/`)."""
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = build_benchmark_manifest(root)
    payload = manifest.model_dump(mode="json")

    manifest_path = root / "benchmark_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    # Also mirror to data/bdd100k/benchmark_manifest.json when writing to default generated/ root
    default_gen = (PROJECT_ROOT / "generated").resolve()
    bdd_dir = (PROJECT_ROOT / "data" / "bdd100k").resolve()
    if root.resolve() == default_gen and bdd_dir.exists():
        mirror_path = bdd_dir / "benchmark_manifest.json"
        with mirror_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")

    return manifest_path
