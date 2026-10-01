"""Tests for BDD100K discovery, VAL-only split enforcement, benchmark manifest, Level 1, and Level 2A."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from challenge_engine.core.config import PROJECT_ROOT
from challenge_engine.core.exporter import build_benchmark_manifest, export_challenge_bundle
from challenge_engine.core.schemas import (
    BenchmarkManifest,
    Level1Config,
    Level2AConfig,
    Level3BConfig,
)
from challenge_engine.core.validation import validate_single_challenge_dir
from challenge_engine.datasets.bdd100k import (
    BDD100KDataSplitError,
    BDD100KDataset,
    BDD100KNotFoundError,
    inspect_bdd100k_status,
    load_bdd100k_dataset,
)
from challenge_engine.levels.level_1.generator import Level1StreetGridGenerator
from challenge_engine.levels.level_2a.generator import Level2AHardStreetGridGenerator
from challenge_engine.levels.level_3b.generator import Level3BDegradedVisionGenerator


def test_real_bdd100k_discovery_and_val_only_statistics() -> None:
    """Verify real BDD100K dataset discovery under data/bdd100k (10,000 val images & det_val.json)."""
    real_root = PROJECT_ROOT / "data" / "bdd100k"
    status = inspect_bdd100k_status(real_root)
    assert status.available is True, f"Expected real BDD100K to be READY, got: {status.message}"
    assert status.source_split == "val"
    assert status.project_role == "held_out_benchmark"
    assert status.image_count == 10000
    assert status.annotated_frame_count == 10000
    assert status.class_image_counts.get("motorcycle", 0) == 346
    assert status.class_box_counts.get("motorcycle", 0) == 460

    ds = load_bdd100k_dataset(real_root, split="val", use_cache=True)
    assert len(ds.frames) == 10000
    for frame in ds.frames:
        assert frame.source_split == "val"
        assert frame.source_dataset == "BDD100K"
        assert frame.project_role == "held_out_benchmark"
        assert "train" not in frame.source_path.lower().split("/")
        assert frame.sequence_id is not None and len(frame.sequence_id) == 8


def test_val_only_split_enforcement_rejects_train_split(sample_bdd100k_root: Path, tmp_path: Path) -> None:
    """Attempting to load or configure BDD100K 'train' split must raise an explicit error."""
    with pytest.raises(BDD100KDataSplitError):
        BDD100KDataset(sample_bdd100k_root, split="train")

    with pytest.raises(BDD100KDataSplitError):
        load_bdd100k_dataset(sample_bdd100k_root, split="train")

    with pytest.raises(ValidationError):
        Level1Config(sourceSplit="train")
    with pytest.raises(ValidationError):
        Level2AConfig(sourceSplit="train")
    with pytest.raises(ValidationError):
        Level3BConfig(sourceSplit="train")

    # Pointing directly at a train folder must also be rejected
    fake_train_dir = tmp_path / "bdd100k" / "images" / "100k" / "train"
    fake_train_dir.mkdir(parents=True)
    with pytest.raises(BDD100KDataSplitError):
        BDD100KDataset(fake_train_dir, split="val")


def test_validation_fails_if_challenge_references_train_split(
    sample_bdd100k_root: Path,
    tmp_path: Path,
) -> None:
    """Validation must fail if any Level 1, 2A, or 3B challenge metadata references 'train'."""
    cfg = Level1Config(bdd100kRoot=str(sample_bdd100k_root))
    gen = Level1StreetGridGenerator(cfg)
    bundle = gen.generate_one(seed=77)
    c_dir = export_challenge_bundle(bundle, tmp_path, update_manifest=False)

    # Tamper with answer.json to simulate train split leakage
    ans_path = c_dir / "answer.json"
    raw_ans = json.loads(ans_path.read_text(encoding="utf-8"))
    raw_ans["tiles"][0]["source_split"] = "train"
    raw_ans["tiles"][0]["source_path"] = "bdd100k/images/100k/train/leaked.jpg"
    ans_path.write_text(json.dumps(raw_ans, indent=2), encoding="utf-8")

    res = validate_single_challenge_dir(c_dir, check_determinism=False)
    assert res.passed is False
    assert any("Data leakage violation" in err for err in res.errors)


def test_bdd100k_missing_dataset_reports_clearly_without_fabricating_data(tmp_path: Path) -> None:
    """When BDD100K directory is empty or missing, status must report available=False and raise BDD100KNotFoundError."""
    empty_bdd = tmp_path / "empty_bdd100k"
    empty_bdd.mkdir()

    status = inspect_bdd100k_status(empty_bdd)
    assert status.available is False
    assert status.image_count == 0
    assert "incomplete" in status.message

    with pytest.raises(BDD100KNotFoundError):
        BDD100KDataset(empty_bdd)


def test_bdd100k_indexer_parses_annotations_bboxes_and_scene_metadata(
    sample_bdd100k_root: Path,
) -> None:
    """BDD100KDataset must index frames, compute relative bbox sizes, and inspect occlusion/truncation."""
    ds = BDD100KDataset(sample_bdd100k_root)
    assert len(ds.frames) == 60

    easy_frame = ds.get_frame("bdd_easy_pos_000.jpg")
    assert easy_frame is not None
    assert easy_frame.weather == "clear"
    assert easy_frame.timeofday == "daytime"
    assert easy_frame.source_split == "val"
    assert easy_frame.project_role == "held_out_benchmark"
    assert "motorcycle" in easy_frame.categories
    eval_easy = easy_frame.evaluate_for_target("motorcycle")
    assert eval_easy["is_positive"] is True
    assert eval_easy["is_easy_positive"] is True
    assert eval_easy["max_target_area_ratio"] > 0.05

    hard_frame = ds.get_frame("bdd_hard_pos_000.jpg")
    assert hard_frame is not None
    eval_hard = hard_frame.evaluate_for_target("motorcycle")
    assert eval_hard["is_positive"] is True
    assert eval_hard["is_easy_positive"] is False
    assert eval_hard["is_hard_positive"] is True
    assert "night" in eval_hard["difficulty_tags"]
    assert "occluded" in eval_hard["difficulty_tags"]
    assert "small-object" in eval_hard["difficulty_tags"]
    assert "confusable-object" in eval_hard["difficulty_tags"]


def test_level_1_selects_easy_bdd100k_val_samples_with_no_train_leakage(
    sample_bdd100k_root: Path,
) -> None:
    """Level 1 must select easy daytime unobstructed positive BDD100K val samples and clear negatives."""
    cfg = Level1Config(
        gridRows=3,
        gridColumns=3,
        target="motorcycle",
        positiveCountRange=(2, 4),
        bdd100kRoot=str(sample_bdd100k_root),
    )
    gen = Level1StreetGridGenerator(cfg)

    for seed in range(10, 18):
        bundle = gen.generate_one(seed)
        pub = bundle.public_challenge
        priv = bundle.private_answer

        assert pub.level == 1
        assert pub.variant == "street-grid"
        assert priv.datasetSource == "bdd100k"
        assert priv.dataset == "BDD100K"
        assert priv.source_dataset == "BDD100K"
        assert priv.source_split == "val"
        assert priv.project_role == "held_out_benchmark"
        assert 2 <= len(priv.correctSelection) <= 4
        assert priv.tiles is not None
        assert len({t.sourceId for t in priv.tiles}) == 9

        for tile in priv.tiles:
            assert tile.datasetSource == "bdd100k"
            assert tile.source_dataset == "BDD100K"
            assert tile.source_split == "val"
            assert tile.project_role == "held_out_benchmark"
            assert tile.source_image_id == tile.sourceId
            assert "train" not in tile.source_path.lower()
            if tile.tileIndex in priv.correctSelection:
                assert tile.isPositive is True
                assert "motorcycle" in tile.classes
                assert tile.sourceId.startswith("bdd_easy_pos_")
                assert tile.timeofday == "daytime"
            else:
                assert tile.isPositive is False
                assert "motorcycle" not in tile.classes
                assert tile.sourceId.startswith("bdd_easy_neg_")


@pytest.mark.parametrize("grid_size,pos_count", [(4, 5), (5, 6)])
def test_level_2a_selects_difficult_real_bdd100k_val_samples(
    sample_bdd100k_root: Path,
    grid_size: int,
    pos_count: int,
) -> None:
    """Level 2A must reuse BDD100K val split and select difficult real scenes (small/occluded/night/rain/confusable)."""
    cfg = Level2AConfig(
        gridSize=grid_size,
        target="motorcycle",
        positiveCount=pos_count,
        bdd100kRoot=str(sample_bdd100k_root),
    )
    gen = Level2AHardStreetGridGenerator(cfg)
    bundle = gen.generate_one(seed=100)

    pub = bundle.public_challenge
    priv = bundle.private_answer
    total_tiles = grid_size * grid_size

    assert pub.level == 2
    assert pub.variant == "hard-street-grid"
    assert priv.datasetSource == "bdd100k"
    assert priv.source_dataset == "BDD100K"
    assert priv.source_split == "val"
    assert priv.project_role == "held_out_benchmark"
    assert (pub.ui.rows, pub.ui.columns) == (grid_size, grid_size)
    assert len(pub.assets) == total_tiles
    assert len(priv.correctSelection) == pos_count

    assert priv.tiles is not None
    assert len({t.sourceId for t in priv.tiles}) == total_tiles

    for tile in priv.tiles:
        assert tile.source_split == "val"
        assert tile.project_role == "held_out_benchmark"
        assert "train" not in tile.source_path.lower()

    pos_tiles = [t for t in priv.tiles if t.isPositive]
    assert len(pos_tiles) == pos_count
    for pt in pos_tiles:
        assert pt.sourceId.startswith("bdd_hard_pos_")
        assert "motorcycle" in pt.classes
        assert len(pt.attributes) >= 1


def test_benchmark_manifest_creation_and_leakage_assertions(
    sample_bdd100k_root: Path,
    tmp_path: Path,
) -> None:
    """Exporting Level 1, 2A, and 3B challenges must create benchmark_manifest.json with val-only items."""
    out_dir = tmp_path / "generated_benchmark"
    gen_1 = Level1StreetGridGenerator(Level1Config(bdd100kRoot=str(sample_bdd100k_root)))
    gen_2a = Level2AHardStreetGridGenerator(Level2AConfig(bdd100kRoot=str(sample_bdd100k_root)))
    gen_3b = Level3BDegradedVisionGenerator(Level3BConfig(bdd100kRoot=str(sample_bdd100k_root)))

    export_challenge_bundle(gen_1.generate_one(seed=101), out_dir, organize_by_level=True)
    export_challenge_bundle(gen_2a.generate_one(seed=201), out_dir, organize_by_level=True)
    export_challenge_bundle(gen_3b.generate_one(seed=301), out_dir, organize_by_level=True)

    manifest_path = out_dir / "benchmark_manifest.json"
    assert manifest_path.exists()

    manifest = BenchmarkManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert manifest.dataset == "BDD100K"
    assert manifest.source_dataset == "BDD100K"
    assert manifest.source_split == "val"
    assert manifest.project_role == "held_out_benchmark"
    assert manifest.total_unique_images > 0

    used_levels: set[str] = set()
    for item in manifest.images:
        assert item.source_split == "val"
        assert item.project_role == "held_out_benchmark"
        assert "train" not in item.source_image_id.lower()
        assert "train" not in item.source_path.lower()
        used_levels.update(item.used_by)

    assert used_levels == {"level-1", "level-2a", "level-3b"}
    rebuilt = build_benchmark_manifest(out_dir)
    assert rebuilt == manifest
