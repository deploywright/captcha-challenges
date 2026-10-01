"""Asset-backed packager for Level 2B — Adelson Checker Shadow Illusion.

IMPORTANT:
Level 2B is NOT procedurally generated. It loads the existing Adelson Checker Shadow
Illusion asset and documented provenance metadata from `Challenges/assets/level-2b/`.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np
from PIL import Image

from challenge_engine.core.config import PROJECT_ROOT
from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.ids import asset_relpath_for_index, generate_challenge_id
from challenge_engine.core.schemas import (
    LEVEL_2B_KEY,
    IllusionMetadata,
    Level2BAssetMetadata,
    Level2BConfig,
    PrivateAnswer,
    PublicChallenge,
    PublicUIConfig,
    SquareMeasurement,
)


class Level2BAssetNotFoundError(FileNotFoundError):
    """Raised when the required static Adelson Checker Shadow Illusion asset or metadata is missing."""


@dataclass
class Level2BAssetStatus:
    """Diagnostic status for the Level 2B static Adelson Checker Shadow Illusion asset."""

    available: bool
    asset_path: Path
    metadata_path: Path
    message: str


def compute_luminance(rgb: tuple[float, float, float] | list[float]) -> float:
    """Compute ITU-R BT.709 relative luminance from RGB values in [0, 255]."""
    r, g, b = rgb[0], rgb[1], rgb[2]
    return float(0.2126 * r + 0.7152 * g + 0.0722 * b)


def measure_box_rgb_and_luminance(
    img: Image.Image,
    box: list[int] | tuple[int, int, int, int],
) -> tuple[list[float], float]:
    """Sample mean RGB and luminance inside `[x1, y1, x2, y2]`."""
    x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    arr = np.asarray(img.convert("RGB"), dtype=np.float64)
    patch = arr[y1:y2, x1:x2]
    if patch.size == 0:
        raise ValueError(f"Empty sampling box: {box}")
    mean_rgb = [float(patch[:, :, i].mean()) for i in range(3)]
    lum = compute_luminance(mean_rgb)
    return mean_rgb, lum


def _resolve_path(raw_path: str | Path) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


def inspect_level_2b_asset_status(config: Level2BConfig | None = None) -> Level2BAssetStatus:
    """Check whether the existing Adelson Checker Shadow Illusion asset and metadata are present."""
    cfg = config or Level2BConfig()
    asset_path = _resolve_path(cfg.assetPath)
    meta_path = _resolve_path(cfg.metadataPath)

    if not asset_path.exists():
        return Level2BAssetStatus(
            available=False,
            asset_path=asset_path,
            metadata_path=meta_path,
            message=f"Missing Adelson Checker Shadow asset at '{asset_path}'.",
        )
    if not meta_path.exists():
        return Level2BAssetStatus(
            available=False,
            asset_path=asset_path,
            metadata_path=meta_path,
            message=f"Missing Level 2B provenance metadata at '{meta_path}'.",
        )
    return Level2BAssetStatus(
        available=True,
        asset_path=asset_path,
        metadata_path=meta_path,
        message=f"Adelson Checker Shadow asset ready at '{asset_path}'.",
    )


class Level2BCheckerShadowGenerator:
    """Packages the existing Adelson Checker Shadow Illusion asset without procedural synthesis."""

    level_key = LEVEL_2B_KEY

    def __init__(self, config: Level2BConfig) -> None:
        self.config = config
        self.asset_path = _resolve_path(self.config.assetPath)
        self.metadata_path = _resolve_path(self.config.metadataPath)
        self.asset_metadata = self._load_and_verify_metadata()

    def _load_and_verify_metadata(self) -> Level2BAssetMetadata:
        if not self.asset_path.exists():
            raise Level2BAssetNotFoundError(
                f"Level 2B Adelson Checker Shadow asset not found at '{self.asset_path}'. "
                f"Level 2B must use an existing Adelson Checker Shadow Illusion image file; "
                f"procedural synthesis is disabled."
            )
        if not self.metadata_path.exists():
            raise Level2BAssetNotFoundError(
                f"Level 2B provenance metadata file not found at '{self.metadata_path}'."
            )
        raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return Level2BAssetMetadata.model_validate(raw)

    def _load_existing_asset_image(self) -> Image.Image:
        with Image.open(self.asset_path) as img:
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                return bg
            return img.convert("RGB")

    def generate_one(self, seed: int) -> ChallengeBundle:
        """Package the existing Adelson Checker Shadow Illusion asset into a challenge bundle."""
        challenge_id = generate_challenge_id(self.level_key, seed)
        img = self._load_existing_asset_image()

        regions = self.asset_metadata.regions or {}
        box_a = regions.get("square_a_interior", [240, 110, 250, 120])
        box_b = regions.get("square_b_interior", [230, 195, 240, 205])

        rgb_a, lum_a = measure_box_rgb_and_luminance(img, box_a)
        rgb_b, lum_b = measure_box_rgb_and_luminance(img, box_b)

        lum_diff = abs(lum_a - lum_b)
        rgb_diff = max(abs(a - b) for a, b in zip(rgb_a, rgb_b))

        rel_asset = asset_relpath_for_index(0, ext="webp")
        options = list(self.config.options)
        yes_index = next(i for i, opt in enumerate(options) if opt.lower() == "yes")

        public_challenge = PublicChallenge(
            schemaVersion=1,
            id=challenge_id,
            level=2,
            variant="checker-shadow",
            type="single-choice",
            instruction=self.config.instruction or self.asset_metadata.question,
            seed=seed,
            assets=[rel_asset],
            ui=PublicUIConfig(
                rows=1,
                columns=1,
                selectionMode="single",
                options=options,
            ),
        )

        private_answer = PrivateAnswer(
            challengeId=challenge_id,
            levelKey=self.level_key,
            datasetSource="adelson-static-asset",
            correctSelection=[yes_index],
            answer=options[yes_index],
            illusion=IllusionMetadata(
                assetName=self.asset_metadata.name,
                source=self.asset_metadata.source,
                license=self.asset_metadata.license,
                assetFile=self.asset_path.name,
                proceduralGenerationUsed=False,
                squareA=SquareMeasurement(
                    label="A",
                    safeInteriorBox=box_a,
                    measuredRgb=[round(v, 4) for v in rgb_a],
                    measuredLuminance=round(lum_a, 4),
                ),
                squareB=SquareMeasurement(
                    label="B",
                    safeInteriorBox=box_b,
                    measuredRgb=[round(v, 4) for v in rgb_b],
                    measuredLuminance=round(lum_b, 4),
                ),
                luminanceDifference=round(lum_diff, 6),
                rgbMaxDifference=round(rgb_diff, 6),
                tolerance=self.config.luminanceTolerance,
            ),
        )

        return ChallengeBundle(
            public_challenge=public_challenge,
            private_answer=private_answer,
            assets={rel_asset: img},
            lossless_webp=True,
        )

    def generate_batch(self, count: int, base_seed: int) -> list[ChallengeBundle]:
        """Package `count` Level 2B challenge bundles starting from `base_seed`."""
        return [self.generate_one(base_seed + i) for i in range(count)]
