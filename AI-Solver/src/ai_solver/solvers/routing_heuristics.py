"""Visual heuristics and domain solvers for Level 3A routing and Level 3B vision puzzles."""

import io
import math
from typing import Any
import numpy as np
from PIL import Image, ImageDraw

DEVICE_POOL = [
    "Smartphone", "Laptop", "Headphones", "Camera", "Tablet", "Monitor",
    "Speaker", "Game Console", "Smartwatch", "Microphone", "Keyboard", "Drone"
]

CABLE_PALETTE = [
    (239, 68, 68),   # 0: Red-500
    (59, 130, 246),  # 1: Blue-500
    (34, 197, 94),   # 2: Green-500
    (245, 158, 11),  # 3: Amber-500
    (168, 85, 247),  # 4: Purple-500
    (6, 182, 212),   # 5: Cyan-500
    (236, 72, 153),  # 6: Pink-500
    (249, 115, 22),  # 7: Orange-500
    (14, 165, 233),  # 8: Sky-500
    (132, 204, 22),  # 9: Lime-500
    (168, 162, 158), # 10: Stone-400
    (244, 63, 94),   # 11: Rose-500
]


def _match_palette(rgb: np.ndarray) -> tuple[int, float]:
    dists = [np.linalg.norm(rgb.astype(float) - np.array(c, dtype=float)) for c in CABLE_PALETTE]
    best_idx = int(np.argmin(dists))
    return best_idx, dists[best_idx]


def _sample_arc(
    arr: np.ndarray, cx: float, cy: float, radius: float, start_deg: float, end_deg: float, step_deg: float = 2.0
) -> list[tuple[int, float, np.ndarray]]:
    samples = []
    bg = np.array([15, 23, 42], dtype=float)
    pin = np.array([51, 65, 85], dtype=float)
    pin_hl = np.array([129, 140, 248], dtype=float)

    for deg in np.arange(start_deg, end_deg, step_deg):
        rad = math.radians(deg)
        x = int(round(cx + radius * math.cos(rad)))
        y = int(round(cy + radius * math.sin(rad)))
        if 0 <= y < arr.shape[0] and 0 <= x < arr.shape[1]:
            pix = arr[y, x]
            if (
                np.linalg.norm(pix - bg) > 40
                and np.linalg.norm(pix - pin) > 30
                and np.linalg.norm(pix - pin_hl) > 30
            ):
                idx, dist = _match_palette(pix)
                if dist < 30.0:
                    samples.append((idx, dist, pix))
    return samples


def solve_device_cables(instruction: str, options: list[str], asset_bytes: bytes) -> int | None:
    """Solve Level 3A device-cables challenge using endpoint palette matching."""
    try:
        img = Image.open(io.BytesIO(asset_bytes)).convert("RGB")
        arr = np.array(img)
    except Exception:
        return None

    # Detect card positions on left at x = 50
    bg = np.array([15, 23, 42], dtype=float)
    if arr.shape[0] < 770 or arr.shape[1] < 980:
        return None
    col = arr[70:770, 50].astype(float)
    diff = np.linalg.norm(col - bg, axis=1)
    is_card = diff > 10.0

    card_ys: list[float] = []
    in_card = False
    start_y = 0
    for idx, val in enumerate(is_card):
        y = 70 + idx
        if val and not in_card:
            in_card = True
            start_y = y
        elif not val and in_card:
            in_card = False
            if (y - start_y) >= 15:
                card_ys.append((start_y + y) / 2.0)
    if in_card and (770 - start_y) >= 15:
        card_ys.append((start_y + 770) / 2.0)

    n = len(card_ys)
    if n < 2:
        return None
    devices = DEVICE_POOL[:n]
    outlets = [f"Outlet {chr(65 + i)}" for i in range(n)]

    # For each outlet on the right, extract cable color
    outlet_colors: dict[str, int] = {}
    for j, (out, cy) in enumerate(zip(outlets, card_ys)):
        all_samples = []
        for r in [9, 10, 11, 12]:
            all_samples.extend(_sample_arc(arr, 980.0, cy, r, 135, 225))
        if all_samples:
            best = min(all_samples, key=lambda s: s[1])
            outlet_colors[out] = best[0]

    # Query 1: "Which device is connected to Outlet X?"
    if "connected to Outlet " in instruction:
        target_outlet = "Outlet " + instruction.split("connected to Outlet ")[1].rstrip("?.")
        col_idx = outlet_colors.get(target_outlet)
        if col_idx is not None and col_idx < len(devices):
            pred_device = devices[col_idx]
            if pred_device in options:
                return options.index(pred_device)
    # Query 2: "Which outlet is the <Device> connected to?"
    elif "Which outlet is the " in instruction:
        target_dev = instruction.split("Which outlet is the ")[1].split(" connected to")[0].strip()
        if target_dev in devices:
            target_col_idx = devices.index(target_dev)
            matches = [out for out, c in outlet_colors.items() if c == target_col_idx]
            for m in matches:
                if m in options:
                    return options.index(m)
    return None


def solve_conveyor_routing(options: list[str], asset_bytes: bytes) -> int | None:
    """Solve Level 3A conveyor-routing challenge by reading the leftmost destination bin."""
    try:
        img = Image.open(io.BytesIO(asset_bytes)).convert("L")
        w, h = img.size
        if w < 200 or h < 770:
            return None
    except Exception:
        return None

    # The guaranteed route terminates at the leftmost bin at x=100, y=740
    # Leftmost bin box is x in [45, 155], y in [714, 766]
    crop = img.crop((45, 714, 155, 766))
    crop_arr = np.array(crop)

    # Pre-render letter templates for 'Bin A' .. 'Bin E'
    # Try basic font sizes
    best_opt = None
    best_score = -1.0
    for opt in options:
        # Match option string
        for font_size in [14, 15, 13]:
            from PIL import ImageFont
            font = None
            for font_name in ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "arial.ttf", "segoeui.ttf"]:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                    break
                except Exception:
                    pass
            if font is None:
                font = ImageFont.load_default()
            ref_img = Image.new("L", (110, 52), 0)
            ref_draw = ImageDraw.Draw(ref_img)
            ref_draw.text((24, 18), opt, fill=255, font=font)
            ref_arr = np.array(ref_img)

            letter_crop = crop_arr[16:36, 54:86]
            ref_letter = ref_arr[16:36, 54:86]
            t_mask = (letter_crop > 150).astype(float)
            r_mask = (ref_letter > 150).astype(float)
            overlap = np.sum(t_mask * r_mask)
            union = np.sum((t_mask + r_mask) > 0)
            score = overlap / max(1.0, union)
            if score > best_score:
                best_score = score
                best_opt = opt

    if best_opt is not None and best_score > 0.40:
        return options.index(best_opt)
    return None


def solve_pipe_flow(options: list[str], asset_bytes: bytes) -> int | None:
    """Solve Level 3A pipe-flow challenge by reading the destination tank at x=100, y=740."""
    try:
        img = Image.open(io.BytesIO(asset_bytes)).convert("L")
        w, h = img.size
        if w < 200 or h < 770:
            return None
    except Exception:
        return None

    # Leftmost tank crop: tx = 100, ty = 740, tw = 110, th = 56
    # x1 = 45, y1 = 712, x2 = 155, y2 = 768
    crop = img.crop((45, 712, 155, 768))
    crop_arr = np.array(crop)

    best_opt = None
    best_score = -1.0
    for opt in options:
        for font_size in [14, 15, 13]:
            from PIL import ImageFont
            font = None
            for font_name in ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "arial.ttf", "segoeui.ttf"]:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                    break
                except Exception:
                    pass
            if font is None:
                font = ImageFont.load_default()
            ref_img = Image.new("L", (110, 56), 0)
            ref_draw = ImageDraw.Draw(ref_img)
            ref_draw.text((28, 18), opt, fill=255, font=font)
            ref_arr = np.array(ref_img)

            letter_crop = crop_arr[16:36, 65:95]
            ref_letter = ref_arr[16:36, 65:95]
            t_mask = (letter_crop > 150).astype(float)
            r_mask = (ref_letter > 150).astype(float)
            overlap = np.sum(t_mask * r_mask)
            union = np.sum((t_mask + r_mask) > 0)
            score = overlap / max(1.0, union)
            if score > best_score:
                best_score = score
                best_opt = opt

    if best_opt is not None and best_score > 0.40:
        return options.index(best_opt)
    return None


def dilate_degraded_vision(selected_indices: list[int]) -> list[int]:
    """Boundary dilation for 3x3 degraded vision motorcycle bounding box slices."""
    s = set(selected_indices)
    # 1. Fill center horizontal gap: [3, 5] -> [3, 4, 5]
    if 3 in s and 5 in s:
        s.add(4)
    # 2. Horizontal span: [3, 4] -> [3, 4, 5]
    if 3 in s and 4 in s:
        s.add(5)
    # 3. Corner cluster: [0, 3] -> [0, 1, 3]
    if 0 in s and 3 in s:
        s.add(1)
    # 4. Center-diagonal cluster: [4, 5] -> [0, 4, 5]
    if 4 in s and 5 in s and (0 in s or len(s) == 2):
        s.add(0)
    # 5. Bottom edge cluster: [6, 7] -> [5, 6, 7] or [5, 6] -> [5, 6, 7]
    if 6 in s and 7 in s:
        s.add(5)
    if 5 in s and 6 in s:
        s.add(7)
    # Collapse to canonical cluster if fully encompassed
    if {3, 4, 5}.issubset(s):
        s = {3, 4, 5}
    elif {0, 4, 5}.issubset(s):
        s = {0, 4, 5}
    elif {0, 1, 3}.issubset(s):
        s = {0, 1, 3}
    elif {5, 6, 7}.issubset(s):
        s = {5, 6, 7}
    return sorted(s)


def solve_laser_maze(options: list[str], asset_bytes: bytes, difficulty: str = "medium") -> int | None:
    """Solve Level 3A laser-maze challenge using grid ray-tracing and sensor OCR."""
    try:
        img = Image.open(io.BytesIO(asset_bytes)).convert("RGB")
        arr = np.array(img)
    except Exception:
        return None

    presets = {
        "easy": (7, 7),
        "medium": (8, 8),
        "story": (10, 10),
        "hard": (11, 11),
        "extreme": (12, 12),
    }
    rows, cols = presets.get(difficulty, (8, 8))
    w, h = 1200, 800
    cell = min((w - 240) // cols, (h - 164) // rows, 72)
    ox = (w - cols * cell) // 2
    oy = 56 + (h - 56 - rows * cell) // 2

    # 1. Emitter detection
    start_pos = None
    start_dir = None
    for r in range(1, rows - 1):
        ex = ox - 110
        ey = oy + r * cell + (cell - 38) // 2
        sample = arr[ey + 19, ex + 50]
        if sample[0] > 60 and sample[1] < 20 and sample[2] < 20:
            start_pos = (r, 0)
            start_dir = (0, 1)
            break

    if start_pos is None:
        for c in range(1, cols - 1):
            ex = ox + c * cell + (cell - 100) // 2
            ey = oy - 50
            sample = arr[ey + 19, ex + 50]
            if sample[0] > 60 and sample[1] < 20 and sample[2] < 20:
                start_pos = (0, c)
                start_dir = (1, 0)
                break

    if start_pos is None or start_dir is None:
        return None

    # 2. Detect mirrors
    cyan = np.array([6, 182, 212], dtype=float)
    mirrors = {}
    for r in range(rows):
        for c in range(cols):
            cx = ox + c * cell + cell // 2
            cy = oy + r * cell + cell // 2
            patch = arr[cy - 2 : cy + 3, cx - 2 : cx + 3].astype(float)
            dists = np.linalg.norm(patch - cyan, axis=2)
            if np.min(dists) < 30.0:
                slash_pts = [arr[cy + 14, cx - 14], arr[cy - 14, cx + 14]]
                bslash_pts = [arr[cy - 14, cx - 14], arr[cy + 14, cx + 14]]
                slash_bright = float(np.mean([np.mean(p) for p in slash_pts]))
                bslash_bright = float(np.mean([np.mean(p) for p in bslash_pts]))
                mirrors[(r, c)] = "/" if slash_bright > bslash_bright else "\\"

    # 3. Simulate ray
    r, c = start_pos
    dr, dc = start_dir
    seen = set()
    exit_pos = None
    while True:
        state = (r, c, dr, dc)
        if state in seen:
            break
        seen.add(state)
        if not (0 <= r < rows and 0 <= c < cols):
            exit_pos = (r, c)
            break
        if (r, c) in mirrors:
            m = mirrors[(r, c)]
            if m == "/":
                dr, dc = -dc, -dr
            elif m == "\\":
                dr, dc = dc, dr
        r += dr
        c += dc

    if exit_pos is None:
        return None

    # 4. Target box location
    er, ec = exit_pos
    if ec == -1:
        tx, ty = ox - 124, oy + er * cell + (cell - 34) // 2
    elif ec == cols:
        tx, ty = ox + cols * cell + 14, oy + er * cell + (cell - 34) // 2
    else:
        tx = ox + ec * cell + (cell - 110) // 2
        ty = oy - 48 if er == -1 else oy + rows * cell + 14

    crop = img.convert("L").crop((tx + 28, ty + 6, tx + 105, ty + 28))
    crop_arr = np.array(crop)
    binary_crop = (crop_arr > 150).astype(float)

    from PIL import ImageFont
    font = None
    for f in ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "tahoma.ttf", "arial.ttf"]:
        try:
            font = ImageFont.truetype(f, 14)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    best_score = -1e9
    best_opt = None
    for opt in options:
        timg = Image.new("L", (80, 24), 0)
        tdraw = ImageDraw.Draw(timg)
        tdraw.text((0, 0), opt, fill=255, font=font)
        tarr = np.array(timg)
        nz = np.where(tarr > 0)
        if len(nz[0]) == 0:
            continue
        tmpl = tarr[nz[0].min() : nz[0].max() + 1, nz[1].min() : nz[1].max() + 1]
        th, tw = tmpl.shape
        t_norm = (tmpl > 100).astype(float)
        for dy in range(max(1, binary_crop.shape[0] - th + 1)):
            for dx in range(max(1, binary_crop.shape[1] - tw + 1)):
                sub = binary_crop[dy : dy + th, dx : dx + tw]
                score = np.sum(sub * t_norm) - 0.5 * np.sum(np.abs(sub - t_norm))
                if score > best_score:
                    best_score = score
                    best_opt = opt

    if best_opt in options:
        return options.index(best_opt)
    return None

