"""Base abstractions, shared typography, rendering utilities, and bundle builders for Level 3A Routing Puzzles."""

from __future__ import annotations

import abc
from typing import Any
from PIL import Image, ImageDraw, ImageFont

from challenge_engine.core.exporter import ChallengeBundle
from challenge_engine.core.ids import asset_relpath_for_index, generate_challenge_id
from challenge_engine.core.schemas import (
    LEVEL_3A_KEY,
    Level3AConfig,
    PrivateAnswer,
    PublicChallenge,
    PublicUIConfig,
)

# Shared modern dark palette (Tailwind Slate-inspired)
COLOR_BG = (15, 23, 42)          # Slate-900
COLOR_HEADER_BG = (30, 41, 59)   # Slate-800
COLOR_CARD_BG = (30, 41, 59)     # Slate-800
COLOR_BORDER = (51, 65, 85)      # Slate-700
COLOR_BORDER_LIGHT = (71, 85, 105) # Slate-600
COLOR_TEXT_PRIMARY = (248, 250, 252) # Slate-50
COLOR_TEXT_MUTED = (148, 163, 184)   # Slate-400
COLOR_TEXT_DIM = (100, 116, 139)     # Slate-500

COLOR_LASER_RED = (239, 68, 68)     # Red-500
COLOR_LASER_GLOW = (252, 165, 165)  # Red-300
COLOR_LASER_BEAM = (255, 75, 75)

COLOR_ACCENT_CYAN = (6, 182, 212)    # Cyan-500
COLOR_ACCENT_GREEN = (34, 197, 94)   # Green-500
COLOR_ACCENT_AMBER = (245, 158, 11)  # Amber-500
COLOR_ACCENT_PURPLE = (168, 85, 247) # Purple-500
COLOR_ACCENT_BLUE = (59, 130, 246)   # Blue-500


def get_font(size: int = 16, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a clean scalable sans-serif font across platforms, falling back gracefully."""
    candidates = (
        ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
        if bold
        else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_header_banner(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    badge_text: str,
    instruction_text: str,
    accent_color: tuple[int, int, int] = COLOR_ACCENT_CYAN,
) -> None:
    """Render a clean top banner with challenge family badge and clear instruction."""
    header_h = 56
    draw.rectangle([0, 0, width, header_h], fill=COLOR_HEADER_BG)
    draw.line([(0, header_h), (width, header_h)], fill=COLOR_BORDER, width=2)

    font_badge = get_font(13, bold=True)
    font_instr = get_font(15, bold=False)

    # Subtype badge pill
    badge_x = 24
    badge_y = 14
    badge_bbox = font_badge.getbbox(badge_text)
    badge_w = (badge_bbox[2] - badge_bbox[0]) + 18
    badge_h = 28
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=6,
        fill=(15, 23, 42),
        outline=accent_color,
        width=2,
    )
    draw.text(
        (badge_x + 9, badge_y + 6),
        badge_text,
        fill=accent_color,
        font=font_badge,
    )

    # Instruction text
    instr_x = badge_x + badge_w + 16
    draw.text(
        (instr_x, badge_y + 5),
        instruction_text,
        fill=COLOR_TEXT_PRIMARY,
        font=font_instr,
    )


class RoutingPuzzleSubtypeGenerator(abc.ABC):
    """Abstract base generator for all Level 3A routing puzzle subtypes."""

    subtype: str
    level_key: str = LEVEL_3A_KEY

    def __init__(self, config: Level3AConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def generate_one(self, seed: int) -> ChallengeBundle:
        """Generate a single deterministic challenge bundle for this subtype."""
        ...

    def build_bundle(
        self,
        seed: int,
        instruction: str,
        options: list[str],
        correct_answer: str,
        image: Image.Image,
        private_routing_metadata: dict[str, Any],
    ) -> ChallengeBundle:
        """Construct the universal ChallengeBundle with strict zero-leakage guarantee."""
        challenge_id = generate_challenge_id(self.level_key, seed, subtype=self.subtype)
        rel_asset = asset_relpath_for_index(0, ext="webp")

        if correct_answer not in options:
            raise ValueError(
                f"Correct answer '{correct_answer}' must be present in options: {options}"
            )
        correct_index = options.index(correct_answer)

        public_challenge = PublicChallenge(
            schemaVersion=1,
            id=challenge_id,
            level=3,
            variant="routing-puzzle",
            subtype=self.subtype,
            difficulty=self.config.difficulty,
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
            datasetSource=f"procedural-{self.subtype}",
            subtype=self.subtype,
            correctSelection=[correct_index],
            answer=correct_answer,
            routing={**private_routing_metadata, "generationConfig": self.config.model_dump(mode="json")},
        )

        return ChallengeBundle(
            public_challenge=public_challenge,
            private_answer=private_answer,
            assets={rel_asset: image},
            lossless_webp=True,
        )
