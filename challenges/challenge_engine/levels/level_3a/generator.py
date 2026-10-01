"""Procedural generator for Level 3A — The Tangled Cables.

NOTE: Level 3A is the ONLY fully procedurally generated challenge level in the system.
It generates the logical one-to-one connection graph FIRST, validates routes SECOND,
and renders the visual challenge THIRD.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.ids import asset_relpath_for_index, generate_challenge_id
from challenge_engine.core.random import DeterministicRNG
from challenge_engine.core.schemas import (
    LEGACY_TANGLED_CABLE_DIFFICULTY_PRESETS,
    LEVEL_3A_KEY,
    CableAnnotations,
    CableIntersection,
    CableQuery,
    Level3AConfig,
    PrivateAnswer,
    PublicChallenge,
    PublicUIConfig,
)
from challenge_engine.levels.level_3a.base import RoutingPuzzleSubtypeGenerator
from challenge_engine.levels.level_3a.conveyor_routing import ConveyorRoutingGenerator
from challenge_engine.levels.level_3a.device_cables import DeviceCablesGenerator
from challenge_engine.levels.level_3a.laser_maze import LaserMazeGenerator
from challenge_engine.levels.level_3a.pipe_flow import PipeFlowGenerator


def _cubic_bezier_segment(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 16,
) -> list[tuple[float, float]]:
    """Sample a cubic Bezier curve from p0 to p3 (excluding p0)."""
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


def _build_smooth_cable_path(
    waypoints: list[tuple[float, float]],
    subdivisions: int = 16,
) -> list[tuple[float, float]]:
    """Interpolate a smooth monotone-X cubic Bezier polyline through `waypoints`."""
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


def _find_polyline_intersections(
    poly_a: np.ndarray,
    poly_b: np.ndarray,
) -> list[tuple[float, float]]:
    """Find all geometric intersections between two 2D polylines using vectorized segment checks."""
    p1 = poly_a[:-1]
    p2 = poly_a[1:]
    q1 = poly_b[:-1]
    q2 = poly_b[1:]

    a_min_x = np.minimum(p1[:, 0], p2[:, 0])[:, None]
    a_max_x = np.maximum(p1[:, 0], p2[:, 0])[:, None]
    a_min_y = np.minimum(p1[:, 1], p2[:, 1])[:, None]
    a_max_y = np.maximum(p1[:, 1], p2[:, 1])[:, None]

    b_min_x = np.minimum(q1[:, 0], q2[:, 0])[None, :]
    b_max_x = np.maximum(q1[:, 0], q2[:, 0])[None, :]
    b_min_y = np.minimum(q1[:, 1], q2[:, 1])[None, :]
    b_max_y = np.maximum(q1[:, 1], q2[:, 1])[None, :]

    overlap = (
        (a_max_x >= b_min_x)
        & (b_max_x >= a_min_x)
        & (a_max_y >= b_min_y)
        & (b_max_y >= a_min_y)
    )
    cand_i, cand_j = np.nonzero(overlap)
    if cand_i.size == 0:
        return []

    pa = p1[cand_i]
    pb = p2[cand_i]
    qa = q1[cand_j]
    qb = q2[cand_j]

    r = pb - pa
    s = qb - qa
    rxs = r[:, 0] * s[:, 1] - r[:, 1] * s[:, 0]
    valid_denom = np.abs(rxs) > 1e-7
    if not np.any(valid_denom):
        return []

    pa = pa[valid_denom]
    qa = qa[valid_denom]
    r = r[valid_denom]
    s = s[valid_denom]
    rxs = rxs[valid_denom]

    qp = qa - pa
    t = (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / rxs
    u = (qp[:, 0] * r[:, 1] - qp[:, 1] * r[:, 0]) / rxs

    hit = (t >= 0.0) & (t <= 1.0) & (u >= 0.0) & (u <= 1.0)
    if not np.any(hit):
        return []

    pts = pa[hit] + t[hit, None] * r[hit]
    results: list[tuple[float, float]] = []
    for pt in pts:
        ix, iy = float(pt[0]), float(pt[1])
        if not any((ix - rx) ** 2 + (iy - ry) ** 2 < 4.0 for rx, ry in results):
            results.append((round(ix, 2), round(iy, 2)))
    return results


class Level3ATangledCablesGenerator:
    """Generates procedural Tangled Cables challenges (logical graph first, visual scene second)."""

    level_key = LEVEL_3A_KEY

    def __init__(self, config: Level3AConfig) -> None:
        self.config = config

    def _resolve_cable_count(self, rng: DeterministicRNG) -> int:
        if self.config.cableCount is not None:
            return self.config.cableCount
        preset = LEGACY_TANGLED_CABLE_DIFFICULTY_PRESETS.get(
            self.config.difficulty,
            LEGACY_TANGLED_CABLE_DIFFICULTY_PRESETS["hard"],
        )
        c_min, c_max = preset["cableCountRange"]
        return rng.randint(c_min, c_max)

    def generate_one(self, seed: int) -> ChallengeBundle:
        """Generate a single deterministic Level 3A Tangled Cables challenge."""
        rng = DeterministicRNG(seed, self.level_key)
        challenge_id = generate_challenge_id(self.level_key, seed)

        width = self.config.canvasWidth
        height = self.config.canvasHeight
        n_cables = self._resolve_cable_count(rng.fork("cable_count"))

        # STEP 1: Create endpoints
        top_margin = 76.0
        bottom_margin = 54.0
        usable_h = height - top_margin - bottom_margin
        step_y = usable_h / float(max(1, n_cables - 1)) if n_cables > 1 else 0.0

        left_pin_x = 175.0
        right_pin_x = float(width - 175)

        sources = [f"server_{i + 1}" for i in range(n_cables)]
        destinations = [f"port_{i + 1}" for i in range(n_cables)]

        source_positions: dict[str, list[float]] = {}
        dest_positions: dict[str, list[float]] = {}
        for i, s_name in enumerate(sources):
            sy = round(top_margin + i * step_y, 2)
            source_positions[s_name] = [left_pin_x, sy]
        for i, d_name in enumerate(destinations):
            dy = round(top_margin + i * step_y, 2)
            dest_positions[d_name] = [right_pin_x, dy]

        # STEP 2: Create one-to-one mapping / permutation
        shuffled_dests = rng.fork("permutation").shuffle(destinations)
        connections: dict[str, str] = {
            src: dst for src, dst in zip(sources, shuffled_dests)
        }

        # STEP 3: Generate cable routes
        w_min, w_max = self.config.waypointRange
        num_cols = rng.fork("waypoints").randint(w_min, w_max)

        route_left_x = left_pin_x + 55.0
        route_right_x = right_pin_x - 55.0
        col_xs = np.linspace(route_left_x, route_right_x, num_cols)

        slot_ys_base = np.linspace(top_margin + 10.0, height - bottom_margin - 10.0, n_cables)
        col_assignments: list[list[float]] = []
        for col_idx in range(num_cols):
            col_rng = rng.fork(f"col_{col_idx}")
            perm_indices = col_rng.shuffle(list(range(n_cables)))
            col_y_for_cable: list[float] = [0.0] * n_cables
            max_jitter = min(8.0, step_y * 0.28)
            for cable_idx, slot_idx in enumerate(perm_indices):
                jitter = col_rng.uniform(-max_jitter, max_jitter)
                y_val = float(
                    np.clip(
                        slot_ys_base[slot_idx] + jitter,
                        top_margin + 4.0,
                        height - bottom_margin - 4.0,
                    )
                )
                col_y_for_cable[cable_idx] = round(y_val, 2)
            col_assignments.append(col_y_for_cable)

        control_points: dict[str, list[list[float]]] = {}
        centerlines: dict[str, list[list[float]]] = {}
        polylines_np: dict[str, np.ndarray] = {}
        cable_masks: dict[str, dict[str, Any]] = {}

        for cable_idx, src in enumerate(sources):
            dst = connections[src]
            start_pt = (source_positions[src][0], source_positions[src][1])
            end_pt = (dest_positions[dst][0], dest_positions[dst][1])

            lead_in = (start_pt[0] + 22.0, start_pt[1])
            lead_out = (end_pt[0] - 22.0, end_pt[1])

            waypoints: list[tuple[float, float]] = [start_pt, lead_in]
            for col_idx in range(num_cols):
                wx = float(col_xs[col_idx])
                wy = col_assignments[col_idx][cable_idx]
                waypoints.append((round(wx, 2), round(wy, 2)))
            waypoints.extend([lead_out, end_pt])

            control_points[src] = [[round(px, 2), round(py, 2)] for px, py in waypoints]
            smooth_pts = _build_smooth_cable_path(waypoints, subdivisions=16)
            centerlines[src] = [[round(px, 2), round(py, 2)] for px, py in smooth_pts]
            arr = np.asarray(smooth_pts, dtype=np.float64)
            polylines_np[src] = arr

            min_xy = arr.min(axis=0)
            max_xy = arr.max(axis=0)
            cable_masks[src] = {
                "boundingBox": [
                    round(float(min_xy[0]), 2),
                    round(float(min_xy[1]), 2),
                    round(float(max_xy[0]), 2),
                    round(float(max_xy[1]), 2),
                ],
                "strokeWidth": self.config.lineWidth,
                "vertexCount": len(smooth_pts),
            }

        # STEP 4: Validate routes & compute intersections
        layer_order = rng.fork("layer_order").shuffle(sources)
        intersections: list[CableIntersection] = []

        for idx_under in range(len(layer_order)):
            under_src = layer_order[idx_under]
            arr_under = polylines_np[under_src]
            if (
                np.any(arr_under[:, 0] < 0)
                or np.any(arr_under[:, 0] > width)
                or np.any(arr_under[:, 1] < 0)
                or np.any(arr_under[:, 1] > height)
            ):
                raise RuntimeError(f"Generated cable {under_src} exceeded canvas bounds")

            for idx_over in range(idx_under + 1, len(layer_order)):
                over_src = layer_order[idx_over]
                arr_over = polylines_np[over_src]
                crossings = _find_polyline_intersections(arr_under, arr_over)
                for cx, cy in crossings:
                    intersections.append(
                        CableIntersection(
                            point=[cx, cy],
                            overCable=over_src,
                            underCable=under_src,
                        )
                    )

        # STEP 5: Choose query
        q_rng = rng.fork("query")
        if self.config.queryType in {"find_destination", "find-destination"}:
            q_type = self.config.queryType
            is_find_source = False
        else:
            q_type = (
                "find-source"
                if self.config.queryType == "find-source"
                else "find_source"
            )
            is_find_source = True

        if is_find_source:
            target_port = q_rng.choice(destinations)
            inverse_map = {dst: src for src, dst in connections.items()}
            correct_answer = inverse_map[target_port]
            options = list(sources)
            instruction = f"Which server is connected to the highlighted port ({target_port})?"
            query_obj = CableQuery(type=q_type, target=target_port)  # type: ignore[arg-type]
        else:
            target_server = q_rng.choice(sources)
            correct_answer = connections[target_server]
            options = list(destinations)
            instruction = f"Which port is connected to the highlighted server ({target_server})?"
            query_obj = CableQuery(type=q_type, target=target_server)  # type: ignore[arg-type]

        correct_index = options.index(correct_answer)

        # STEP 6: Render visual scene with unambiguous over/under bridges
        bg_color = (20, 24, 32)
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        draw.rectangle([0, 0, width, 44], fill=(28, 34, 46))
        draw.text(
            (24, 15),
            f"NETWORK PATCH PANEL  |  {instruction}",
            fill=(225, 232, 245),
            font=font,
        )

        palette = [
            (235, 75, 75),
            (65, 175, 245),
            (85, 215, 115),
            (245, 190, 55),
            (185, 105, 245),
            (245, 125, 60),
            (65, 220, 205),
            (235, 95, 175),
            (165, 225, 70),
            (110, 135, 245),
        ]

        lw = self.config.lineWidth
        bridge_w = lw + 8
        casing_w = lw + 4

        for src in layer_order:
            src_idx = int(src.split("_")[1]) - 1
            base_col = palette[src_idx % len(palette)]
            highlight_col = (
                min(255, base_col[0] + 55),
                min(255, base_col[1] + 55),
                min(255, base_col[2] + 55),
            )
            pts = [tuple(pt) for pt in centerlines[src]]

            draw.line(pts, fill=bg_color, width=bridge_w, joint="curve")
            draw.line(pts, fill=(8, 10, 14), width=casing_w, joint="curve")
            draw.line(pts, fill=base_col, width=lw, joint="curve")
            draw.line(pts, fill=highlight_col, width=1, joint="curve")

        box_h = max(12, min(22, int(step_y * 0.76))) if n_cables > 1 else 22
        half_bh = box_h // 2

        for src in sources:
            px, py = source_positions[src]
            is_highlighted = (not is_find_source) and query_obj.target == src
            fill_c = (75, 58, 18) if is_highlighted else (38, 45, 58)
            outline_c = (255, 205, 45) if is_highlighted else (110, 125, 150)
            outline_w = 3 if is_highlighted else 1

            draw.rounded_rectangle(
                [18, int(py - half_bh), int(px - 6), int(py + half_bh)],
                radius=4,
                fill=fill_c,
                outline=outline_c,
                width=outline_w,
            )
            draw.ellipse([int(px - 5), int(py - 5), int(px + 5), int(py + 5)], fill=outline_c)
            label_txt = f"{src} [TARGET]" if is_highlighted else src
            draw.text((28, int(py - 5)), label_txt, fill=(245, 248, 255), font=font)

        for dst in destinations:
            px, py = dest_positions[dst]
            is_highlighted = is_find_source and query_obj.target == dst
            fill_c = (85, 62, 16) if is_highlighted else (38, 45, 58)
            outline_c = (255, 205, 45) if is_highlighted else (110, 125, 150)
            outline_w = 3 if is_highlighted else 1

            draw.rounded_rectangle(
                [int(px + 6), int(py - half_bh), width - 18, int(py + half_bh)],
                radius=4,
                fill=fill_c,
                outline=outline_c,
                width=outline_w,
            )
            draw.ellipse([int(px - 5), int(py - 5), int(px + 5), int(py + 5)], fill=outline_c)
            label_txt = f"[TARGET] {dst}" if is_highlighted else dst
            draw.text((int(px + 14), int(py - 5)), label_txt, fill=(245, 248, 255), font=font)

        # STEP 7: Export ground truth
        rel_asset = asset_relpath_for_index(0, ext="webp")

        public_challenge = PublicChallenge(
            schemaVersion=1,
            id=challenge_id,
            level=3,
            variant="tangled-cables",
            type="single-choice",
            instruction=instruction,
            seed=seed,
            assets=[rel_asset],
            ui=PublicUIConfig(
                rows=1,
                columns=1,
                selectionMode="single",
                options=options,
            ),
        )

        private_answer = PrivateAnswer(
            challengeId=challenge_id,
            levelKey=self.level_key,
            datasetSource="procedural-tangled-cables",
            correctSelection=[correct_index],
            answer=correct_answer,
            connections=connections,
            query=query_obj,
            annotations=CableAnnotations(
                canvasDimensions=[width, height],
                endpointPositions={
                    "sources": source_positions,
                    "destinations": dest_positions,
                },
                controlPoints=control_points,
                centerlines=centerlines,
                cableMasks=cable_masks,
                intersections=intersections,
                layerOrder=layer_order,
                difficultyMetadata={
                    "difficulty": self.config.difficulty,
                    "cableCount": n_cables,
                    "waypointColumnCount": num_cols,
                    "crossingCount": len(intersections),
                    "lineWidth": self.config.lineWidth,
                },
            ),
        )

        return ChallengeBundle(
            public_challenge=public_challenge,
            private_answer=private_answer,
            assets={rel_asset: img},
            lossless_webp=True,
        )

    def generate_batch(self, count: int, base_seed: int) -> list[ChallengeBundle]:
        """Generate `count` deterministic Level 3A challenges starting from `base_seed`."""
        return [self.generate_one(base_seed + i) for i in range(count)]


class Level3ARoutingGenerator:
    """Procedural generator for the Level 3A Routing Puzzles family.

    Subtypes:
      - 'laser-maze': Grid-based optical ray tracing (Story Mode default)
      - 'conveyor-routing': Industrial directed diverter routing
      - 'pipe-flow': Plumbing network with open/closed valve gates
      - 'device-cables': Clean device-to-outlet cable tracing with crossing halos
    """

    level_key = LEVEL_3A_KEY

    def __init__(self, config: Level3AConfig) -> None:
        self.config = config
        self._subgenerators: dict[str, type[RoutingPuzzleSubtypeGenerator]] = {
            "laser-maze": LaserMazeGenerator,
            "conveyor-routing": ConveyorRoutingGenerator,
            "pipe-flow": PipeFlowGenerator,
            "device-cables": DeviceCablesGenerator,
        }

    def _resolve_generator(self, subtype: str | None = None) -> Any:
        st = subtype or self.config.subtype or self.config.defaultSubtype or "laser-maze"
        if st in self._subgenerators:
            return self._subgenerators[st](self.config)
        if st == "tangled-cables" or (
            self.config.cableCount is not None and not subtype and not self.config.subtype
        ):
            return Level3ATangledCablesGenerator(self.config)
        return LaserMazeGenerator(self.config)

    def generate_one(self, seed: int, subtype: str | None = None) -> ChallengeBundle:
        """Generate a single deterministic Level 3A routing puzzle."""
        gen = self._resolve_generator(subtype)
        return gen.generate_one(seed)

    def generate_batch(self, count: int, base_seed: int) -> list[ChallengeBundle]:
        """Generate `count` deterministic Level 3A challenges.

        If subtype is 'all', round-robins across the 4 distinct routing puzzle subtypes.
        Otherwise generates challenges of the selected subtype (defaulting to 'laser-maze').
        """
        target_subtype = self.config.subtype or self.config.defaultSubtype or "laser-maze"
        if target_subtype == "all":
            subtypes = ["laser-maze", "conveyor-routing", "pipe-flow", "device-cables"]
            bundles: list[ChallengeBundle] = []
            for i in range(count):
                st = subtypes[i % len(subtypes)]
                gen = self._resolve_generator(st)
                bundles.append(gen.generate_one(base_seed + i))
            return bundles
        else:
            gen = self._resolve_generator(target_subtype)
            return [gen.generate_one(base_seed + i) for i in range(count)]

