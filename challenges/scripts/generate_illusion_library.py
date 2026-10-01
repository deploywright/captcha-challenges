"""Generates the canonical Level 2B Visual Illusions library assets and metadata.

Produces 6 canonical illusions with mathematical ground truth:
1. checker-shadow (existing Adelson 1995 asset)
2. muller-lyer (Franz Carl Müller-Lyer 1889)
3. ebbinghaus (Hermann Ebbinghaus 1902 / Edward Titchener 1901)
4. ponzo (Mario Ponzo 1911)
5. simultaneous-contrast (Michel Eugène Chevreul 1839)
6. cafe-wall (Richard Gregory & Priscilla Heard 1979)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "level-2b"


def generate_muller_lyer() -> tuple[Image.Image, dict]:
    """Müller-Lyer Illusion: equal shaft lengths with inward vs outward fins."""
    width, height = 600, 480
    img = Image.new("RGB", (width, height), (248, 249, 250))
    draw = ImageDraw.Draw(img)

    # Line A: outward-pointing fins (>---<) -> appears shorter
    # Line B: inward-pointing fins (<--->) -> appears longer
    x_start = 170
    x_end = 430
    shaft_len = x_end - x_start  # 260px
    y_a = 160
    y_b = 320
    fin_len = 45
    fin_angle = math.radians(35)
    dx = fin_len * math.cos(fin_angle)
    dy = fin_len * math.sin(fin_angle)

    line_w = 4
    # Draw Line A
    draw.line([(x_start, y_a), (x_end, y_a)], fill=(20, 24, 32), width=line_w)
    # Fins at start of A (pointing right into the shaft)
    draw.line([(x_start, y_a), (x_start + dx, y_a - dy)], fill=(20, 24, 32), width=line_w)
    draw.line([(x_start, y_a), (x_start + dx, y_a + dy)], fill=(20, 24, 32), width=line_w)
    # Fins at end of A (pointing left into the shaft)
    draw.line([(x_end, y_a), (x_end - dx, y_a - dy)], fill=(20, 24, 32), width=line_w)
    draw.line([(x_end, y_a), (x_end - dx, y_a + dy)], fill=(20, 24, 32), width=line_w)

    # Draw Line B
    draw.line([(x_start, y_b), (x_end, y_b)], fill=(20, 24, 32), width=line_w)
    # Fins at start of B (pointing left away from shaft)
    draw.line([(x_start, y_b), (x_start - dx, y_b - dy)], fill=(20, 24, 32), width=line_w)
    draw.line([(x_start, y_b), (x_start - dx, y_b + dy)], fill=(20, 24, 32), width=line_w)
    # Fins at end of B (pointing right away from shaft)
    draw.line([(x_end, y_b), (x_end + dx, y_b - dy)], fill=(20, 24, 32), width=line_w)
    draw.line([(x_end, y_b), (x_end + dx, y_b + dy)], fill=(20, 24, 32), width=line_w)

    font = ImageFont.load_default()
    draw.text((60, y_a - 8), "Line A", fill=(30, 41, 59), font=font)
    draw.text((60, y_b - 8), "Line B", fill=(30, 41, 59), font=font)

    metadata = {
        "illusion_type": "muller-lyer",
        "name": "Müller-Lyer Illusion",
        "author": "Franz Carl Müller-Lyer (1889)",
        "source": "Archiv für Physiologie (1889). Canonical geometric optical illusion.",
        "license": "Public Domain. Canonical scientific benchmark illusion.",
        "asset_file": "muller-lyer.png",
        "question": "Are horizontal lines A and B the same length?",
        "answer": "yes",
        "options": ["Yes", "No"],
        "ground_truth_metric": "shaft_pixel_length",
        "measured_values": {
            "line_a_length": float(shaft_len),
            "line_b_length": float(shaft_len),
            "difference": 0.0,
            "line_a_span": [x_start, y_a, x_end, y_a],
            "line_b_span": [x_start, y_b, x_end, y_b],
        },
        "explanation": "Both central horizontal line shafts are exactly 260 pixels long. The inward vs outward orientation of the tail fins produces a powerful perceptual illusion of differing lengths.",
    }
    return img, metadata


def generate_ebbinghaus() -> tuple[Image.Image, dict]:
    """Ebbinghaus Illusion: two identical center circles surrounded by large vs small inducers."""
    width, height = 640, 480
    img = Image.new("RGB", (width, height), (248, 249, 250))
    draw = ImageDraw.Draw(img)

    # Target circles
    c1_x, c1_y = 190, 240
    c2_x, c2_y = 450, 240
    target_r = 30  # diameter 60px
    target_color = (235, 115, 35)

    # Surrounding Circle 1: 6 large inducers (radius 55px, distance 115px)
    n_large = 6
    large_r = 52
    dist_large = 112
    inducer_color = (148, 163, 184)
    for i in range(n_large):
        ang = (2 * math.pi / n_large) * i
        ix = c1_x + dist_large * math.cos(ang)
        iy = c1_y + dist_large * math.sin(ang)
        draw.ellipse([ix - large_r, iy - large_r, ix + large_r, iy + large_r], fill=inducer_color)

    # Surrounding Circle 2: 8 small inducers (radius 18px, distance 62px)
    n_small = 8
    small_r = 16
    dist_small = 60
    for i in range(n_small):
        ang = (2 * math.pi / n_small) * i + math.pi / 8
        ix = c2_x + dist_small * math.cos(ang)
        iy = c2_y + dist_small * math.sin(ang)
        draw.ellipse([ix - small_r, iy - small_r, ix + small_r, iy + small_r], fill=inducer_color)

    # Draw target orange circles on top
    draw.ellipse([c1_x - target_r, c1_y - target_r, c1_x + target_r, c1_y + target_r], fill=target_color)
    draw.ellipse([c2_x - target_r, c2_y - target_r, c2_x + target_r, c2_y + target_r], fill=target_color)

    font = ImageFont.load_default()
    draw.text((c1_x - 12, c1_y + target_r + 80), "Circle A", fill=(30, 41, 59), font=font)
    draw.text((c2_x - 12, c2_y + target_r + 80), "Circle B", fill=(30, 41, 59), font=font)

    metadata = {
        "illusion_type": "ebbinghaus",
        "name": "Ebbinghaus Illusion",
        "author": "Hermann Ebbinghaus (1902) / Edward Titchener (1901)",
        "source": "Grundzüge der Psychologie (1902). Canonical size-contrast illusion.",
        "license": "Public Domain. Canonical scientific benchmark illusion.",
        "asset_file": "ebbinghaus.png",
        "question": "Are the two orange center circles the same size?",
        "answer": "yes",
        "options": ["Yes", "No"],
        "ground_truth_metric": "circle_diameter",
        "measured_values": {
            "circle_a_diameter": float(target_r * 2),
            "circle_b_diameter": float(target_r * 2),
            "circle_a_radius": float(target_r),
            "circle_b_radius": float(target_r),
            "difference": 0.0,
            "circle_a_center": [c1_x, c1_y],
            "circle_b_center": [c2_x, c2_y],
        },
        "explanation": "Both central orange circles have an identical diameter of 60 pixels. The size contrast of the surrounding inducers causes Circle A to appear smaller than Circle B.",
    }
    return img, metadata


def generate_ponzo() -> tuple[Image.Image, dict]:
    """Ponzo Illusion: converging perspective rails with two identical horizontal yellow bars."""
    width, height = 540, 520
    img = Image.new("RGB", (width, height), (248, 249, 250))
    draw = ImageDraw.Draw(img)

    # Converging rails (linear perspective)
    top_x1, top_x2 = 230, 310
    bot_x1, bot_x2 = 100, 440
    y_top = 50
    y_bot = 470
    rail_color = (71, 85, 105)
    draw.line([(top_x1, y_top), (bot_x1, y_bot)], fill=rail_color, width=4)
    draw.line([(top_x2, y_top), (bot_x2, y_bot)], fill=rail_color, width=4)

    # Cross ties (perspective rungs)
    n_ties = 14
    for i in range(n_ties):
        t = (i + 1) / (n_ties + 1)
        # Perspective quadratic spacing
        yt = y_top + (y_bot - y_top) * (t**1.4)
        xt1 = top_x1 + (bot_x1 - top_x1) * t
        xt2 = top_x2 + (bot_x2 - top_x2) * t
        draw.line([(xt1 - 25, yt), (xt2 + 25, yt)], fill=(148, 163, 184), width=2)

    # Target horizontal bars A (top, near apex) and B (bottom, near base)
    bar_len = 130
    bar_h = 10
    bar_color = (234, 179, 8)  # Amber / Yellow
    outline_color = (161, 98, 7)

    y_bar_a = 150
    y_bar_b = 390
    cx = width // 2
    xa1 = cx - bar_len // 2
    xa2 = cx + bar_len // 2
    xb1 = cx - bar_len // 2
    xb2 = cx + bar_len // 2

    # Draw Bar A
    draw.rectangle([xa1, y_bar_a - bar_h // 2, xa2, y_bar_a + bar_h // 2], fill=bar_color, outline=outline_color, width=1)
    # Draw Bar B
    draw.rectangle([xb1, y_bar_b - bar_h // 2, xb2, y_bar_b + bar_h // 2], fill=bar_color, outline=outline_color, width=1)

    font = ImageFont.load_default()
    draw.text((xa1 - 50, y_bar_a - 6), "Bar A", fill=(30, 41, 59), font=font)
    draw.text((xb1 - 50, y_bar_b - 6), "Bar B", fill=(30, 41, 59), font=font)

    metadata = {
        "illusion_type": "ponzo",
        "name": "Ponzo Illusion",
        "author": "Mario Ponzo (1911)",
        "source": "Atti della Reale Accademia delle Scienze di Torino (1911). Canonical perspective illusion.",
        "license": "Public Domain. Canonical scientific benchmark illusion.",
        "asset_file": "ponzo.png",
        "question": "Are horizontal bars A and B the same length?",
        "answer": "yes",
        "options": ["Yes", "No"],
        "ground_truth_metric": "bar_pixel_length",
        "measured_values": {
            "bar_a_length": float(bar_len),
            "bar_b_length": float(bar_len),
            "bar_a_span": [xa1, y_bar_a, xa2, y_bar_a],
            "bar_b_span": [xb1, y_bar_b, xb2, y_bar_b],
            "difference": 0.0,
        },
        "explanation": "Both yellow horizontal bars are exactly 130 pixels long. The linear perspective created by the converging rails induces an illusion that Bar A is larger.",
    }
    return img, metadata


def generate_simultaneous_contrast() -> tuple[Image.Image, dict]:
    """Simultaneous Contrast Illusion: identical grey squares on dark vs light backgrounds."""
    width, height = 640, 420
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Left field: dark background
    draw.rectangle([0, 0, width // 2, height], fill=(40, 40, 40))
    # Right field: light background
    draw.rectangle([width // 2, 0, width, height], fill=(220, 220, 220))

    # Center target squares: identical grey RGB(130, 130, 130)
    sq_size = 90
    sq_y1 = (height - sq_size) // 2
    sq_y2 = sq_y1 + sq_size

    # Square A on dark
    cx_a = width // 4
    sq_a_box = [cx_a - sq_size // 2, sq_y1, cx_a + sq_size // 2, sq_y2]
    draw.rectangle(sq_a_box, fill=(130, 130, 130))

    # Square B on light
    cx_b = 3 * width // 4
    sq_b_box = [cx_b - sq_size // 2, sq_y1, cx_b + sq_size // 2, sq_y2]
    draw.rectangle(sq_b_box, fill=(130, 130, 130))

    font = ImageFont.load_default()
    draw.text((cx_a - 24, sq_y2 + 25), "Square A", fill=(220, 220, 220), font=font)
    draw.text((cx_b - 24, sq_y2 + 25), "Square B", fill=(40, 40, 40), font=font)

    metadata = {
        "illusion_type": "simultaneous-contrast",
        "name": "Simultaneous Contrast Illusion",
        "author": "Michel Eugène Chevreul (1839)",
        "source": "De la loi du contraste simultané des couleurs (1839). Canonical brightness contrast illusion.",
        "license": "Public Domain. Canonical scientific benchmark illusion.",
        "asset_file": "simultaneous-contrast.png",
        "question": "Are squares A and B the same shade of grey?",
        "answer": "yes",
        "options": ["Yes", "No"],
        "ground_truth_metric": "rgb_luminance",
        "measured_values": {
            "square_a_rgb": [130.0, 130.0, 130.0],
            "square_b_rgb": [130.0, 130.0, 130.0],
            "luminance_difference": 0.0,
            "rgb_difference": 0.0,
            "square_a_box": sq_a_box,
            "square_b_box": sq_b_box,
        },
        "regions": {
            "square_a_interior": [sq_a_box[0] + 5, sq_a_box[1] + 5, sq_a_box[2] - 5, sq_a_box[3] - 5],
            "square_b_interior": [sq_b_box[0] + 5, sq_b_box[1] + 5, sq_b_box[2] - 5, sq_b_box[3] - 5],
        },
        "explanation": "Both Square A and Square B have the exact same RGB color (130, 130, 130). Lateral inhibition causes Square A to appear significantly lighter against its dark surround.",
    }
    return img, metadata


def generate_cafe_wall() -> tuple[Image.Image, dict]:
    """Café Wall Illusion: parallel horizontal mortar lines appearing wedge-shaped and tilted."""
    width, height = 640, 460
    img = Image.new("RGB", (width, height), (136, 136, 136))
    draw = ImageDraw.Draw(img)

    tile_w = 48
    tile_h = 44
    mortar_h = 3
    mortar_color = (136, 136, 136)

    # Row offsets producing the Café Wall illusion
    offsets = [0, 12, 24, 12, 0, 12, 24, 12, 0]
    num_rows = len(offsets)
    total_grid_h = num_rows * tile_h + (num_rows - 1) * mortar_h
    start_y = (height - total_grid_h) // 2

    mortar_y_positions: list[int] = []

    curr_y = start_y
    for r_idx, offset in enumerate(offsets):
        # Draw tiles across row
        x = -tile_w + offset
        color_idx = 0
        while x < width + tile_w:
            color = (25, 25, 25) if color_idx % 2 == 0 else (240, 240, 240)
            draw.rectangle([x, curr_y, x + tile_w, curr_y + tile_h], fill=color)
            x += tile_w
            color_idx += 1

        curr_y += tile_h
        if r_idx < num_rows - 1:
            draw.rectangle([0, curr_y, width, curr_y + mortar_h], fill=mortar_color)
            mortar_y_positions.append(curr_y)
            curr_y += mortar_h

    metadata = {
        "illusion_type": "cafe-wall",
        "name": "Café Wall Illusion",
        "author": "Richard Gregory and Priscilla Heard (1979)",
        "source": "Border locking and the Café Wall illusion, Perception 8(4), 1979.",
        "license": "Public Domain. Canonical geometric optical illusion.",
        "asset_file": "cafe-wall.png",
        "question": "Are the horizontal mortar lines dividing the rows parallel?",
        "answer": "yes",
        "options": ["Yes", "No"],
        "ground_truth_metric": "line_parallelism",
        "measured_values": {
            "mortar_y_positions": mortar_y_positions,
            "slope": 0.0,
            "slope_difference": 0.0,
            "is_strictly_parallel": True,
        },
        "explanation": "Every horizontal grey mortar line is perfectly horizontal and parallel (slope = 0.0). The staggered black and white tiles create luminance border-locking signals that mislead human edge detectors.",
    }
    return img, metadata


def build_library() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    generators = [
        ("muller-lyer", generate_muller_lyer),
        ("ebbinghaus", generate_ebbinghaus),
        ("ponzo", generate_ponzo),
        ("simultaneous-contrast", generate_simultaneous_contrast),
        ("cafe-wall", generate_cafe_wall),
    ]

    all_metadata: dict[str, dict] = {}

    # Load existing checker shadow metadata
    existing_meta_path = ASSETS_DIR / "metadata.json"
    if existing_meta_path.exists():
        existing_cs = json.loads(existing_meta_path.read_text(encoding="utf-8"))
        existing_cs["illusion_type"] = "checker-shadow"
        all_metadata["checker-shadow"] = existing_cs

    for name, gen_fn in generators:
        img, meta = gen_fn()
        img_path = ASSETS_DIR / meta["asset_file"]
        img.save(img_path, format="PNG", optimize=True)
        all_metadata[name] = meta
        print(f"Generated {name} -> {img_path} ({img.size})")

    # Write combined catalog metadata
    index_path = ASSETS_DIR / "illusions_catalog.json"
    index_path.write_text(json.dumps(all_metadata, indent=2), encoding="utf-8")
    print(f"Saved illusions catalog to {index_path} ({len(all_metadata)} illusions)")


if __name__ == "__main__":
    build_library()
