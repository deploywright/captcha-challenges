"""Conveyor Routing puzzle generator (Level 3A subtype).

A package travels along an automated logistics conveyor network with mechanical diverter
switches. Each switch has a visibly set diverter arm and directional indicator showing
which route is active. The user must visually follow the active track to find the destination bin.
"""

from __future__ import annotations

import math
from challenge_engine.levels.level_3a.topology import build_route_network
from typing import Any
from PIL import Image, ImageDraw

from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.random import DeterministicRNG
from challenge_engine.core.schemas import ROUTING_DIFFICULTY_PRESETS
from challenge_engine.levels.level_3a.base import (
    COLOR_ACCENT_AMBER,
    COLOR_ACCENT_CYAN,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_PURPLE,
    COLOR_BG,
    COLOR_BORDER_LIGHT,
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
        cfg = self.config.conveyorRouting
        p = ROUTING_DIFFICULTY_PRESETS[self.subtype][self.config.difficulty]
        return {
            "depth": cfg.routeDecisionDepth if cfg.routeDecisionDepth is not None else p["routeDecisionDepth"],
            "total": cfg.totalSwitchCount if cfg.totalSwitchCount is not None else (cfg.switchCount if cfg.switchCount is not None else p["totalSwitchCount"]),
            "bins": cfg.binCount if cfg.binCount is not None else p["bins"],
            "decoys": cfg.decoyBranches if cfg.decoyBranches is not None else p["decoyBranchCount"],
        }

    def generate_one(self, seed: int) -> ChallengeBundle:
        rng = DeterministicRNG(seed, f"{self.level_key}:{self.subtype}")
        p = self._resolve_params(rng.fork("params"))
        main, bins, branches = build_route_network(
            rng, p["depth"], p["total"], p["decoys"], p["bins"],
            self.config.canvasWidth, self.config.canvasHeight, "Bin",
        )
        nodes = main + [node for branch in branches for node in branch]
        for node in nodes:
            state = rng.fork(node["id"]).choice(["left", "right"])
            node["state"] = state
            # All main switches activate the guaranteed route. Decoy switches
            # continue along plausible multi-segment routes to other bins.
            node[f"{state}_child"] = node["next"]
            other = "right" if state == "left" else "left"
            node[f"{other}_child"] = node["wrong"]
        graph = {n["id"]: {"state": n["state"], "left": n["left_child"]["id"],
                            "right": n["right_child"]["id"]} for n in nodes}
        # Trace active edges independently of the construction path.
        route = []
        current = main[0]["id"]
        while current in graph:
            if current in route:
                raise RuntimeError("Conveyor active route contains a cycle")
            route.append(current)
            current = graph[current][graph[current]["state"]]
        target = next(b["label"] for b in bins if b["id"] == current)
        route.append(current)
        img = self._render_conveyor_scene(
            self.config.canvasWidth, self.config.canvasHeight, [nodes], bins,
            (main[0]["x"], 95.0), main,
        )
        metadata = {
            "subtype": self.subtype, "difficulty": self.config.difficulty,
            "routeDecisionDepth": len(route) - 1, "totalSwitchCount": len(graph),
            "decoyBranchCount": len(branches), "binCount": len(bins),
            "switchGraph": graph, "solutionPath": route, "targetBin": target,
            "decoyPaths": [[n["id"] for n in branch] + [branch[-1]["next"]["id"]] for branch in branches],
        }
        return self.build_bundle(seed, "Which bin will receive the package?",
                                 sorted(b["label"] for b in bins), target, img, metadata)

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

                draw.line([(nx, ny), (lc["x"], lc["y"])], fill=COLOR_BG, width=22)
                draw.line([(nx, ny), (lc["x"], lc["y"])], fill=track_color, width=16)
                draw.line([(nx, ny), (lc["x"], lc["y"])], fill=track_fill, width=10)

                draw.line([(nx, ny), (rc["x"], rc["y"])], fill=COLOR_BG, width=22)
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
