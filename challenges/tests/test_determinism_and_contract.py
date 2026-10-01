"""Tests for deterministic seeded generation, universal schema contract, and public/private separation."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from PIL import Image
import pytest
from pydantic import ValidationError

from challenge_engine.cli import main as cli_main
from challenge_engine.core.schemas import (
    ALL_LEVEL_KEYS,
    Level1Config,
    Level3BConfig,
    PrivateAnswer,
    PublicChallenge,
)
from challenge_engine.core.validation import (
    FORBIDDEN_PUBLIC_KEYS,
    validate_generated_directory,
)


@pytest.mark.parametrize("level_key", ALL_LEVEL_KEYS)
def test_deterministic_seeded_generation_across_all_levels(
    level_key: str,
    sample_bdd100k_root: Path,
    tmp_path: Path,
) -> None:
    """Running generation twice with the same seed must produce equivalent challenge definitions and pixels."""
    dir_run1 = tmp_path / "run1"
    dir_run2 = tmp_path / "run2"

    rc1 = cli_main(
        [
            "generate",
            "--level",
            level_key,
            "--count",
            "2",
            "--seed",
            "42",
            "--bdd100k-root",
            str(sample_bdd100k_root),
            "--output",
            str(dir_run1),
            "--flat-output",
        ]
    )
    rc2 = cli_main(
        [
            "generate",
            "--level",
            level_key,
            "--count",
            "2",
            "--seed",
            "42",
            "--bdd100k-root",
            str(sample_bdd100k_root),
            "--output",
            str(dir_run2),
            "--flat-output",
        ]
    )
    assert rc1 == 0
    assert rc2 == 0

    subdirs_1 = sorted(p.name for p in dir_run1.iterdir() if p.is_dir())
    subdirs_2 = sorted(p.name for p in dir_run2.iterdir() if p.is_dir())
    assert len(subdirs_1) == 2
    assert subdirs_1 == subdirs_2

    for cid in subdirs_1:
        c1_json = (dir_run1 / cid / "challenge.json").read_text(encoding="utf-8")
        c2_json = (dir_run2 / cid / "challenge.json").read_text(encoding="utf-8")
        assert c1_json == c2_json

        a1_json = (dir_run1 / cid / "answer.json").read_text(encoding="utf-8")
        a2_json = (dir_run2 / cid / "answer.json").read_text(encoding="utf-8")
        assert a1_json == a2_json

        pub = PublicChallenge.model_validate_json(c1_json)
        for asset_rel in pub.assets:
            with Image.open(dir_run1 / cid / asset_rel) as img1, Image.open(
                dir_run2 / cid / asset_rel
            ) as img2:
                arr1 = np.asarray(img1.convert("RGB"))
                arr2 = np.asarray(img2.convert("RGB"))
                assert np.array_equal(arr1, arr2)


@pytest.mark.parametrize("level_key", ALL_LEVEL_KEYS)
def test_public_private_answer_separation(
    level_key: str,
    sample_bdd100k_root: Path,
    tmp_path: Path,
) -> None:
    """Public challenge.json, asset filenames, and image metadata must never leak the answer."""
    out_dir = tmp_path / "out"
    rc = cli_main(
        [
            "generate",
            "--level",
            level_key,
            "--count",
            "1",
            "--seed",
            "99",
            "--bdd100k-root",
            str(sample_bdd100k_root),
            "--output",
            str(out_dir),
            "--flat-output",
        ]
    )
    assert rc == 0

    c_dir = next(p for p in out_dir.iterdir() if p.is_dir())
    raw_public = json.loads((c_dir / "challenge.json").read_text(encoding="utf-8"))
    raw_private = json.loads((c_dir / "answer.json").read_text(encoding="utf-8"))

    for key in FORBIDDEN_PUBLIC_KEYS:
        assert key not in raw_public, f"Leaked private key '{key}' in challenge.json"

    pub = PublicChallenge.model_validate(raw_public)
    priv = PrivateAnswer.model_validate(raw_private)
    assert pub.id == priv.challengeId

    for asset_path in pub.assets:
        assert asset_path.startswith("assets/")
        stem = Path(asset_path).stem
        assert stem.isalpha() and stem.islower()
        assert "bdd" not in stem
        assert "pos" not in stem
        assert "neg" not in stem

    report = validate_generated_directory(out_dir, bdd100k_root=sample_bdd100k_root)
    assert report.is_valid, f"Validation failed: {[r.errors for r in report.results]}"


def test_schema_validation_rejects_invalid_configs_and_payloads() -> None:
    """Pydantic schemas must reject out-of-range parameters, non-val splits, and extra/leaked fields."""
    with pytest.raises(ValidationError):
        Level1Config(gridRows=3, gridColumns=3, positiveCountRange=(2, 9))

    with pytest.raises(ValidationError):
        Level1Config(sourceSplit="train")

    with pytest.raises(ValidationError):
        Level3BConfig(resolution=15)

    with pytest.raises(ValidationError):
        PublicChallenge.model_validate(
            {
                "schemaVersion": 1,
                "id": "lvl1_abc123",
                "level": 1,
                "variant": "street-grid",
                "type": "image-selection",
                "instruction": "Select all images containing a motorcycle.",
                "seed": 42,
                "assets": ["assets/a.webp"],
                "ui": {"rows": 1, "columns": 1, "selectionMode": "multiple"},
                "correctSelection": [0],
            }
        )
