"""Level 3B — Degraded Vision CAPTCHA builder (real BDD100K `val` images + controlled degradation)."""

from __future__ import annotations

import io
from typing import Sequence
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.ids import asset_relpath_for_index, generate_challenge_id
from challenge_engine.core.image_prep import (
    prepare_context_crop,
    prepare_negative_crop,
)
from challenge_engine.core.random import DeterministicRNG
from challenge_engine.core.schemas import (
    LEVEL_3B_KEY,
    DegradationInfo,
    Level3BConfig,
    PrivateAnswer,
    PublicChallenge,
    PublicUIConfig,
    TilePrivateMetadata,
    TransformationSpec,
)
from challenge_engine.datasets.bdd100k import (
    BDD100KDataSplitError,
    BDD100KDataset,
    CLASS_PROFILES,
    load_bdd100k_dataset,
    normalize_bdd100k_category,
)
from challenge_engine.levels.level_1.generator import format_grid_instruction

_UPSCALE_MAP = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
}


def degrade_image(
    img: Image.Image,
    downsample_width: int,
    downsample_height: int,
    output_width: int = 256,
    output_height: int = 256,
    upscale_method: str = "nearest",
    color_quantization: int | None = None,
    blur_radius: float = 0.0,
    contrast_factor: float = 1.0,
    jpeg_quality: int | None = None,
    partial_mask_ratio: float = 0.0,
) -> Image.Image:
    """Apply controlled degradation (downsample -> nearest-neighbor upscale, plus optional transforms)."""
    work = img.convert("RGB")

    if blur_radius > 0.0:
        work = work.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    if abs(contrast_factor - 1.0) > 1e-6:
        work = ImageEnhance.Contrast(work).enhance(contrast_factor)

    if jpeg_quality is not None and 5 <= jpeg_quality <= 100:
        buf = io.BytesIO()
        work.save(buf, format="JPEG", quality=int(jpeg_quality))
        buf.seek(0)
        with Image.open(buf) as j_img:
            work = j_img.convert("RGB")

    # Primary transformation: downsample to low resolution (e.g., 64, 48, 32, 24, 16, 12, 8)
    small = work.resize(
        (downsample_width, downsample_height),
        resample=Image.Resampling.BOX,
    )

    if color_quantization is not None and color_quantization >= 2:
        small = small.quantize(colors=color_quantization, method=Image.Quantize.MEDIANCUT).convert(
            "RGB"
        )

    # Upscale back to tile display dimensions using nearest-neighbor by default
    resample_mode = _UPSCALE_MAP.get(upscale_method, Image.Resampling.NEAREST)
    degraded = small.resize((output_width, output_height), resample=resample_mode)

    if partial_mask_ratio > 0.0:
        draw = ImageDraw.Draw(degraded)
        mask_w = int(output_width * partial_mask_ratio)
        mask_h = int(output_height * partial_mask_ratio)
        mx0 = (output_width - mask_w) // 2
        my0 = (output_height - mask_h) // 2
        draw.rectangle([mx0, my0, mx0 + mask_w, my0 + mask_h], fill=(64, 64, 64))

    return degraded


class Level3BDegradedVisionGenerator:
    """Applies controlled resolution degradation to real BDD100K `val` street images."""

    level_key = LEVEL_3B_KEY

    def __init__(self, config: Level3BConfig, dataset: BDD100KDataset | None = None) -> None:
        self.config = config
        if self.config.sourceSplit != "val":
            raise BDD100KDataSplitError(
                f"Level 3B requires BDD100K 'val' split only, got '{self.config.sourceSplit}'."
            )
        if dataset is not None:
            if getattr(dataset, "source_split", "val") != "val":
                raise BDD100KDataSplitError(
                    f"Level 3B dataset must use 'val' split only, got '{dataset.source_split}'."
                )
            self.dataset = dataset
        else:
            self.dataset = load_bdd100k_dataset(
                self.config.bdd100kRoot,
                split=self.config.sourceSplit,
            )

    def generate_one(
        self,
        seed: int,
        resolution: int | None = None,
        extra_id_discriminator: str = "",
    ) -> ChallengeBundle:
        """Generate a single deterministic Level 3B degraded vision challenge from BDD100K `val`.

        Tile selection and grid ordering depend ONLY on `seed` (not `resolution`),
        so multi-resolution comparisons across [64, 48, 32, 24, 16, 12, 8] transform
        the exact same underlying BDD100K validation frames in the exact same grid layout.
        """
        res = resolution if resolution is not None else self.config.resolution
        if res not in self.config.supportedResolutions:
            raise ValueError(
                f"Unsupported resolution {res}; allowed: {self.config.supportedResolutions}"
            )

        selection_rng = DeterministicRNG(seed, f"{self.level_key}:selection")
        challenge_id = generate_challenge_id(
            self.level_key,
            seed,
            extra_discriminator=extra_id_discriminator,
        )

        rows = self.config.gridRows
        cols = self.config.gridColumns
        total_tiles = rows * cols

        if getattr(self.config, "targets", None):
            norm_target = normalize_bdd100k_category(selection_rng.fork("target").choice(self.config.targets))
        else:
            norm_target = normalize_bdd100k_category(self.config.target)
        profile = CLASS_PROFILES.get(norm_target)

        selected = self.dataset.select_easy_grid_samples(
            rng=selection_rng,
            target_class=norm_target,
            total_tiles=total_tiles,
            positive_count=self.config.positiveCount,
            min_easy_area_ratio=self.config.minEasyAreaRatio,
            allow_duplicates=self.config.allowDuplicates,
        )

        transformation_spec = TransformationSpec(
            type="downsample_upscale",
            resolution=res,
            upscale=self.config.upscaleMethod,
            colorQuantization=self.config.colorQuantization,
            blurRadius=self.config.blurRadius,
            contrastFactor=self.config.contrastFactor,
            jpegQuality=self.config.jpegQuality,
            partialMaskRatio=self.config.partialMaskRatio,
        )

        degradation_info = DegradationInfo(
            method="downsample_upscale",
            downsampleWidth=res,
            downsampleHeight=res,
            upscaleMethod=self.config.upscaleMethod,
            colorQuantization=self.config.colorQuantization,
            blurRadius=self.config.blurRadius,
            contrastFactor=self.config.contrastFactor,
            jpegQuality=self.config.jpegQuality,
            partialMaskRatio=self.config.partialMaskRatio,
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

            orig_img = self.dataset.load_image(frame)
            # Use seed (independent of resolution) so multi-resolution comparisons use identical crops
            crop_rng = DeterministicRNG(seed, f"level_3b:crop:{idx}")

            if is_positive:
                correct_indices.append(idx)
                target_box = eval_meta.get("target_box")
                if target_box is None:
                    for obj in frame.objects:
                        if obj.category == norm_target:
                            target_box = obj.box2d
                            break
                context_factor = profile.default_context_factor if profile else 1.0
                crop_res = prepare_context_crop(
                    img=orig_img,
                    target_box=target_box,
                    output_size=(self.config.tileWidth, self.config.tileHeight),
                    context_padding=context_factor,
                    rng=crop_rng,
                )
                rendered_metrics = crop_res.target_metrics
                r_size = rendered_metrics.rendered_max_dim if rendered_metrics else None
                r_w = rendered_metrics.rendered_width if rendered_metrics else None
                r_h = rendered_metrics.rendered_height if rendered_metrics else None
            else:
                confusable = profile.confusable_distractors if profile else ()
                forbidden = [
                    obj.box2d
                    for obj in frame.objects
                    if obj.category == norm_target or obj.category in confusable
                ]
                crop_res = prepare_negative_crop(
                    img=orig_img,
                    output_size=(self.config.tileWidth, self.config.tileHeight),
                    forbidden_boxes=forbidden,
                    rng=crop_rng,
                )
                context_factor = None
                r_size = None
                r_w = None
                r_h = None

            # Apply controlled degradation to the clean 1:1 square crop
            degraded_img = degrade_image(
                img=crop_res.image,
                downsample_width=res,
                downsample_height=res,
                output_width=self.config.tileWidth,
                output_height=self.config.tileHeight,
                upscale_method=self.config.upscaleMethod,
                color_quantization=self.config.colorQuantization,
                blur_radius=self.config.blurRadius,
                contrast_factor=self.config.contrastFactor,
                jpeg_quality=self.config.jpegQuality,
                partial_mask_ratio=self.config.partialMaskRatio,
            )
            assets_map[rel_asset] = degraded_img

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
                    attributes=list(eval_meta.get("difficulty_tags", [])),
                    maxTargetAreaRatio=float(eval_meta.get("max_target_area_ratio", 0.0)),
                    weather=frame.weather,
                    timeofday=frame.timeofday,
                    isPositive=is_positive,
                    crop_box=list(crop_res.crop_window),
                    crop_context_factor=context_factor,
                    rendered_object_size=r_size,
                    rendered_object_width=r_w,
                    rendered_object_height=r_h,
                    difficulty_budget_factors=[],
                    transformation=transformation_spec,
                    degradation=degradation_info,
                )
            )

        public_challenge = PublicChallenge(
            schemaVersion=1,
            id=challenge_id,
            level=3,
            variant="degraded-vision",
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
        first_source = first_tile.sourceImage if first_tile else None
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
            target=norm_target,
            source_image=first_source,
            sourceImage=first_source,
            transformation=transformation_spec,
            degradation=degradation_info,
            tiles=tile_meta,
        )

        return ChallengeBundle(
            public_challenge=public_challenge,
            private_answer=private_answer,
            assets=assets_map,
            lossless_webp=True,
        )

    def generate_multi_resolution_series(
        self,
        seed: int,
        resolutions: Sequence[int] = (64, 48, 32, 24, 16, 12, 8),
    ) -> list[ChallengeBundle]:
        """Generate identical BDD100K `val` challenge grids degraded across multiple resolutions."""
        return [
            self.generate_one(
                seed=seed,
                resolution=res,
                extra_id_discriminator=f"res_{res}",
            )
            for res in resolutions
        ]

    def generate_batch(self, count: int, base_seed: int) -> list[ChallengeBundle]:
        """Generate `count` deterministic challenges (or multi-resolution series if configured)."""
        if self.config.batchResolutions:
            bundles: list[ChallengeBundle] = []
            for i in range(count):
                bundles.extend(
                    self.generate_multi_resolution_series(
                        seed=base_seed + i,
                        resolutions=self.config.batchResolutions,
                    )
                )
            return bundles
        return [self.generate_one(base_seed + i) for i in range(count)]
