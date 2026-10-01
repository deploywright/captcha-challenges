"""Level 1 — Normal Street CAPTCHA builder using real BDD100K `val` easy samples."""

from __future__ import annotations

from PIL import Image

from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.ids import asset_relpath_for_index, generate_challenge_id
from challenge_engine.core.random import DeterministicRNG
from challenge_engine.core.schemas import (
    LEVEL_1_KEY,
    Level1Config,
    PrivateAnswer,
    PublicChallenge,
    PublicUIConfig,
    TilePrivateMetadata,
)
from challenge_engine.datasets.bdd100k import (
    BDD100KDataSplitError,
    BDD100KDataset,
    load_bdd100k_dataset,
    normalize_bdd100k_category,
)


def format_grid_instruction(target: str) -> str:
    """Format human-readable instruction for a target class."""
    display = target.replace("-", " ").replace("_", " ").strip()
    article = "an" if display[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"Select all images containing {article} {display}."


class Level1StreetGridGenerator:
    """Selects easy, clearly visible BDD100K `val` samples and packages a 3x3 Street CAPTCHA."""

    level_key = LEVEL_1_KEY

    def __init__(self, config: Level1Config, dataset: BDD100KDataset | None = None) -> None:
        self.config = config
        if self.config.sourceSplit != "val":
            raise BDD100KDataSplitError(
                f"Level 1 requires BDD100K 'val' split only, got '{self.config.sourceSplit}'."
            )
        if dataset is not None:
            if getattr(dataset, "source_split", "val") != "val":
                raise BDD100KDataSplitError(
                    f"Level 1 dataset must use 'val' split only, got '{dataset.source_split}'."
                )
            self.dataset = dataset
        else:
            self.dataset = load_bdd100k_dataset(
                self.config.bdd100kRoot,
                split=self.config.sourceSplit,
            )

    def generate_one(self, seed: int) -> ChallengeBundle:
        """Select BDD100K `val` easy positives and clear negatives deterministically from `seed`."""
        rng = DeterministicRNG(seed, self.level_key)
        challenge_id = generate_challenge_id(self.level_key, seed)

        rows = self.config.gridRows
        cols = self.config.gridColumns
        total_tiles = rows * cols
        norm_target = normalize_bdd100k_category(self.config.target)

        if self.config.positiveCount is not None:
            pos_count = self.config.positiveCount
        else:
            p_min, p_max = self.config.positiveCountRange
            pos_count = rng.fork("pos_count").randint(p_min, p_max)

        selected = self.dataset.select_easy_grid_samples(
            rng=rng.fork("selection"),
            target_class=norm_target,
            total_tiles=total_tiles,
            positive_count=pos_count,
            min_easy_area_ratio=self.config.minEasyAreaRatio,
            allow_duplicates=self.config.allowDuplicates,
        )

        asset_paths: list[str] = []
        assets_map: dict[str, Image.Image] = {}
        tile_meta: list[TilePrivateMetadata] = []
        correct_indices: list[int] = []

        for idx, (frame, is_positive, eval_meta) in enumerate(selected):
            if frame.source_split != "val":
                raise BDD100KDataSplitError(
                    f"Data leakage blocked: frame '{frame.name}' has source_split='{frame.source_split}'."
                )
            rel_asset = asset_relpath_for_index(idx, ext="webp")
            asset_paths.append(rel_asset)

            img = self.dataset.load_image(frame)
            if img.size != (self.config.tileWidth, self.config.tileHeight):
                img = img.resize(
                    (self.config.tileWidth, self.config.tileHeight),
                    resample=Image.Resampling.BILINEAR,
                )
            assets_map[rel_asset] = img

            if is_positive:
                correct_indices.append(idx)

            tile_meta.append(
                TilePrivateMetadata(
                    tileIndex=idx,
                    asset=rel_asset,
                    sourceId=frame.name,
                    sourceImage=frame.name,
                    source_image_id=frame.name,
                    source_path=frame.source_path,
                    source_dataset=frame.source_dataset,
                    source_split=frame.source_split,
                    project_role=frame.project_role,
                    sequence_id=frame.sequence_id,
                    datasetSource="bdd100k",
                    targetClass=norm_target,
                    classes=sorted(frame.categories),
                    difficulty="easy",
                    attributes=list(eval_meta["difficulty_tags"]),
                    maxTargetAreaRatio=float(eval_meta["max_target_area_ratio"]),
                    weather=frame.weather,
                    timeofday=frame.timeofday,
                    isPositive=is_positive,
                )
            )

        public_challenge = PublicChallenge(
            schemaVersion=1,
            id=challenge_id,
            level=1,
            variant="street-grid",
            type="image-selection",
            instruction=format_grid_instruction(norm_target),
            seed=seed,
            assets=asset_paths,
            ui=PublicUIConfig(
                rows=rows,
                columns=cols,
                selectionMode="multiple",
            ),
        )

        first_tile = tile_meta[0] if tile_meta else None
        private_answer = PrivateAnswer(
            challengeId=challenge_id,
            levelKey=self.level_key,
            datasetSource="bdd100k",
            dataset="BDD100K",
            source_dataset="BDD100K",
            source_split="val",
            project_role="held_out_benchmark",
            source_image_id=first_tile.source_image_id if first_tile else None,
            source_path=first_tile.source_path if first_tile else None,
            sequence_id=first_tile.sequence_id if first_tile else None,
            correctSelection=correct_indices,
            targetClass=norm_target,
            tiles=tile_meta,
        )

        return ChallengeBundle(
            public_challenge=public_challenge,
            private_answer=private_answer,
            assets=assets_map,
            lossless_webp=True,
        )

    def generate_batch(self, count: int, base_seed: int) -> list[ChallengeBundle]:
        """Generate `count` deterministic Level 1 challenges starting from `base_seed`."""
        return [self.generate_one(base_seed + i) for i in range(count)]
