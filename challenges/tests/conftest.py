"""Shared pytest fixtures for testing BDD100K indexing, filtering, and challenge packaging in ephemeral tmp_path."""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw
import pytest


@pytest.fixture()
def sample_bdd100k_root(tmp_path: Path) -> Path:
    """Create an ephemeral BDD100K directory structure (images/100k/val + labels/det_20/det_val.json) in tmp_path."""
    bdd_root = tmp_path / "bdd100k_sample"
    img_dir = bdd_root / "images" / "100k" / "val"
    lbl_dir = bdd_root / "labels" / "det_20"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    frames_spec: list[dict] = []

    # 1. Easy motorcycle frames (10 frames: daytime, clear, large unoccluded/untruncated box)
    for i in range(10):
        fname = f"bdd_easy_pos_{i:03d}.jpg"
        frames_spec.append(
            {
                "name": fname,
                "attributes": {
                    "weather": "clear",
                    "scene": "city street",
                    "timeofday": "daytime",
                },
                "labels": [
                    {
                        "id": f"m_{i}",
                        "category": "motorcycle",
                        "attributes": {"occluded": False, "truncated": False},
                        "box2d": {"x1": 300.0, "y1": 220.0, "x2": 580.0, "y2": 500.0},
                    },
                    {
                        "id": f"c_{i}",
                        "category": "car",
                        "attributes": {"occluded": False, "truncated": False},
                        "box2d": {"x1": 50.0, "y1": 260.0, "x2": 220.0, "y2": 420.0},
                    },
                ],
            }
        )

    # 2. Hard motorcycle frames (10 frames: small/distant, occluded, truncated, night, rain, confusable bicycle)
    hard_configs = [
        ("night", "clear", True, False, (500.0, 320.0, 560.0, 380.0), ["bicycle"]),
        ("daytime", "rainy", True, False, (420.0, 300.0, 490.0, 380.0), []),
        ("dawn/dusk", "overcast", False, True, (10.0, 310.0, 85.0, 390.0), []),
        ("night", "rainy", False, False, (600.0, 340.0, 680.0, 430.0), ["car"]),
        ("daytime", "foggy", True, False, (520.0, 330.0, 565.0, 372.0), []),
        ("night", "clear", False, True, (1200.0, 300.0, 1278.0, 380.0), []),
        ("dawn/dusk", "rainy", False, False, (480.0, 310.0, 560.0, 400.0), []),
        ("daytime", "clear", True, False, (610.0, 350.0, 650.0, 386.0), ["bicycle", "rider"]),
        ("night", "overcast", True, False, (400.0, 290.0, 460.0, 350.0), []),
        ("daytime", "rainy", False, False, (580.0, 345.0, 660.0, 430.0), ["bicycle"]),
    ]
    for i, (tod, weather, occ, trunc, box, extra_cats) in enumerate(hard_configs):
        fname = f"bdd_hard_pos_{i:03d}.jpg"
        labels = [
            {
                "id": f"hm_{i}",
                "category": "motorcycle",
                "attributes": {"occluded": occ, "truncated": trunc},
                "box2d": {"x1": box[0], "y1": box[1], "x2": box[2], "y2": box[3]},
            }
        ]
        for j, ecat in enumerate(extra_cats):
            labels.append(
                {
                    "id": f"he_{i}_{j}",
                    "category": ecat,
                    "attributes": {"occluded": False, "truncated": False},
                    "box2d": {"x1": 100.0 + j * 80, "y1": 280.0, "x2": 170.0 + j * 80, "y2": 360.0},
                }
            )
        frames_spec.append(
            {
                "name": fname,
                "attributes": {"weather": weather, "scene": "city street", "timeofday": tod},
                "labels": labels,
            }
        )

    # 3. Clear daytime negative frames (20 frames: car, bus, traffic light, traffic sign; no motorcycle/rider)
    neg_cats = ["car", "bus", "traffic light", "truck", "traffic sign"]
    for i in range(20):
        fname = f"bdd_easy_neg_{i:03d}.jpg"
        cat = neg_cats[i % len(neg_cats)]
        frames_spec.append(
            {
                "name": fname,
                "attributes": {"weather": "clear", "scene": "city street", "timeofday": "daytime"},
                "labels": [
                    {
                        "id": f"en_{i}",
                        "category": cat,
                        "attributes": {"occluded": False, "truncated": False},
                        "box2d": {"x1": 240.0, "y1": 200.0, "x2": 520.0, "y2": 440.0},
                    }
                ],
            }
        )

    # 4. Hard negative frames (20 frames: bicycle distractors, night, rain, dense traffic; no motorcycle)
    for i in range(20):
        fname = f"bdd_hard_neg_{i:03d}.jpg"
        tod = "night" if i % 2 == 0 else "dawn/dusk"
        weather = "rainy" if i % 3 == 0 else "overcast"
        cat = "bicycle" if i % 2 == 0 else "car"
        frames_spec.append(
            {
                "name": fname,
                "attributes": {"weather": weather, "scene": "city street", "timeofday": tod},
                "labels": [
                    {
                        "id": f"hn_{i}",
                        "category": cat,
                        "attributes": {"occluded": True, "truncated": False},
                        "box2d": {"x1": 310.0, "y1": 260.0, "x2": 430.0, "y2": 390.0},
                    }
                ],
            }
        )

    # Create distinct test images on disk for each annotated frame
    for idx, spec in enumerate(frames_spec):
        # Match annotation coordinates, so crop/visibility tests exercise real geometry.
        img = Image.new("RGB", (1280, 720), (40 + (idx * 3) % 150, 70 + (idx * 5) % 140, 110))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20 + (idx % 40), 30, 140 + (idx % 40), 130], fill=(200, 120, 50))
        for label in spec['labels']:
            box=label['box2d']
            draw.rectangle((box['x1'],box['y1'],box['x2'],box['y2']),fill=(200,120,50))
        img.save(img_dir / spec["name"], format="JPEG", quality=95)

    (lbl_dir / "det_val.json").write_text(json.dumps(frames_spec, indent=2), encoding="utf-8")
    return bdd_root
