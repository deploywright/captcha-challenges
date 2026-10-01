"""Tests for Level 3B — BDD100K `val` Degraded Vision resolution ladder, original linkage, and source immutability."""

from __future__ import annotations

import hashlib
from pathlib import Path
import numpy as np
import pytest

from challenge_engine.core.schemas import Level3BConfig
from challenge_engine.levels.level_3b.generator import Level3BDegradedVisionGenerator


@pytest.mark.parametrize("resolution", [64, 48, 32, 24, 16, 12, 8])
def test_level_3b_resolution_ladder_and_bdd100k_val_linkage(
    sample_bdd100k_root: Path,
    resolution: int,
) -> None:
    """Degraded BDD100K val images must preserve source linkage, leave originals untouched, and match block size."""
    tile_size = 192 if resolution in (48, 24, 12) else 256
    cfg = Level3BConfig(
        resolution=resolution,
        tileWidth=tile_size,
        tileHeight=tile_size,
        positiveCount=3,
        bdd100kRoot=str(sample_bdd100k_root),
    )

    # Hash original BDD100K files before transformation to verify they remain untouched
    orig_files = sorted((sample_bdd100k_root / "images").rglob("*.jpg"))
    before_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in orig_files}

    gen = Level3BDegradedVisionGenerator(cfg)
    bundle = gen.generate_one(seed=410)

    after_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in orig_files}
    assert before_hashes == after_hashes, "Source BDD100K files must never be modified"

    priv = bundle.private_answer
    assert priv.datasetSource == "bdd100k"
    assert priv.dataset == "BDD100K"
    assert priv.source_dataset == "BDD100K"
    assert priv.source_split == "val"
    assert priv.project_role == "held_out_benchmark"
    assert priv.source_image is not None and priv.source_image.endswith(".jpg")
    assert priv.source_image_id == priv.source_image
    assert priv.target == "motorcycle"
    assert priv.transformation is not None
    assert priv.transformation.type == "downsample_upscale"
    assert priv.transformation.resolution == resolution
    assert priv.transformation.upscale == "nearest"
    assert priv.degradation is not None
    assert priv.degradation.downsampleWidth == resolution
    assert len(priv.correctSelection) == 3

    assert priv.tiles is not None
    for tile in priv.tiles:
        assert tile.source_split == "val"
        assert tile.project_role == "held_out_benchmark"
        assert tile.source_image_id == tile.sourceId
        assert "train" not in tile.source_path.lower()

    block_size = tile_size // resolution
    for rel_asset, img in bundle.assets.items():
        assert img.size == (tile_size, tile_size)
        arr = np.asarray(img.convert("RGB"), dtype=np.int32)
        blocks = arr.reshape(resolution, block_size, resolution, block_size, 3)
        intra_block_diff = int((blocks.max(axis=(1, 3)) - blocks.min(axis=(1, 3))).max())
        assert intra_block_diff == 0, f"Expected constant nearest-neighbor blocks in {rel_asset}"


def test_level_3b_multi_resolution_series_preserves_exact_bdd100k_grid(
    sample_bdd100k_root: Path,
) -> None:
    """Multi-resolution comparison across [64, 48, 32, 24, 16, 12, 8] must use the exact same BDD100K val frames."""
    cfg = Level3BConfig(bdd100kRoot=str(sample_bdd100k_root))
    gen = Level3BDegradedVisionGenerator(cfg)
    resolutions = [64, 48, 32, 24, 16, 12, 8]
    series = gen.generate_multi_resolution_series(seed=500, resolutions=resolutions)

    assert len(series) == 7
    ids = [b.public_challenge.id for b in series]
    assert len(set(ids)) == 7

    base_sources = [t.source_image_id for t in series[0].private_answer.tiles or []]
    base_selection = series[0].private_answer.correctSelection

    for bundle, expected_res in zip(series, resolutions):
        assert bundle.private_answer.source_split == "val"
        assert bundle.private_answer.transformation is not None
        assert bundle.private_answer.transformation.resolution == expected_res
        assert bundle.private_answer.correctSelection == base_selection
        sources = [t.source_image_id for t in bundle.private_answer.tiles or []]
        assert sources == base_sources
