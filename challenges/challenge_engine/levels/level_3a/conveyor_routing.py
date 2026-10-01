"""Conveyor Routing puzzle generator (Level 3A subtype).

A package travels along an automated logistics conveyor network with mechanical diverter
switches. Each switch has a visibly set diverter arm and directional indicator showing
which route is active. The user must visually follow the active track to find the destination bin.
"""

from __future__ import annotations

import math
from typing import Any
from PIL import Image, ImageDraw

from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.random import DeterministicRNG
from challenge_engine.core.schemas import ROUTING_DIFFICULTY_PRESETS, Level3AConfig
from challenge_engine.levels.level_3a.base import (
    COLOR_ACCENT_AMBER,
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_CYAN,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_PURPLE,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_CARD_BG,
    COLOR_HEADER_BG,
    COLOR_TEXT_DIM,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    RoutingPuzzleSubtypeGenerator,
    draw_header_banner,
    get_font,
)

BIN_COLORS = [
    COLOR_ACCENT_CYAN,
    COLOR_ACCENT_AMBER,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_PURPLE,
    (236, 72, 153),  # Pink-500
]


class ConveyorRoutingGenerator(RoutingPuzzleSubtypeGenerator):
    """Procedural generator for Conveyor Routing challenges."""

    subtype = "conveyor-routing"

    def _resolve_params(self, rng: DeterministicRNG) -> dict[str, int]:
        cfg_sub = self.config.conveyorRouting
        diff = self.config.difficulty
        presets = ROUTING_DIFFICULTY_PRESETS["conveyor-routing"].get(
            diff, ROUTING_DIFFICULTY_PRESETS["conveyor-routing"]["medium"]
        )
        return {
            "switches": cfg_sub.switchCount or presets["switches"],
            "bins": cfg_sub.binCount or presets["bins"],
            "decoys": cfg_sub.decoyBranches or presets["decoys"],
        }

    def generate_one(self, seed: int) -> ChallengeBundle:
        rng = DeterministicRNG(seed, f"{self.level_key}:{self.subtype}")
        params = self._resolve_params(rng.fork("params"))
        n_bins = min(max(3, params["bins"]), 5)

        width = self.config.canvasWidth
        height = self.config.canvasHeight

        # Build a multi-tier directed network of switches
        num_tiers = 3 if n_bins <= 4 else 4

        y_start = 120.0
        y_end = height - 90.0
        y_step = (y_end - y_start) / (num_tiers + 1)

        tier_nodes: list[list[dict[str, Any]]] = []

        # Tier 0: Single entry switch
        entry_x = width / 2.0
        entry_y = y_start + y_step
        tier_nodes.append([{"x": entry_x, "y": entry_y, "tier": 0, "idx": 0}])

        # Intermediate switch tiers
        for t in range(1, num_tiers):
            tier_y = y_start + (t + 1) * y_step
            count = min(t + 1, n_bins)
            span = width * 0.72
            xs = [width / 2.0 - span / 2.0 + (span / (count - 1)) * i for i in range(count)]
            nodes_in_tier = []
            for i, nx in enumerate(xs):
                nodes_in_tier.append({"x": nx, "y": tier_y, "tier": t, "idx": i})
            tier_nodes.append(nodes_in_tier)

        # Destination bins at the bottom
        bin_y = y_end
        span_bins = width * 0.76
        bin_xs = [
            width / 2.0 - span_bins / 2.0 + (span_bins / (n_bins - 1)) * i
            for i in range(n_bins)
        ]
        bin_nodes = [
            {"x": bx, "y": bin_y, "label": f"Bin {chr(65 + i)}", "idx": i}
            for i, bx in enumerate(bin_xs)
        ]

        # Connect switches to children and assign switch states
        switch_states: dict[tuple[int, int], str] = {}
        for t, nodes in enumerate(tier_nodes):
            for i, node in enumerate(nodes):
                state = rng.fork(f"switch_{t}_{i}").choice(["left", "right"])
                switch_states[(t, i)] = state
                node["state"] = state

                if t < num_tiers - 1:
                    next_nodes = tier_nodes[t + 1]
                    node["left_child"] = next_nodes[min(i, len(next_nodes) - 1)]
                    node["right_child"] = next_nodes[min(i + 1, len(next_nodes) - 1)]
                else:
                    node["left_child"] = bin_nodes[min(i, len(bin_nodes) - 1)]
                    node["right_child"] = bin_nodes[min(i + 1, len(bin_nodes) - 1)]

        # Trace package path from entry node
        curr = tier_nodes[0][0]
        route_nodes = [curr]
        while "label" not in curr:
            active_child = (
                curr["left_child"] if curr["state"] == "left" else curr["right_child"]
            )
            route_nodes.append(active_child)
            curr = active_child

        target_bin = curr["label"]
        options = [b["label"] for b in bin_nodes]

        # Render visual scene
        img = self._render_conveyor_scene(
            width=width,
            height=height,
            tier_nodes=tier_nodes,
            bin_nodes=bin_nodes,
            entry_pos=(entry_x, y_start),
            route_nodes=route_nodes,
        )

        instruction = "Which bin will receive the package?"
        private_meta = {
            "subtype": self.subtype,
            "difficulty": self.config.difficulty,
            "switchCount": sum(len(tn) for tn in tier_nodes),
            "targetBin": target_bin,
            "routeLength": len(route_nodes),
            "options": options,
        }

        return self.build_bundle(
            seed=seed,
            instruction=instruction,
            options=options,
            correct_answer=target_bin,
            image=img,
            private_routing_metadata=private_meta,
        )

    def _render_conveyor_scene(
        self,
        width: int,
        height: int,
        tier_nodes: list[list[dict[str, Any]]],
        bin_nodes: list[dict[str, Any]],
        entry_pos: tuple[float, float],
        route_nodes: list[dict[str, Any]],
    ) -> Image.Image:
        """Render high-clarity industrial conveyor routing scene."""
        img = Image.new("RGB", (width, height), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Header banner
        draw_header_banner(
            draw=draw,
            width=width,
            height=height,
            badge_text="LEVEL 3A — CONVEYOR ROUTING",
            instruction_text="Trace the package path through the active switches to find its destination bin.",
            accent_color=COLOR_ACCENT_AMBER,
        )

        font_label = get_font(14, bold=True)
        track_color = (71, 85, 105)         # Slate-600
        track_fill = (30, 41, 59)           # Slate-800
        active_arrow_color = (74, 222, 128) # Green-400

        # 1. Draw Entry conveyor track from top
        e_x, e_y = entry_pos
        top_node = tier_nodes[0][0]
        draw.line([(e_x, e_y), (top_node["x"], top_node["y"])], fill=track_color, width=16)
        draw.line([(e_x, e_y), (top_node["x"], top_node["y"])], fill=track_fill, width=10)

        # 2. Draw all conveyor branch tracks
        for tier in tier_nodes:
            for node in tier:
                nx, ny = node["x"], node["y"]
                lc = node["left_child"]
                rc = node["right_child"]

                draw.line([(nx, ny), (lc["x"], lc["y"])], fill=track_color, width=16)
                draw.line([(nx, ny), (lc["x"], lc["y"])], fill=track_fill, width=10)

                draw.line([(nx, ny), (rc["x"], rc["y"])], fill=track_color, width=16)
                draw.line([(nx, ny), (rc["x"], rc["y"])], fill=track_fill, width=10)

        # 3. Draw switches (junction hubs) with mechanical diverter blade
        for tier in tier_nodes:
            for node in tier:
                nx, ny = node["x"], node["y"]
                state = node["state"]
                target_child = node["left_child"] if state == "left" else node["right_child"]

                # Switch circular base housing
                draw.ellipse([nx - 24, ny - 24, nx + 24, ny + 24], fill=(15, 23, 42), outline=COLOR_BORDER_LIGHT, width=2)
                draw.ellipse([nx - 18, ny - 18, nx + 18, ny + 18], fill=(30, 41, 59))

                dx = target_child["x"] - nx
                dy = target_child["y"] - ny
                mag = math.hypot(dx, dy)
                if mag > 0:
                    ux = dx / mag
                    uy = dy / mag
                else:
                    ux, uy = (0.0, 1.0)

                # Active mechanical diverter arm
                arm_tip_x = nx + ux * 20.0
                arm_tip_y = ny + uy * 20.0
                draw.line([(nx, ny), (arm_tip_x, arm_tip_y)], fill=COLOR_ACCENT_AMBER, width=6)
                # Diverter pivot bolt
                draw.ellipse([nx - 5, ny - 5, nx + 5, ny + 5], fill=(248, 250, 252))

                # Bright green directional arrow on active branch
                arr_x = nx + ux * 36.0
                arr_y = ny + uy * 36.0
                draw.ellipse([arr_x - 8, arr_y - 8, arr_x + 8, arr_y + 8], fill=active_arrow_color)

        # 4. Draw Entry Package
        pkg_w, pkg_h = 76, 44
        pkg_x = int(e_x - pkg_w / 2)
        pkg_y = int(e_y - 10)
        draw.rounded_rectangle(
            [pkg_x, pkg_y, pkg_x + pkg_w, pkg_y + pkg_h],
            radius=6,
            fill=(180, 83, 9),  # Cardboard Amber-700
            outline=(251, 191, 36),  # Amber-400
            width=2,
        )
        draw.line(
            [(e_x, pkg_y), (e_x, pkg_y + pkg_h)],
            fill=(253, 230, 138),
            width=4,
        )
        draw.text((pkg_x + 10, pkg_y + 14), "PACKAGE", fill=(255, 255, 255), font=get_font(12, bold=True))

        # 5. Draw Destination Bins at the bottom
        for i, b in enumerate(bin_nodes):
            bx = b["x"]
            by = b["y"]
            b_color = BIN_COLORS[i % len(BIN_COLORS)]
            bw, bh = 110, 52
            x1 = bx - bw / 2
            y1 = by - bh / 2
            x2 = bx + bw / 2
            y2 = by + bh / 2

            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=8,
                fill=(15, 23, 42),
                outline=b_color,
                width=3,
            )
            draw.line([(x1 + 10, y1 + 8), (x2 - 10, y1 + 8)], fill=b_color, width=2)
            draw.text((x1 + 24, y1 + 18), b["label"], fill=COLOR_TEXT_PRIMARY, font=font_label)

        return img
