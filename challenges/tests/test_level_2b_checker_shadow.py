"""Tests for Level 2B — Adelson Checker Shadow Illusion static asset, provenance metadata, and equal shade."""

from __future__ import annotations

from pathlib import Path
from PIL import Image
import pytest

from challenge_engine.core.exporter import export_challenge_bundle
from challenge_engine.core.schemas import Level2BConfig
from challenge_engine.core.validation import validate_single_challenge_dir
from challenge_engine.levels.level_2b.generator import (
    Level2BAssetNotFoundError,
    Level2BCheckerShadowGenerator,
    inspect_level_2b_asset_status,
    measure_box_rgb_and_luminance,
)


def test_level_2b_uses_existing_adelson_asset_and_validates_provenance(tmp_path: Path) -> None:
    """Level 2B must package the existing Adelson Checker Shadow asset without procedural synthesis."""
    status = inspect_level_2b_asset_status()
    assert status.available is True

    cfg = Level2BConfig()
    gen = Level2BCheckerShadowGenerator(cfg)
    bundle = gen.generate_one(seed=200)
    out_dir = export_challenge_bundle(bundle, tmp_path)

    val_res = validate_single_challenge_dir(out_dir)
    assert val_res.passed, f"Validation failed: {val_res.errors}"

    priv = bundle.private_answer
    assert priv.datasetSource == "adelson-static-asset"
    assert priv.answer == "Yes"
    assert priv.illusion is not None
    assert priv.illusion.proceduralGenerationUsed is False
    assert "Adelson" in priv.illusion.assetName
    assert "Adelson" in priv.illusion.license

    asset_path = out_dir / bundle.public_challenge.assets[0]
    with Image.open(asset_path) as saved_img:
        rgb_a, lum_a = measure_box_rgb_and_luminance(
            saved_img, priv.illusion.squareA.safeInteriorBox
        )
        rgb_b, lum_b = measure_box_rgb_and_luminance(
            saved_img, priv.illusion.squareB.safeInteriorBox
        )

    assert abs(lum_a - lum_b) <= cfg.luminanceTolerance
    for ca, cb in zip(rgb_a, rgb_b):
        assert abs(ca - cb) <= max(1.0, cfg.luminanceTolerance)


def test_level_2b_missing_asset_raises_error_instead_of_synthesizing(tmp_path: Path) -> None:
    """If the configured Adelson asset path does not exist, Level 2B must raise Level2BAssetNotFoundError."""
    cfg = Level2BConfig(assetPath=str(tmp_path / "nonexistent-checker-shadow.png"))
    with pytest.raises(Level2BAssetNotFoundError):
        Level2BCheckerShadowGenerator(cfg)
