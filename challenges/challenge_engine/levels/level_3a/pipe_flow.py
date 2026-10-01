"""Pipe Flow routing puzzle generator (Level 3A subtype).

Water enters a plumbing distribution network from a main inlet and flows through
junctions and inline valves towards destination storage tanks.
Valves have clearly distinguishable OPEN (inline green aperture) and CLOSED (perpendicular red barrier)
mechanical states. The user visualizes flow connectivity to determine which tank receives water.
"""

from __future__ import annotations

import collections
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
        cfg_sub = self.config.pipeFlow
        diff = self.config.difficulty
        presets = ROUTING_DIFFICULTY_PRESETS["pipe-flow"].get(
            diff, ROUTING_DIFFICULTY_PRESETS["pipe-flow"]["medium"]
        )
        return {
            "junctions": cfg_sub.junctionCount or presets["junctions"],
            "tanks": cfg_sub.tankCount or presets["tanks"],
            "closedValves": cfg_sub.closedValves or presets["closedValves"],
        }

    def generate_one(self, seed: int) -> ChallengeBundle:
        rng = DeterministicRNG(seed, f"{self.level_key}:{self.subtype}")
        params = self._resolve_params(rng.fork("params"))
        n_tanks = min(max(3, params["tanks"]), 5)

        width = self.config.canvasWidth
        height = self.config.canvasHeight

        # Build tree network from Inlet -> Tanks
        # Tiers of split junctions
        num_tiers = 3 if n_tanks <= 4 else 4
        y_top = 110.0
        y_bottom = height - 90.0
        y_step = (y_bottom - y_top) / (num_tiers + 1)

        # Generate tier nodes
        tier_nodes: list[list[dict[str, Any]]] = []
        entry_x = width / 2.0
        entry_y = y_top + y_step
        tier_nodes.append([{"x": entry_x, "y": entry_y, "tier": 0, "idx": 0}])

        for t in range(1, num_tiers):
            tier_y = y_top + (t + 1) * y_step
            count = min(t + 1, n_tanks)
            span = width * 0.72
            xs = [width / 2.0 - span / 2.0 + (span / (count - 1)) * i for i in range(count)]
            nodes_in_tier = [{"x": nx, "y": tier_y, "tier": t, "idx": i} for i, nx in enumerate(xs)]
            tier_nodes.append(nodes_in_tier)

        # Destination tanks at the bottom
        span_tanks = width * 0.76
        tank_xs = [
            width / 2.0 - span_tanks / 2.0 + (span_tanks / (n_tanks - 1)) * i
            for i in range(n_tanks)
        ]
        tank_nodes = [
            {"x": tx, "y": y_bottom, "label": f"Tank {chr(65 + i)}", "idx": i}
            for i, tx in enumerate(tank_xs)
        ]

        # Connect pipe edges and assign valves
        # Each edge from parent to child has a valve that can be OPEN or CLOSED
        edges: list[dict[str, Any]] = []

        for t, nodes in enumerate(tier_nodes):
            for i, node in enumerate(nodes):
                if t < num_tiers - 1:
                    next_nodes = tier_nodes[t + 1]
                    lc = next_nodes[min(i, len(next_nodes) - 1)]
                    rc = next_nodes[min(i + 1, len(next_nodes) - 1)]
                else:
                    lc = tank_nodes[min(i, len(tank_nodes) - 1)]
                    rc = tank_nodes[min(i + 1, len(tank_nodes) - 1)]

                node["left_child"] = lc
                node["right_child"] = rc

                # Create edge objects with midpoints for valves
                edge_l = {
                    "id": f"e_{t}_{i}_L",
                    "u": node,
                    "v": lc,
                    "side": "left",
                    "valve": "OPEN",  # Default open, will adjust
                }
                edge_r = {
                    "id": f"e_{t}_{i}_R",
                    "u": node,
                    "v": rc,
                    "side": "right",
                    "valve": "OPEN",
                }
                edges.append(edge_l)
                edges.append(edge_r)
                node["edge_l"] = edge_l
                node["edge_r"] = edge_r

        # Select exactly ONE target tank to be reachable
        target_tank_idx = rng.fork("target").randint(0, n_tanks - 1)
        target_tank = tank_nodes[target_tank_idx]["label"]

        # Ensure reachability: exactly ONE tank reachable from root via OPEN valves
        # We can set valve states: at each fork on the path to target_tank, set that edge OPEN and other edge CLOSED
        # Trace path from root to target_tank:
        def find_path_to_target(curr: dict[str, Any]) -> list[dict[str, Any]] | None:
            if curr.get("label") == target_tank:
                return []
            if "left_child" not in curr:
                return None
            # Try left
            p_left = find_path_to_target(curr["left_child"])
            if p_left is not None:
                return [curr["edge_l"]] + p_left
            p_right = find_path_to_target(curr["right_child"])
            if p_right is not None:
                return [curr["edge_r"]] + p_right
            return None

        solution_edges = find_path_to_target(tier_nodes[0][0])
        if not solution_edges:
            # Fallback path directly to leftmost or rightmost
            solution_edges = []

        sol_edge_set = set(e["id"] for e in solution_edges)

        # Set all solution edges to OPEN
        for e in solution_edges:
            e["valve"] = "OPEN"

        # For non-solution branches, close enough valves so NO other tank is reachable
        for node in [n for tier in tier_nodes for n in tier]:
            el = node.get("edge_l")
            er = node.get("edge_r")
            if el and er:
                if el["id"] in sol_edge_set and er["id"] not in sol_edge_set:
                    er["valve"] = "CLOSED"
                elif er["id"] in sol_edge_set and el["id"] not in sol_edge_set:
                    el["valve"] = "CLOSED"
                elif el["id"] not in sol_edge_set and er["id"] not in sol_edge_set:
                    # Randomly open or close deterministically
                    el["valve"] = rng.fork(f"v_{el['id']}").choice(["OPEN", "CLOSED"])
                    er["valve"] = rng.fork(f"v_{er['id']}").choice(["OPEN", "CLOSED"])

        # BFS reachability verification from root
        reachable_tanks: set[str] = set()
        queue = collections.deque([tier_nodes[0][0]])
        visited_nodes: set[str] = {"node_0_0"}

        while queue:
            curr = queue.popleft()
            if "label" in curr:
                reachable_tanks.add(curr["label"])
                continue

            c_key_l = f"node_{curr['left_child'].get('tier', 't')}_{curr['left_child'].get('idx', 'i')}_{curr['left_child'].get('label', '')}"
            el = curr.get("edge_l")
            if el and el["valve"] == "OPEN" and c_key_l not in visited_nodes:
                visited_nodes.add(c_key_l)
                queue.append(el["v"])

            c_key_r = f"node_{curr['right_child'].get('tier', 't')}_{curr['right_child'].get('idx', 'i')}_{curr['right_child'].get('label', '')}"
            er = curr.get("edge_r")
            if er and er["valve"] == "OPEN" and c_key_r not in visited_nodes:
                visited_nodes.add(c_key_r)
                queue.append(er["v"])

        # If more than 1 tank is reachable, close the leaks
        if reachable_tanks != {target_tank}:
            for e in edges:
                if e["id"] not in sol_edge_set:
                    e["valve"] = "CLOSED"

        options = [t["label"] for t in tank_nodes]

        # Render visual scene
        img = self._render_pipe_scene(
            width=width,
            height=height,
            tier_nodes=tier_nodes,
            tank_nodes=tank_nodes,
            edges=edges,
            entry_pos=(entry_x, y_top),
        )

        instruction = "Which tank will receive water from the main inlet?"
        private_meta = {
            "subtype": self.subtype,
            "difficulty": self.config.difficulty,
            "junctionCount": sum(len(tn) for tn in tier_nodes),
            "targetTank": target_tank,
            "options": options,
        }

        return self.build_bundle(
            seed=seed,
            instruction=instruction,
            options=options,
            correct_answer=target_tank,
            image=img,
            private_routing_metadata=private_meta,
        )

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
            draw.line([(ux, uy), (vx, vy)], fill=COLOR_PIPE_OUTER, width=18)
            draw.line([(ux, uy), (vx, vy)], fill=COLOR_PIPE_INNER, width=10)

        # 3. Draw Junction fittings
        for tier in tier_nodes:
            for node in tier:
                nx, ny = node["x"], node["y"]
                draw.ellipse([nx - 14, ny - 14, nx + 14, ny + 14], fill=COLOR_PIPE_OUTER)
                draw.ellipse([nx - 8, ny - 8, nx + 8, ny + 8], fill=COLOR_BORDER_LIGHT)

        # 4. Draw Valves on each edge
        for e in edges:
            ux, uy = e["u"]["x"], e["u"]["y"]
            vx, vy = e["v"]["x"], e["v"]["y"]
            mx = (ux + vx) / 2.0
            my = (uy + vy) / 2.0
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
