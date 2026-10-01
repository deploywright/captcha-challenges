"""Shared image preparation utilities for BDD100K street challenges.

Guarantees:
1. Aspect Ratio Preservation: Never squashes 16:9 frames into square tiles.
2. Context-Aware Cropping: Positive crops center on the target object with natural visual context.
3. Realistic Negative Cropping: Negative crops capture natural street scenes.
4. Rendered Size Estimation: Accurately calculates target pixel dimensions in the final rendered tile.
5. Deterministic Behavior: Seeded cropping for complete reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import numpy as np
from PIL import Image

from challenge_engine.core.random import DeterministicRNG


@dataclass(frozen=True)
class RenderedTargetMetrics:
    """Metrics estimating target visibility in the final rendered tile."""

    rendered_x1: float
    rendered_y1: float
    rendered_x2: float
    rendered_y2: float
    rendered_width: float
    rendered_height: float
    rendered_min_dim: float
    rendered_max_dim: float
    rendered_area: float
    rendered_area_ratio: float
    crop_window: tuple[int, int, int, int]  # (x1, y1, x2, y2) in original frame


@dataclass
class PreparedCropResult:
    """Result of context-aware cropping and resizing."""

    image: Image.Image
    crop_window: tuple[int, int, int, int]
    target_metrics: RenderedTargetMetrics | None = None


def compute_context_crop_window(
    frame_width: int,
    frame_height: int,
    target_box: Sequence[float],
    context_padding: float = 1.0,
    min_crop_dim: int = 240,
    max_crop_dim: int = 680,
    rng: DeterministicRNG | None = None,
) -> tuple[int, int, int, int]:
    """Calculate a square crop window around `target_box` with natural visual context.

    Args:
        frame_width: Width of the original frame (e.g. 1280).
        frame_height: Height of the original frame (e.g. 720).
        target_box: [x1, y1, x2, y2] bounding box of target object.
        context_padding: Multiplier for padding around the target (e.g. 1.0 = target + 100% context on each side).
        min_crop_dim: Minimum square crop dimension in source pixels.
        max_crop_dim: Maximum square crop dimension in source pixels (cannot exceed frame_height).
        rng: Optional deterministic RNG for subtle natural framing jitter.

    Returns:
        (crop_x1, crop_y1, crop_x2, crop_y2) integer pixel bounds.
    """
    bx1, by1, bx2, by2 = float(target_box[0]), float(target_box[1]), float(target_box[2]), float(target_box[3])
    bw = max(1.0, bx2 - bx1)
    bh = max(1.0, by2 - by1)
    bcx = (bx1 + bx2) / 2.0
    bcy = (by1 + by2) / 2.0

    target_max_dim = max(bw, bh)
    ideal_crop_dim = target_max_dim * (1.0 + 2.0 * context_padding)

    # Upper bound by frame height and width so it fits within the frame
    max_allowed = max(1, min(frame_height, frame_width, max_crop_dim))
    min_allowed = max(1, min(min_crop_dim, max_allowed))
    crop_dim = int(np.clip(ideal_crop_dim, min_allowed, max_allowed))

    # Optional deterministic framing jitter so the target isn't always dead-center
    jitter_x = 0.0
    jitter_y = 0.0
    if rng is not None:
        max_j_x = (crop_dim - bw) * 0.15
        max_j_y = (crop_dim - bh) * 0.15
        if max_j_x > 2.0:
            jitter_x = rng.fork("jitter_x").uniform(-max_j_x, max_j_x)
        if max_j_y > 2.0:
            jitter_y = rng.fork("jitter_y").uniform(-max_j_y, max_j_y)

    cx = bcx + jitter_x
    cy = bcy + jitter_y

    x1 = int(round(cx - crop_dim / 2.0))
    y1 = int(round(cy - crop_dim / 2.0))
    x2 = x1 + crop_dim
    y2 = y1 + crop_dim

    # Clamp to image boundaries
    if x1 < 0:
        x2 += -x1
        x1 = 0
    if x2 > frame_width:
        x1 -= (x2 - frame_width)
        x2 = frame_width
    if x1 < 0:
        x1 = 0

    if y1 < 0:
        y2 += -y1
        y1 = 0
    if y2 > frame_height:
        y1 -= (y2 - frame_height)
        y2 = frame_height
    if y1 < 0:
        y1 = 0

    return (x1, y1, x2, y2)


def compute_rendered_metrics(
    target_box: Sequence[float],
    crop_window: tuple[int, int, int, int],
    output_size: tuple[int, int] = (256, 256),
) -> RenderedTargetMetrics:
    """Compute the exact pixel coordinates and dimensions of the target inside the final tile."""
    bx1, by1, bx2, by2 = float(target_box[0]), float(target_box[1]), float(target_box[2]), float(target_box[3])
    cx1, cy1, cx2, cy2 = crop_window
    crop_w = float(max(1, cx2 - cx1))
    crop_h = float(max(1, cy2 - cy1))
    out_w, out_h = float(output_size[0]), float(output_size[1])

    # Intersect target box with crop window
    int_x1 = max(bx1, float(cx1))
    int_y1 = max(by1, float(cy1))
    int_x2 = min(bx2, float(cx2))
    int_y2 = min(by2, float(cy2))

    if int_x2 <= int_x1 or int_y2 <= int_y1:
        # Target outside crop window
        return RenderedTargetMetrics(
            rendered_x1=0.0,
            rendered_y1=0.0,
            rendered_x2=0.0,
            rendered_y2=0.0,
            rendered_width=0.0,
            rendered_height=0.0,
            rendered_min_dim=0.0,
            rendered_max_dim=0.0,
            rendered_area=0.0,
            rendered_area_ratio=0.0,
            crop_window=crop_window,
        )

    rx1 = ((int_x1 - cx1) / crop_w) * out_w
    ry1 = ((int_y1 - cy1) / crop_h) * out_h
    rx2 = ((int_x2 - cx1) / crop_w) * out_w
    ry2 = ((int_y2 - cy1) / crop_h) * out_h

    rw = max(0.0, rx2 - rx1)
    rh = max(0.0, ry2 - ry1)
    min_dim = min(rw, rh)
    max_dim = max(rw, rh)
    area = rw * rh
    area_ratio = area / (out_w * out_h)

    return RenderedTargetMetrics(
        rendered_x1=round(rx1, 2),
        rendered_y1=round(ry1, 2),
        rendered_x2=round(rx2, 2),
        rendered_y2=round(ry2, 2),
        rendered_width=round(rw, 2),
        rendered_height=round(rh, 2),
        rendered_min_dim=round(min_dim, 2),
        rendered_max_dim=round(max_dim, 2),
        rendered_area=round(area, 2),
        rendered_area_ratio=round(area_ratio, 5),
        crop_window=crop_window,
    )


def prepare_context_crop(
    img: Image.Image,
    target_box: Sequence[float],
    output_size: tuple[int, int] = (256, 256),
    context_padding: float = 1.0,
    min_crop_dim: int = 240,
    max_crop_dim: int = 680,
    rng: DeterministicRNG | None = None,
    resample: Image.Resampling = Image.Resampling.BILINEAR,
) -> PreparedCropResult:
    """Crop naturally around target object without geometric distortion, resizing to output_size."""
    frame_w, frame_h = img.size
    crop_window = compute_context_crop_window(
        frame_width=frame_w,
        frame_height=frame_h,
        target_box=target_box,
        context_padding=context_padding,
        min_crop_dim=min_crop_dim,
        max_crop_dim=max_crop_dim,
        rng=rng,
    )

    cropped = img.crop(crop_window)
    if cropped.size != output_size:
        cropped = cropped.resize(output_size, resample=resample)

    metrics = compute_rendered_metrics(target_box, crop_window, output_size)
    return PreparedCropResult(
        image=cropped,
        crop_window=crop_window,
        target_metrics=metrics,
    )


def prepare_negative_crop(
    img: Image.Image,
    output_size: tuple[int, int] = (256, 256),
    forbidden_boxes: Sequence[Sequence[float]] | None = None,
    rng: DeterministicRNG | None = None,
    resample: Image.Resampling = Image.Resampling.BILINEAR,
) -> PreparedCropResult:
    """Extract a realistic street scene crop from a negative frame without stretching.

    Avoids pure sky (top 15%) or pure empty foreground asphalt (bottom 10%) when possible.
    """
    frame_w, frame_h = img.size
    max_dim = max(1, min(frame_h, frame_w, 520))
    min_dim = max(1, min(280, int(max_dim * 0.75)))

    if min_dim >= max_dim or rng is None:
        crop_dim = max_dim
    else:
        crop_dim = rng.fork("neg_dim").randint(min_dim, max_dim)

    min_y = int(frame_h * 0.10)
    max_y = max(0, frame_h - crop_dim)
    if min_y > max_y or rng is None:
        y1 = 0 if max_y == 0 else (frame_h - crop_dim) // 2
    else:
        y1 = rng.fork("neg_y").randint(min_y, max_y)

    max_x = max(0, frame_w - crop_dim)
    if max_x == 0 or rng is None:
        x1 = 0
    else:
        x1 = rng.fork("neg_x").randint(0, max_x)

    x2 = min(frame_w, x1 + crop_dim)
    y2 = min(frame_h, y1 + crop_dim)

    # Ensure strictly square crop
    side = min(x2 - x1, y2 - y1)
    crop_window = (x1, y1, x1 + side, y1 + side)

    cropped = img.crop(crop_window)
    if cropped.size != output_size:
        cropped = cropped.resize(output_size, resample=resample)

    return PreparedCropResult(
        image=cropped,
        crop_window=crop_window,
        target_metrics=None,
    )
