"""Pipe Flow routing puzzle generator (Level 3A subtype).

Water enters a plumbing distribution network from a main inlet and flows through
junctions and inline valves towards destination storage tanks.
Valves have clearly distinguishable OPEN (inline green aperture) and CLOSED (perpendicular red barrier)
mechanical states. The user visualizes flow connectivity to determine which tank receives water.
"""

from __future__ import annotations

from challenge_engine.levels.level_3a.topology import build_route_network, private_graph_edges, reachable_tanks
from typing import Any
from PIL import Image, ImageDraw

from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.random import DeterministicRNG
from challenge_engine.core.schemas import ROUTING_DIFFICULTY_PRESETS
from challenge_engine.levels.level_3a.base import (
    COLOR_ACCENT_AMBER,
    COLOR_ACCENT_BLUE,
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

TANK_COLORS = [
    COLOR_ACCENT_CYAN,
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_AMBER,
    COLOR_ACCENT_PURPLE,
    COLOR_ACCENT_GREEN,
]

COLOR_VALVE_OPEN = (34, 197, 94)    # Green-500
COLOR_VALVE_CLOSED = (239, 68, 68)  # Red-500
COLOR_PIPE_OUTER = (51, 65, 85)     # Slate-700
COLOR_PIPE_INNER = (30, 41, 59)     # Slate-800


class PipeFlowGenerator(RoutingPuzzleSubtypeGenerator):
    """Procedural generator for Pipe Flow routing challenges."""

    subtype = "pipe-flow"

    def _resolve_params(self, rng: DeterministicRNG) -> dict[str, int]:
        cfg = self.config.pipeFlow
        p = ROUTING_DIFFICULTY_PRESETS[self.subtype][self.config.difficulty]
        return {
            "depth": cfg.solutionDecisionDepth if cfg.solutionDecisionDepth is not None else p["solutionDecisionDepth"],
            "total": cfg.totalJunctionCount if cfg.totalJunctionCount is not None else (cfg.junctionCount if cfg.junctionCount is not None else p["totalJunctionCount"]),
            "tanks": cfg.tankCount if cfg.tankCount is not None else p["tanks"],
            "closed": cfg.closedValves if cfg.closedValves is not None else p["criticalClosedValveCount"],
            "decoys": cfg.decoyBranchCount if cfg.decoyBranchCount is not None else p["decoyBranchCount"],
        }

    def generate_one(self, seed: int) -> ChallengeBundle:
        rng = DeterministicRNG(seed, f"{self.level_key}:{self.subtype}")
        p = self._resolve_params(rng.fork("params"))
        if p["closed"] != p["decoys"]:
            raise ValueError("Each independent wrong-tank branch requires one critical closed valve")
        for attempt in range(100):
            attempt_rng = rng.fork(f"attempt_{attempt}")
            main, tanks, branches = build_route_network(
                attempt_rng, p["depth"], p["total"], p["decoys"], p["tanks"],
                self.config.canvasWidth, self.config.canvasHeight, "Tank",
            )
            nodes = main + [n for branch in branches for n in branch]
            # Move the blocker along each wrong route. Never block its first
            # edge: the branch must remain traceable beyond the main junction.
            blocked = {attempt_rng.choice(branch)["id"] for branch in branches}
            inlet = {"id": "inlet", "x": main[0]["x"], "y": 95.0}
            edges = [{"id": "inlet_next", "u": inlet, "v": main[0], "valve": "OPEN"}]
            for node in nodes:
                for side in ("next", "wrong"):
                    edges.append({"id": f"{node['id']}_{side}", "u": node, "v": node[side],
                                  "valve": "CLOSED" if side == "next" and node["id"] in blocked else "OPEN"})
            graph = private_graph_edges(edges)
            tank_map = {t["id"]: t["label"] for t in tanks}
            reachable = reachable_tanks(main[0]["id"], graph, tank_map)
            if len(reachable) != 1:
                continue  # Deterministic retry, without repairing valve states.
            target = next(iter(reachable))
            # Count essential blockers by opening each one independently.
            critical = 0
            for i, edge in enumerate(graph):
                if edge["valve"] == "CLOSED":
                    opened = [dict(e) for e in graph]
                    opened[i]["valve"] = "OPEN"
                    critical += len(reachable_tanks(main[0]["id"], opened, tank_map)) > 1
            if critical != p["closed"]:
                continue
            # Place unchanged-size valve housings away from other housings and
            # fittings. Long wrong branches permit varying blocker depths.
            placements = []
            layout_valid = True
            for edge in edges:
                if edge["u"]["id"] == "inlet" or edge["v"].get("cap"):
                    continue
                u, v = edge["u"], edge["v"]
                fractions = attempt_rng.fork(edge["id"]).shuffle([0.5, 0.35, 0.65, 0.25, 0.75])
                for fraction in fractions:
                    x = u["x"] + (v["x"] - u["x"]) * fraction
                    y = u["y"] + (v["y"] - u["y"]) * fraction
                    fittings_clear = all(abs(x - n["x"]) >= 40 or abs(y - n["y"]) >= 34 for n in nodes)
                    if fittings_clear and all(abs(x - px) >= 58 or abs(y - py) >= 42 for px, py in placements):
                        edge["valvePosition"] = (x, y)
                        placements.append((x, y))
                        break
                else:
                    layout_valid = False
                    break
            if not layout_valid:
                continue
            image = self._render_pipe_scene(
                self.config.canvasWidth, self.config.canvasHeight, [nodes], tanks, edges,
                (main[0]["x"], 95.0),
            )
            metadata = {
                "subtype": self.subtype, "difficulty": self.config.difficulty,
                "solutionDecisionDepth": len(main), "totalJunctionCount": len(nodes),
                "criticalClosedValveCount": critical, "decoyBranchCount": len(branches),
                "tankCount": len(tanks), "source": main[0]["id"], "tanks": tank_map,
                "edges": graph, "targetTank": target, "generationAttempt": attempt,
                "solutionPath": [n["id"] for n in main] + [tanks[0]["id"]],
                "decoyPaths": [[n["id"] for n in branch] + [branch[-1]["next"]["id"]] for branch in branches],
            }
            return self.build_bundle(seed, "Which tank will fill with water?",
                                     sorted(tank_map.values()), target, image, metadata)
        raise RuntimeError(f"Failed to generate independently verified Pipe Flow for seed {seed}")

    def _render_pipe_scene(
        self,
        width: int,
        height: int,
        tier_nodes: list[list[dict[str, Any]]],
        tank_nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        entry_pos: tuple[float, float],
    ) -> Image.Image:
        """Render clean schematic pipe network with distinct open/closed valve gates."""
        img = Image.new("RGB", (width, height), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Header banner
        draw_header_banner(
            draw=draw,
            width=width,
            height=height,
            badge_text="LEVEL 3A — PIPE FLOW",
            instruction_text="Trace the water flow through the OPEN valves to find which tank fills.",
            accent_color=COLOR_ACCENT_BLUE,
        )

        font_label = get_font(14, bold=True)
        font_tag = get_font(11, bold=True)

        # 1. Main Water Inlet pipe from top
        e_x, e_y = entry_pos
        top_node = tier_nodes[0][0]
        draw.line([(e_x, e_y), (top_node["x"], top_node["y"])], fill=COLOR_PIPE_OUTER, width=18)
        draw.line([(e_x, e_y), (top_node["x"], top_node["y"])], fill=(14, 116, 144), width=10)  # Fluid cyan-slate

        # 2. Draw all pipe branches (outer pipe and inner conduit)
        for e in edges:
            ux, uy = e["u"]["x"], e["u"]["y"]
            vx, vy = e["v"]["x"], e["v"]["y"]
            draw.line([(ux, uy), (vx, vy)], fill=COLOR_BG, width=24)
            draw.line([(ux, uy), (vx, vy)], fill=COLOR_PIPE_OUTER, width=18)
            draw.line([(ux, uy), (vx, vy)], fill=COLOR_PIPE_INNER, width=10)
            if e["v"].get("cap"):
                draw.ellipse([vx - 7, vy - 7, vx + 7, vy + 7], fill=COLOR_PIPE_OUTER, outline=COLOR_BORDER_LIGHT, width=2)

        # 3. Draw Junction fittings
        for tier in tier_nodes:
            for node in tier:
                nx, ny = node["x"], node["y"]
                draw.ellipse([nx - 14, ny - 14, nx + 14, ny + 14], fill=COLOR_PIPE_OUTER)
                draw.ellipse([nx - 8, ny - 8, nx + 8, ny + 8], fill=COLOR_BORDER_LIGHT)

        # 4. Draw Valves on each edge
        for e in edges:
            if "valvePosition" not in e:
                continue
            ux, uy = e["u"]["x"], e["u"]["y"]
            vx, vy = e["v"]["x"], e["v"]["y"]
            mx, my = e["valvePosition"]
            is_open = e["valve"] == "OPEN"

            # Valve housing body
            bw, bh = 48, 26
            bx1, by1 = mx - bw / 2, my - bh / 2
            bx2, by2 = mx + bw / 2, my + bh / 2

            if is_open:
                # OPEN VALVE: Green inline channel + parallel handle + OPEN label
                draw.rounded_rectangle([bx1, by1, bx2, by2], radius=4, fill=(5, 46, 22), outline=COLOR_VALVE_OPEN, width=2)
                # Inline aperture line (flow permitted)
                draw.line([(mx - 14, my), (mx + 14, my)], fill=COLOR_VALVE_OPEN, width=3)
                # Parallel handle
                draw.line([(mx, my - 16), (mx, my - 6)], fill=(248, 250, 252), width=3)
                # Text tag
                draw.text((mx - 16, my - 6), "OPEN", fill=COLOR_VALVE_OPEN, font=font_tag)
            else:
                # CLOSED VALVE: Red barrier plate + perpendicular handle + CLOSED label
                draw.rounded_rectangle([bx1, by1, bx2, by2], radius=4, fill=(69, 10, 10), outline=COLOR_VALVE_CLOSED, width=2)
                # Perpendicular barrier bar across pipe
                draw.line([(mx, my - 9), (mx, my + 9)], fill=COLOR_VALVE_CLOSED, width=4)
                # Perpendicular handle cross
                draw.line([(mx - 6, my - 16), (mx + 6, my - 16)], fill=(248, 250, 252), width=3)
                draw.line([(mx, my - 16), (mx, my - 6)], fill=(248, 250, 252), width=2)
                # Text tag
                draw.text((mx - 20, my - 6), "CLOSED", fill=COLOR_VALVE_CLOSED, font=font_tag)

        # 5. Draw Water Inlet Badge
        inlet_w, inlet_h = 120, 40
        ix1 = int(e_x - inlet_w / 2)
        iy1 = int(e_y - 12)
        draw.rounded_rectangle(
            [ix1, iy1, ix1 + inlet_w, iy1 + inlet_h],
            radius=6,
            fill=(8, 51, 68),  # Cyan-950
            outline=COLOR_ACCENT_CYAN,
            width=2,
        )
        draw.text((ix1 + 14, iy1 + 11), "WATER INLET", fill=COLOR_ACCENT_CYAN, font=get_font(12, bold=True))

        # 6. Draw Destination Tanks
        for i, t in enumerate(tank_nodes):
            tx = t["x"]
            ty = t["y"]
            t_color = TANK_COLORS[i % len(TANK_COLORS)]
            tw, th = 110, 56
            x1 = tx - tw / 2
            y1 = ty - th / 2
            x2 = tx + tw / 2
            y2 = ty + th / 2

            # Tank body
            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=8,
                fill=(15, 23, 42),
                outline=t_color,
                width=3,
            )
            # Level measurement lines on tank side
            for step in range(3):
                ly = y1 + 14 + step * 10
                draw.line([(x1 + 8, ly), (x1 + 18, ly)], fill=COLOR_BORDER_LIGHT, width=2)

            # Tank label
            draw.text((x1 + 28, y1 + 18), t["label"], fill=COLOR_TEXT_PRIMARY, font=font_label)

        return img
