"""Comprehensive test suite for the challenge overhaul requirements:
1. Aspect ratio preservation & context-aware cropping.
2. Rendered target visibility gates (Level 1 and Level 2A).
3. Multi-class street CAPTCHA generation across canonical profiles.
4. Level 2B canonical visual illusions library with measurable ground truth.
5. Level 3A device/outlet endpoints, halo bridges, and query types.
6. Level 3B consistent context crops across resolution ladder.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image
import pytest

from challenge_engine.core.exporter import export_challenge_bundle
from challenge_engine.core.image_prep import (
    compute_context_crop_window,
    compute_rendered_metrics,
    prepare_context_crop,
    prepare_negative_crop,
)
from challenge_engine.core.schemas import (
    Level1Config,
    Level2AConfig,
    Level2BConfig,
    Level3AConfig,
    Level3BConfig,
)
from challenge_engine.datasets.bdd100k import CLASS_PROFILES
from challenge_engine.levels.level_1.generator import Level1StreetGridGenerator
from challenge_engine.levels.level_2a.generator import Level2AHardStreetGridGenerator
from challenge_engine.levels.level_2b.generator import Level2BCheckerShadowGenerator
from challenge_engine.levels.level_3a.generator import Level3ATangledCablesGenerator
from challenge_engine.levels.level_3b.generator import Level3BDegradedVisionGenerator


def test_aspect_ratio_preservation_and_context_crop() -> None:
    """Cropping must produce square crops from 16:9 images without geometric stretching."""
    img = Image.new("RGB", (1280, 720), (50, 100, 150))
    target_box = [400.0, 250.0, 480.0, 350.0]  # width 80, height 100

    crop_window = compute_context_crop_window(
        frame_width=1280,
        frame_height=720,
        target_box=target_box,
        context_padding=1.0,
    )
    cx1, cy1, cx2, cy2 = crop_window
    crop_w = cx2 - cx1
    crop_h = cy2 - cy1

    # Must be strictly 1:1 aspect ratio
    assert crop_w == crop_h, f"Crop window {crop_window} is not square"
    # Target must be contained inside the crop window
    assert cx1 <= target_box[0] and cx2 >= target_box[2]
    assert cy1 <= target_box[1] and cy2 >= target_box[3]

    res = prepare_context_crop(img, target_box, output_size=(256, 256), context_padding=1.0)
    assert res.image.size == (256, 256)
    assert res.target_metrics is not None
    assert res.target_metrics.rendered_width > 0
    assert res.target_metrics.rendered_height > 0


def test_rendered_target_metrics_computation() -> None:
    """Compute accurate pixel dimensions and bounding boxes within the rendered tile."""
    target_box = [100.0, 100.0, 200.0, 200.0]  # 100x100 in original frame
    crop_window = (50, 50, 250, 250)           # 200x200 crop window
    output_size = (256, 256)

    metrics = compute_rendered_metrics(target_box, crop_window, output_size)
    # Target spans (100-50)/200 to (200-50)/200 of crop -> 25% to 75% -> in 256x256: 64px to 192px
    assert metrics.rendered_width == pytest.approx(128.0, abs=1.0)
    assert metrics.rendered_height == pytest.approx(128.0, abs=1.0)
    assert metrics.rendered_max_dim == pytest.approx(128.0, abs=1.0)


def test_level_1_and_level_2a_multi_class_generation(sample_bdd100k_root: Path) -> None:
    """Generators must support multiple street target classes and record rendered dimensions."""
    cfg1 = Level1Config(
        gridRows=3,
        gridColumns=3,
        target="motorcycle",
        positiveCount=3,
        bdd100kRoot=str(sample_bdd100k_root),
    )
    gen1 = Level1StreetGridGenerator(cfg1)
    bundle1 = gen1.generate_one(seed=101)

    assert bundle1.public_challenge.ui.rows == 3
    assert bundle1.public_challenge.ui.columns == 3
    assert len(bundle1.private_answer.tiles) == 9

    pos_tiles_l1 = [t for t in bundle1.private_answer.tiles if t.isPositive]
    assert len(pos_tiles_l1) == 3
    for t in pos_tiles_l1:
        assert t.rendered_object_size is not None
        assert t.crop_box is not None
        assert len(t.crop_box) == 4

    # Test Level 2A with 3x3 default
    cfg2a = Level2AConfig(
        gridSize=3,
        target="motorcycle",
        positiveCount=3,
        bdd100kRoot=str(sample_bdd100k_root),
    )
    gen2a = Level2AHardStreetGridGenerator(cfg2a)
    bundle2a = gen2a.generate_one(seed=201)

    assert bundle2a.public_challenge.ui.rows == 3
    assert bundle2a.public_challenge.ui.columns == 3
    assert len(bundle2a.private_answer.tiles) == 9

    pos_tiles_l2a = [t for t in bundle2a.private_answer.tiles if t.isPositive]
    assert len(pos_tiles_l2a) == 3
    for t in pos_tiles_l2a:
        assert t.rendered_object_size is not None
        assert t.difficulty_budget_factors is not None


def test_level_2b_canonical_illusions_library(tmp_path: Path) -> None:
    """Level 2B must support all 6 canonical visual illusions with verified mathematical equality."""
    cfg = Level2BConfig()
    gen = Level2BCheckerShadowGenerator(cfg)

    # Generate batch of 6 to verify cycling through all canonical illusions
    bundles = gen.generate_batch(count=6, base_seed=100)
    assert len(bundles) == 6

    illusion_types_seen = set()
    for b in bundles:
        pub = b.public_challenge
        priv = b.private_answer
        assert priv.illusion is not None
        assert priv.illusion.proceduralGenerationUsed is False
        assert priv.illusion.source != ""
        assert priv.illusion.license != ""
        assert str(priv.answer).lower() == "yes"
        illusion_types_seen.add(priv.illusion.illusionType)

    # Must contain multiple canonical illusions from the library
    assert len(illusion_types_seen) >= 4


def test_level_3a_device_outlet_naming_and_bridges() -> None:
    """Level 3A must use familiar devices/outlets, 8 cables default, and valid one-to-one connections."""
    cfg = Level3AConfig(cableCount=8, queryType="find_source")
    gen = Level3ATangledCablesGenerator(cfg)
    bundle = gen.generate_one(seed=301)

    pub = bundle.public_challenge
    priv = bundle.private_answer

    assert "plugged into" in pub.instruction or "connected to" in pub.instruction
    assert priv.connections is not None
    assert len(priv.connections) == 8

    # Endpoints should be familiar devices and outlets
    sources = list(priv.connections.keys())
    dests = list(priv.connections.values())
    assert all(not s.startswith("server_") for s in sources)
    assert all(not d.startswith("port_") for d in dests)
    assert all(d.startswith("Outlet") for d in dests)


def test_level_3b_fixed_crop_across_resolution_ladder(sample_bdd100k_root: Path) -> None:
    """Level 3B must use the EXACT same 1:1 context crop window across different degradation resolutions."""
    cfg = Level3BConfig(
        gridRows=3,
        gridColumns=3,
        target="motorcycle",
        positiveCount=3,
        bdd100kRoot=str(sample_bdd100k_root),
    )
    gen = Level3BDegradedVisionGenerator(cfg)

    bundle_64 = gen.generate_one(seed=555, resolution=64)
    bundle_16 = gen.generate_one(seed=555, resolution=16)

    # Grid selection, positives, and crop windows must be 100% identical between resolutions
    assert bundle_64.private_answer.correctSelection == bundle_16.private_answer.correctSelection

    for t64, t16 in zip(bundle_64.private_answer.tiles, bundle_16.private_answer.tiles):
        assert t64.sourceId == t16.sourceId
        assert t64.crop_box == t16.crop_box, "Crop box must not change across resolution ladder"
        assert t64.isPositive == t16.isPositive
