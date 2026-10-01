"""Tests for Level 3A — Routing Puzzles family (Laser Maze, Conveyor, Pipe Flow, Device Cables)."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from PIL import Image
import pytest

from challenge_engine.core.schemas import (
    LEVEL_3A_KEY,
    Level3AConfig,
    PrivateAnswer,
    PublicChallenge,
)
from challenge_engine.core.validation import (
    FORBIDDEN_PUBLIC_KEYS,
    validate_generated_directory,
)
from challenge_engine.levels.level_3a.conveyor_routing import ConveyorRoutingGenerator
from challenge_engine.levels.level_3a.device_cables import DeviceCablesGenerator
from challenge_engine.levels.level_3a.generator import Level3ARoutingGenerator
from challenge_engine.levels.level_3a.laser_maze import LaserMazeGenerator
from challenge_engine.levels.level_3a.pipe_flow import PipeFlowGenerator


SUBTYPE_CLASSES = [
    ("laser-maze", LaserMazeGenerator),
    ("conveyor-routing", ConveyorRoutingGenerator),
    ("pipe-flow", PipeFlowGenerator),
    ("device-cables", DeviceCablesGenerator),
]


@pytest.mark.parametrize("subtype_name,gen_cls", SUBTYPE_CLASSES)
def test_routing_puzzle_subtypes_generation_and_contract(subtype_name: str, gen_cls: type) -> None:
    """Each routing puzzle subtype must generate a valid single-choice challenge with zero private leakage."""
    cfg = Level3AConfig(difficulty="medium")
    gen = gen_cls(cfg)
    bundle = gen.generate_one(seed=777)

    pub = bundle.public_challenge
    priv = bundle.private_answer

    # 1. Public contract
    assert pub.level == 3
    assert pub.variant == "routing-puzzle"
    assert pub.subtype == subtype_name
    assert pub.type == "single-choice"
    assert len(pub.assets) == 1
    assert pub.ui.selectionMode == "single"
    assert pub.ui.options is not None
    assert len(pub.ui.options) >= 3

    # 2. Private contract
    assert priv.datasetSource == f"procedural-{subtype_name}"
    assert priv.subtype == subtype_name
    assert len(priv.correctSelection) == 1
    corr_idx = priv.correctSelection[0]
    assert pub.ui.options[corr_idx] == str(priv.answer)
    assert priv.routing is not None

    # 3. Asset validation
    rel_asset = pub.assets[0]
    assert rel_asset in bundle.assets
    img = bundle.assets[rel_asset]
    assert img.size == (cfg.canvasWidth, cfg.canvasHeight)

    # 4. Zero leakage check
    pub_dict = pub.model_dump()
    for forbidden in FORBIDDEN_PUBLIC_KEYS:
        assert forbidden not in pub_dict, f"Forbidden key '{forbidden}' leaked in public challenge"


@pytest.mark.parametrize("subtype_name,gen_cls", SUBTYPE_CLASSES)
def test_routing_puzzle_subtypes_determinism(subtype_name: str, gen_cls: type) -> None:
    """Identical seeds must produce bit-for-bit identical definitions and rendered pixels."""
    cfg = Level3AConfig(difficulty="medium")
    gen = gen_cls(cfg)

    b1 = gen.generate_one(seed=888)
    b2 = gen.generate_one(seed=888)

    assert b1.public_challenge.model_dump_json() == b2.public_challenge.model_dump_json()
    assert b1.private_answer.model_dump_json() == b2.private_answer.model_dump_json()

    img1 = b1.assets[b1.public_challenge.assets[0]]
    img2 = b2.assets[b2.public_challenge.assets[0]]
    arr1 = np.asarray(img1.convert("RGB"))
    arr2 = np.asarray(img2.convert("RGB"))
    assert np.array_equal(arr1, arr2)


def test_level_3a_routing_generator_dispatcher(tmp_path: Path) -> None:
    """Level3ARoutingGenerator must dispatch to default laser-maze and handle 'all' round-robin batch."""
    cfg = Level3AConfig(difficulty="medium")
    main_gen = Level3ARoutingGenerator(cfg)

    # Default single generation -> laser-maze
    b_default = main_gen.generate_one(seed=123)
    assert b_default.public_challenge.variant == "routing-puzzle"
    assert b_default.public_challenge.subtype == "laser-maze"

    # Batch with subtype="all" -> all 4 subtypes produced
    cfg_all = Level3AConfig(subtype="all", difficulty="medium")
    gen_all = Level3ARoutingGenerator(cfg_all)
    batch = gen_all.generate_batch(count=4, base_seed=500)
    assert len(batch) == 4
    subtypes = [b.public_challenge.subtype for b in batch]
    assert subtypes == ["laser-maze", "conveyor-routing", "pipe-flow", "device-cables"]

    # Export and validate directory
    from challenge_engine.core.exporter import export_challenge_bundle
    for b in batch:
        export_challenge_bundle(b, output_root=tmp_path, overwrite=True)

    report = validate_generated_directory(tmp_path, check_determinism=False)
    assert report.total_count == 4
    assert report.passed_count == 4
    assert report.failed_count == 0
