"""Device Cables routing puzzle generator (Level 3A human-friendly cable tracing).

Clean redesign of cable tracing with familiar devices (Laptop, Smartphone, Camera, etc.)
and wall outlets (Outlet A, Outlet B, etc.). Uses 6px stroke lines, high-contrast distinct
colors, and wide background-halo crossover bridges to ensure zero ambiguity at crossings.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from PIL import Image, ImageDraw

from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.random import DeterministicRNG
from challenge_engine.core.schemas import ROUTING_DIFFICULTY_PRESETS
from challenge_engine.levels.level_3a.base import (
    COLOR_ACCENT_GREEN,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_HEADER_BG,
    COLOR_TEXT_PRIMARY,
    RoutingPuzzleSubtypeGenerator,
    draw_header_banner,
    get_font,
)

DEVICE_POOL = [
    "Smartphone",
    "Laptop",
    "Headphones",
    "Camera",
    "Tablet",
    "Monitor",
    "Speaker",
    "Game Console",
    "Smartwatch",
    "Microphone",
    "Keyboard",
    "Drone",
]

CABLE_PALETTE = [
    (239, 68, 68),   # Red-500
    (59, 130, 246),  # Blue-500
    (34, 197, 94),   # Green-500
    (245, 158, 11),  # Amber-500
    (168, 85, 247),  # Purple-500
    (6, 182, 212),   # Cyan-500
    (236, 72, 153),  # Pink-500
    (249, 115, 22),  # Orange-500
    (14, 165, 233),  # Sky-500
    (132, 204, 22),  # Lime-500
    (168, 162, 158), # Stone-400
    (244, 63, 94),   # Rose-500
]


def _cubic_bezier_segment(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 16,
) -> list[tuple[float, float]]:
    """Sample a cubic Bezier curve from p0 to p3."""
    pts: list[tuple[float, float]] = []
    for i in range(1, steps + 1):
        t = i / float(steps)
        mt = 1.0 - t
        x = (
            (mt**3) * p0[0]
            + 3 * (mt**2) * t * p1[0]
            + 3 * mt * (t**2) * p2[0]
            + (t**3) * p3[0]
        )
        y = (
            (mt**3) * p0[1]
            + 3 * (mt**2) * t * p1[1]
            + 3 * mt * (t**2) * p2[1]
            + (t**3) * p3[1]
        )
        pts.append((float(x), float(y)))
    return pts


def _build_smooth_path(
    waypoints: list[tuple[float, float]],
    subdivisions: int = 16,
) -> list[tuple[float, float]]:
    """Generate smooth polyline through waypoints."""
    if len(waypoints) < 2:
        return list(waypoints)
    polyline: list[tuple[float, float]] = [waypoints[0]]
    for i in range(len(waypoints) - 1):
        p0 = waypoints[i]
        p3 = waypoints[i + 1]
        dx = (p3[0] - p0[0]) * 0.42
        p1 = (p0[0] + dx, p0[1])
        p2 = (p3[0] - dx, p3[1])
        polyline.extend(_cubic_bezier_segment(p0, p1, p2, p3, steps=subdivisions))
    return polyline


class DeviceCablesGenerator(RoutingPuzzleSubtypeGenerator):
    """Procedural generator for Device Cables routing challenges."""

    subtype = "device-cables"

    def _resolve_params(self, rng: DeterministicRNG) -> dict[str, Any]:
        cfg_sub = self.config.deviceCables
        diff = self.config.difficulty
        presets = ROUTING_DIFFICULTY_PRESETS["device-cables"].get(
            diff, ROUTING_DIFFICULTY_PRESETS["device-cables"]["medium"]
        )

        cable_range = cfg_sub.cableCountRange or presets["cableCountRange"]
        n_cables = rng.randint(cable_range[0], cable_range[1])
        n_cables = min(n_cables, len(DEVICE_POOL))

        wp_range = cfg_sub.waypointRange or presets["waypointRange"]
        line_w = cfg_sub.lineWidth or presets["lineWidth"]

        opt_range = cfg_sub.answerOptionCountRange or presets["answerOptionCountRange"]
        return {
            "answerOptionCount": rng.randint(*opt_range),
            "cableCount": n_cables,
            "waypointRange": wp_range,
            "lineWidth": line_w,
        }

    def generate_one(self, seed: int) -> ChallengeBundle:
        rng = DeterministicRNG(seed, f"{self.level_key}:{self.subtype}")
        params = self._resolve_params(rng.fork("params"))
        n_cables = params["cableCount"]
        line_w = params["lineWidth"]
        w_min, w_max = params["waypointRange"]

        width = self.config.canvasWidth
        height = self.config.canvasHeight

        # Select devices and outlets
        devices = DEVICE_POOL[:n_cables]
        outlets = [f"Outlet {chr(65 + i)}" for i in range(n_cables)]

        # Determine query type: find connected device or find connected outlet
        query_type = rng.fork("query_type").choice(["find_device", "find_outlet"])

        # Spatial layout
        top_m = 90.0
        bottom_m = 50.0
        usable_h = height - top_m - bottom_m
        step_y = usable_h / float(max(1, n_cables - 1))

        left_pin_x = 220.0
        right_pin_x = float(width - 220)

        device_positions: dict[str, tuple[float, float]] = {}
        outlet_positions: dict[str, tuple[float, float]] = {}

        for i, dev in enumerate(devices):
            device_positions[dev] = (left_pin_x, top_m + i * step_y)
        for i, out in enumerate(outlets):
            outlet_positions[out] = (right_pin_x, top_m + i * step_y)

        # One-to-one permutation
        shuffled_outlets = rng.fork("mapping").shuffle(outlets)
        connections: dict[str, str] = {
            dev: out for dev, out in zip(devices, shuffled_outlets)
        }

        # Generate smooth cable paths with intermediate columns
        num_cols = rng.fork("cols").randint(w_min, w_max)
        route_left = left_pin_x + 50.0
        route_right = right_pin_x - 50.0
        col_xs = np.linspace(route_left, route_right, num_cols)

        slot_ys = np.linspace(top_m + 8.0, height - bottom_m - 8.0, n_cables)
        col_assignments: list[list[float]] = []

        for col_idx in range(num_cols):
            col_rng = rng.fork(f"col_{col_idx}")
            perm = col_rng.shuffle(list(range(n_cables)))
            col_y_cable: list[float] = [0.0] * n_cables
            jitter_max = min(12.0, step_y * 0.3)
            for cable_idx, slot_idx in enumerate(perm):
                jitter = col_rng.uniform(-jitter_max, jitter_max)
                y_val = float(np.clip(slot_ys[slot_idx] + jitter, top_m + 4.0, height - bottom_m - 4.0))
                col_y_cable[cable_idx] = round(y_val, 2)
            col_assignments.append(col_y_cable)

        polylines: dict[str, list[tuple[float, float]]] = {}
        for c_idx, dev in enumerate(devices):
            out = connections[dev]
            start_p = device_positions[dev]
            end_p = outlet_positions[out]
            waypoints = [start_p]
            for col_idx in range(num_cols):
                waypoints.append((float(col_xs[col_idx]), col_assignments[col_idx][c_idx]))
            waypoints.append(end_p)
            polylines[dev] = _build_smooth_path(waypoints, subdivisions=16)

        # Layer order for halo crossover rendering
        layer_order = rng.fork("layers").shuffle(list(devices))

        # Build query and options
        if query_type == "find_device":
            target_outlet = rng.fork("target").choice(outlets)
            inv_map = {out: dev for dev, out in connections.items()}
            correct_device = inv_map[target_outlet]
            instruction = f"Which device is connected to {target_outlet}?"
            correct_answer = correct_device
            other_devs = [d for d in devices if d != correct_device]
            decoy_devs = rng.fork("decoys").sample(other_devs, min(params["answerOptionCount"] - 1, len(other_devs)))
            options = rng.fork("opt_shuf").shuffle([correct_device] + decoy_devs)
            highlight_target = ("outlet", target_outlet)
        else:
            target_device = rng.fork("target").choice(devices)
            correct_outlet = connections[target_device]
            instruction = f"Which outlet is the {target_device} connected to?"
            correct_answer = correct_outlet
            other_outs = [o for o in outlets if o != correct_outlet]
            decoy_outs = rng.fork("decoys").sample(other_outs, min(params["answerOptionCount"] - 1, len(other_outs)))
            options = rng.fork("opt_shuf").shuffle([correct_outlet] + decoy_outs)
            highlight_target = ("device", target_device)

        # Render visual scene
        img = self._render_cables_scene(
            width=width,
            height=height,
            devices=devices,
            outlets=outlets,
            device_positions=device_positions,
            outlet_positions=outlet_positions,
            polylines=polylines,
            layer_order=layer_order,
            highlight_target=highlight_target,
            line_w=line_w,
        )

        private_meta = {
            "subtype": self.subtype,
            "difficulty": self.config.difficulty,
            "cableCount": n_cables,
            "waypointColumnCount": num_cols,
            "answerOptionCount": len(options),
            "connections": connections,
            "queryType": query_type,
            "highlighted": highlight_target,
            "options": options,
        }

        return self.build_bundle(
            seed=seed,
            instruction=instruction,
            options=options,
            correct_answer=correct_answer,
            image=img,
            private_routing_metadata=private_meta,
        )

    def _render_cables_scene(
        self,
        width: int,
        height: int,
        devices: list[str],
        outlets: list[str],
        device_positions: dict[str, tuple[float, float]],
        outlet_positions: dict[str, tuple[float, float]],
        polylines: dict[str, list[tuple[float, float]]],
        layer_order: list[str],
        highlight_target: tuple[str, str],
        line_w: int,
    ) -> Image.Image:
        """Render high-clarity cable scene with wide background halos at crossings."""
        img = Image.new("RGB", (width, height), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Header banner
        draw_header_banner(
            draw=draw,
            width=width,
            height=height,
            badge_text="LEVEL 3A — DEVICE CABLES",
            instruction_text="Trace the cable from the highlighted item to find where it connects.",
            accent_color=COLOR_ACCENT_GREEN,
        )

        font_item = get_font(13, bold=True)
        font_badge = get_font(11, bold=True)

        halo_w = line_w + 10  # 16px wide background halo for 6px stroke
        casing_w = line_w + 4  # 10px dark casing border

        # 1. Draw cables according to layer order with background halo
        for dev in layer_order:
            dev_idx = devices.index(dev)
            base_col = CABLE_PALETTE[dev_idx % len(CABLE_PALETTE)]
            highlight_col = (
                min(255, base_col[0] + 60),
                min(255, base_col[1] + 60),
                min(255, base_col[2] + 60),
            )
            pts = polylines[dev]

            # Halo bridge (erases line underneath at crossings)
            draw.line(pts, fill=COLOR_BG, width=halo_w, joint="curve")
            # Casing
            draw.line(pts, fill=(15, 23, 42), width=casing_w, joint="curve")
            # Vibrant core cable
            draw.line(pts, fill=base_col, width=line_w, joint="curve")
            # Center reflection highlight
            draw.line(pts, fill=highlight_col, width=1, joint="curve")

        # 2. Draw Device Cards on left
        h_kind, h_name = highlight_target
        for dev in devices:
            px, py = device_positions[dev]
            is_hl = (h_kind == "device" and dev == h_name)

            card_w, card_h = 190, 36
            x1 = px - card_w
            y1 = py - card_h / 2
            x2 = px
            y2 = py + card_h / 2

            fill_c = (55, 48, 163) if is_hl else COLOR_HEADER_BG
            outline_c = (129, 140, 248) if is_hl else COLOR_BORDER
            outline_w = 3 if is_hl else 1

            draw.rounded_rectangle([x1, y1, x2, y2], radius=6, fill=fill_c, outline=outline_c, width=outline_w)
            draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=outline_c)
            draw.text((x1 + 14, y1 + 9), dev, fill=COLOR_TEXT_PRIMARY, font=font_item)
            if is_hl:
                draw.text((x2 - 68, y1 + 10), "[TARGET]", fill=(253, 224, 71), font=font_badge)

        # 3. Draw Outlet Cards on right
        for out in outlets:
            px, py = outlet_positions[out]
            is_hl = (h_kind == "outlet" and out == h_name)

            card_w, card_h = 180, 36
            x1 = px
            y1 = py - card_h / 2
            x2 = px + card_w
            y2 = py + card_h / 2

            fill_c = (55, 48, 163) if is_hl else COLOR_HEADER_BG
            outline_c = (129, 140, 248) if is_hl else COLOR_BORDER
            outline_w = 3 if is_hl else 1

            draw.rounded_rectangle([x1, y1, x2, y2], radius=6, fill=fill_c, outline=outline_c, width=outline_w)
            draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=outline_c)
            draw.text((x1 + 18, y1 + 9), out, fill=COLOR_TEXT_PRIMARY, font=font_item)
            if is_hl:
                draw.text((x2 - 68, y1 + 10), "[TARGET]", fill=(253, 224, 71), font=font_badge)

        return img
