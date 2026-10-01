"""Laser Maze routing puzzle generator (Level 3A primary subtype).

A laser beam enters an optical grid from an emitter on the perimeter, reflects
off 45-degree mirrors ('/' and '\\'), and reaches exactly one perimeter sensor target.
The user must visually trace the beam to determine which target is struck.
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
    COLOR_ACCENT_CYAN,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_PURPLE,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_HEADER_BG,
    COLOR_LASER_BEAM,
    COLOR_LASER_GLOW,
    COLOR_LASER_RED,
    COLOR_TEXT_DIM,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    RoutingPuzzleSubtypeGenerator,
    draw_header_banner,
    get_font,
)

# Direction constants: (dr, dc)
UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)

TARGET_COLORS = [
    COLOR_ACCENT_CYAN,
    COLOR_ACCENT_AMBER,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_PURPLE,
    (236, 72, 153),  # Pink-500
    (59, 130, 246),  # Blue-500
]


def _reflect(direction: tuple[int, int], mirror: str) -> tuple[int, int]:
    """Reflect ray off a 45-degree mirror."""
    dr, dc = direction
    if mirror == "/":
        return (-dc, -dr)
    elif mirror == "\\":
        return (dc, dr)
    raise ValueError(f"Unknown mirror type: {mirror}")


class LaserMazeGenerator(RoutingPuzzleSubtypeGenerator):
    """Procedural generator for Laser Maze routing challenges."""

    subtype = "laser-maze"

    def _resolve_params(self, rng: DeterministicRNG) -> dict[str, Any]:
        cfg_sub = self.config.laserMaze
        diff = self.config.difficulty
        presets = ROUTING_DIFFICULTY_PRESETS["laser-maze"].get(
            diff, ROUTING_DIFFICULTY_PRESETS["laser-maze"]["medium"]
        )

        grid = cfg_sub.gridSize or presets["grid"]
        ref_min, ref_max = cfg_sub.reflectionsRange or presets["reflections"]
        n_targets = cfg_sub.targetCount or presets["targets"]
        d_min, d_max = cfg_sub.distractorMirrors or presets["distractors"]

        n_reflections = rng.randint(ref_min, ref_max)
        n_distractors = rng.randint(d_min, d_max)

        return {
            "rows": grid[0],
            "cols": grid[1],
            "reflections": n_reflections,
            "targets": n_targets,
            "distractors": n_distractors,
        }

    def _simulate_ray(
        self,
        rows: int,
        cols: int,
        start_pos: tuple[int, int],
        start_dir: tuple[int, int],
        mirrors: dict[tuple[int, int], str],
    ) -> tuple[list[tuple[int, int]], list[tuple[int, int]], tuple[int, int] | None]:
        """Simulate ray traversal. Returns (visited_cells, reflection_cells, exit_border_pos)."""
        r, c = start_pos
        dr, dc = start_dir
        visited: list[tuple[int, int]] = []
        reflections: list[tuple[int, int]] = []
        seen_states: set[tuple[int, int, int, int]] = set()

        while True:
            state = (r, c, dr, dc)
            if state in seen_states:
                # Cycle / loop detected
                return visited, reflections, None
            seen_states.add(state)

            if not (0 <= r < rows and 0 <= c < cols):
                # Ray exited the grid
                return visited, reflections, (r, c)

            visited.append((r, c))

            if (r, c) in mirrors:
                m_type = mirrors[(r, c)]
                reflections.append((r, c))
                dr, dc = _reflect((dr, dc), m_type)

            r += dr
            c += dc

    def generate_one(self, seed: int) -> ChallengeBundle:
        rng = DeterministicRNG(seed, f"{self.level_key}:{self.subtype}")
        params = self._resolve_params(rng.fork("params"))
        rows, cols = params["rows"], params["cols"]
        desired_reflections = params["reflections"]
        target_count = min(params["targets"], 6)

        # Attempt procedural generation until a clean solvable layout is produced
        for attempt in range(100):
            attempt_rng = rng.fork(f"attempt_{attempt}")

            # 1. Choose emitter on perimeter
            # Pick a starting side: 0=Left, 1=Top
            side = attempt_rng.randint(0, 1)
            if side == 0:
                # Left border entering rightward
                start_r = attempt_rng.randint(1, rows - 2)
                start_c = 0
                start_dir = RIGHT
                emitter_pos = (start_r, -1)
            else:
                # Top border entering downward
                start_r = 0
                start_c = attempt_rng.randint(1, cols - 2)
                start_dir = DOWN
                emitter_pos = (-1, start_c)

            # 2. Build reflection path
            mirrors: dict[tuple[int, int], str] = {}
            curr_r, curr_c = start_r, start_c
            curr_dir = start_dir
            path_cells: set[tuple[int, int]] = set()
            valid_path = True

            for step in range(desired_reflections):
                path_cells.add((curr_r, curr_c))
                # Choose length to travel before placing next mirror
                dr, dc = curr_dir
                avail_steps: list[int] = []
                tr, tc = curr_r + dr, curr_c + dc
                s = 0
                while 0 <= tr < rows and 0 <= tc < cols:
                    s += 1
                    if (tr, tc) not in mirrors:
                        avail_steps.append(s)
                    tr += dr
                    tc += dc

                if not avail_steps:
                    valid_path = False
                    break

                # Pick step count for next mirror
                step_dist = attempt_rng.choice(avail_steps)
                next_r = curr_r + dr * step_dist
                next_c = curr_c + dc * step_dist

                # Mark all cells in straight line
                for k in range(step_dist):
                    path_cells.add((curr_r + dr * k, curr_c + dc * k))

                # Choose mirror orientation that keeps ray in bounds or directs towards exit
                valid_types: list[str] = []
                for m in ["/", "\\"]:
                    ndr, ndc = _reflect((dr, dc), m)
                    check_r, check_c = next_r + ndr, next_c + ndc
                    # Don't immediate exit if not at final reflection
                    if step < desired_reflections - 1:
                        if 0 <= check_r < rows and 0 <= check_c < cols:
                            valid_types.append(m)
                    else:
                        # Final reflection: can stay or head towards perimeter
                        valid_types.append(m)

                if not valid_types:
                    valid_path = False
                    break

                chosen_m = attempt_rng.choice(valid_types)
                mirrors[(next_r, next_c)] = chosen_m
                curr_r, curr_c = next_r, next_c
                curr_dir = _reflect((dr, dc), chosen_m)

            if not valid_path:
                continue

            # Trace ray to exit
            dr, dc = curr_dir
            tr, tc = curr_r, curr_c
            while 0 <= tr < rows and 0 <= tc < cols:
                path_cells.add((tr, tc))
                tr += dr
                tc += dc
            exit_pos = (tr, tc)

            # Verify ray simulation from emitter
            visited, actual_refs, sim_exit = self._simulate_ray(
                rows, cols, (start_r, start_c), start_dir, mirrors
            )

            if sim_exit != exit_pos or len(actual_refs) != desired_reflections:
                continue

            # 3. Place Targets
            # Exit position becomes target 0 (the correct target)
            all_perimeter_slots: list[tuple[int, int]] = []
            # Bottom border
            for c in range(cols):
                all_perimeter_slots.append((rows, c))
            # Right border
            for r in range(rows):
                all_perimeter_slots.append((r, cols))
            # Top border
            for c in range(cols):
                all_perimeter_slots.append((-1, c))
            # Left border
            for r in range(rows):
                all_perimeter_slots.append((r, -1))

            # Remove emitter and exit positions from candidate decoys
            decoy_candidates = [
                p
                for p in all_perimeter_slots
                if p != emitter_pos
                and p != exit_pos
                and math.hypot(p[0] - exit_pos[0], p[1] - exit_pos[1]) >= 1.5
            ]

            if len(decoy_candidates) < target_count - 1:
                continue

            chosen_decoys = attempt_rng.sample(decoy_candidates, target_count - 1)
            target_positions = [exit_pos] + chosen_decoys

            # Assign letters A, B, C, D...
            target_labels = [f"Target {chr(65 + i)}" for i in range(target_count)]
            # Shuffle label assignment deterministically to avoid Target A always being correct
            label_perm = attempt_rng.shuffle(list(range(target_count)))
            labeled_targets: dict[str, tuple[int, int]] = {
                target_labels[label_perm[i]]: target_positions[i]
                for i in range(target_count)
            }
            correct_answer = target_labels[label_perm[0]]

            # 4. Add distractor mirrors
            all_empty_cells = [
                (r, c)
                for r in range(rows)
                for c in range(cols)
                if (r, c) not in path_cells and (r, c) not in mirrors
            ]
            n_dist = min(params["distractors"], len(all_empty_cells))
            if n_dist > 0:
                dist_cells = attempt_rng.sample(all_empty_cells, n_dist)
                for dc_r, dc_c in dist_cells:
                    mirrors[(dc_r, dc_c)] = attempt_rng.choice(["/", "\\"])

            # 5. Final simulation verification with distractor mirrors in place
            v_check, refs_check, exit_check = self._simulate_ray(
                rows, cols, (start_r, start_c), start_dir, mirrors
            )
            if exit_check != exit_pos or len(refs_check) != desired_reflections:
                continue

            # Success! Render visual scene
            img = self._render_maze(
                rows=rows,
                cols=cols,
                mirrors=mirrors,
                emitter_pos=emitter_pos,
                start_dir=start_dir,
                labeled_targets=labeled_targets,
                correct_target=correct_answer,
            )

            options = [f"Target {chr(65 + i)}" for i in range(target_count)]
            instruction = "Which target will the laser beam hit?"

            private_meta = {
                "subtype": self.subtype,
                "difficulty": self.config.difficulty,
                "gridDimensions": [rows, cols],
                "reflectionCount": desired_reflections,
                "mirrorCount": len(mirrors),
                "emitter": {"perimeter": emitter_pos, "direction": start_dir},
                "solutionTarget": correct_answer,
                "targets": {lbl: list(pos) for lbl, pos in labeled_targets.items()},
            }

            return self.build_bundle(
                seed=seed,
                instruction=instruction,
                options=options,
                correct_answer=correct_answer,
                image=img,
                private_routing_metadata=private_meta,
            )

        # Fallback if attempt loop somehow exhausted
        raise RuntimeError(
            f"Failed to generate valid Laser Maze challenge for seed {seed}"
        )

    def _render_maze(
        self,
        rows: int,
        cols: int,
        mirrors: dict[tuple[int, int], str],
        emitter_pos: tuple[int, int],
        start_dir: tuple[int, int],
        labeled_targets: dict[str, tuple[int, int]],
        correct_target: str,
    ) -> Image.Image:
        """Render optical laser maze scene."""
        w = self.config.canvasWidth
        h = self.config.canvasHeight
        img = Image.new("RGB", (w, h), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Header banner
        draw_header_banner(
            draw=draw,
            width=w,
            height=h,
            badge_text="LEVEL 3A — LASER MAZE",
            instruction_text="Follow the laser beam reflections to find which sensor target it strikes.",
            accent_color=COLOR_LASER_RED,
        )

        # Calculate grid geometry centered in canvas
        avail_w = w - 240
        avail_h = h - 160
        cell_size = min(avail_w // (cols + 2), avail_h // (rows + 2), 72)
        grid_pixel_w = cols * cell_size
        grid_pixel_h = rows * cell_size
        offset_x = (w - grid_pixel_w) // 2
        offset_y = 68 + (avail_h - grid_pixel_h) // 2

        # Grid background panel
        pad = 12
        draw.rounded_rectangle(
            [
                offset_x - pad,
                offset_y - pad,
                offset_x + grid_pixel_w + pad,
                offset_y + grid_pixel_h + pad,
            ],
            radius=10,
            fill=COLOR_HEADER_BG,
            outline=COLOR_BORDER,
            width=2,
        )

        # Grid cells
        for r in range(rows):
            for c in range(cols):
                cx1 = offset_x + c * cell_size
                cy1 = offset_y + r * cell_size
                cx2 = cx1 + cell_size
                cy2 = cy1 + cell_size
                draw.rectangle([cx1, cy1, cx2, cy2], outline=(40, 53, 72), width=1)

        # Draw mirrors
        font_mirror = get_font(12, bold=True)
        for (r, c), m_type in mirrors.items():
            cx = offset_x + c * cell_size + cell_size // 2
            cy = offset_y + r * cell_size + cell_size // 2
            m_len = int(cell_size * 0.38)

            if m_type == "/":
                p1 = (cx - m_len, cy + m_len)
                p2 = (cx + m_len, cy - m_len)
                b1 = (cx - m_len - 2, cy + m_len + 2)
                b2 = (cx + m_len - 2, cy - m_len + 2)
            else:
                p1 = (cx - m_len, cy - m_len)
                p2 = (cx + m_len, cy + m_len)
                b1 = (cx - m_len + 2, cy - m_len + 2)
                b2 = (cx + m_len + 2, cy + m_len + 2)

            # Mirror backing plate
            draw.line([b1, b2], fill=(71, 85, 105), width=5)
            # High-reflectance mirror face
            draw.line([p1, p2], fill=(226, 232, 240), width=3)
            # Center mounting pivot
            draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=COLOR_ACCENT_CYAN)

        # Draw Targets on perimeter
        font_target = get_font(14, bold=True)
        for idx, (label, (tr, tc)) in enumerate(labeled_targets.items()):
            color = TARGET_COLORS[idx % len(TARGET_COLORS)]
            # Target position in pixels
            if tc == -1:  # Left perimeter
                tx = offset_x - cell_size - 14
                ty = offset_y + tr * cell_size + (cell_size - 36) // 2
            elif tc == cols:  # Right perimeter
                tx = offset_x + grid_pixel_w + 14
                ty = offset_y + tr * cell_size + (cell_size - 36) // 2
            elif tr == -1:  # Top perimeter
                tx = offset_x + tc * cell_size + (cell_size - 78) // 2
                ty = offset_y - 48
            else:  # Bottom perimeter
                tx = offset_x + tc * cell_size + (cell_size - 78) // 2
                ty = offset_y + grid_pixel_h + 14

            tw, th = 82, 34
            draw.rounded_rectangle(
                [tx, ty, tx + tw, ty + th],
                radius=6,
                fill=(15, 23, 42),
                outline=color,
                width=2,
            )
            # Sensor aperture circle
            draw.ellipse([tx + 8, ty + 10, tx + 22, ty + 24], fill=color)
            draw.text((tx + 28, ty + 8), label, fill=COLOR_TEXT_PRIMARY, font=font_target)

        # Draw Emitter
        er, ec = emitter_pos
        dr, dc = start_dir
        if ec == -1:  # Left side
            ex = offset_x - 110
            ey = offset_y + er * cell_size + (cell_size - 38) // 2
            beam_start = (ex + 100, ey + 19)
            beam_lead = (offset_x + 10, ey + 19)
        elif er == -1:  # Top side
            ex = offset_x + ec * cell_size + (cell_size - 100) // 2
            ey = offset_y - 50
            beam_start = (ex + 50, ey + 38)
            beam_lead = (ex + 50, offset_y + 10)
        else:
            ex = offset_x - 110
            ey = offset_y + er * cell_size
            beam_start = (ex + 100, ey + 19)
            beam_lead = (offset_x + 10, ey + 19)

        # Emitter body
        draw.rounded_rectangle(
            [ex, ey, ex + 98, ey + 38],
            radius=6,
            fill=(69, 10, 10),
            outline=COLOR_LASER_RED,
            width=2,
        )
        font_emitter = get_font(12, bold=True)
        draw.text((ex + 8, ey + 11), "LASER IN", fill=(254, 202, 202), font=font_emitter)

        # Initial beam spark entering first cell (indicates starting ray)
        draw.line([beam_start, beam_lead], fill=COLOR_LASER_GLOW, width=4)
        draw.line([beam_start, beam_lead], fill=COLOR_LASER_BEAM, width=2)
        # Small emitter nozzle
        draw.ellipse(
            [beam_start[0] - 5, beam_start[1] - 5, beam_start[0] + 5, beam_start[1] + 5],
            fill=COLOR_LASER_RED,
        )

        return img
