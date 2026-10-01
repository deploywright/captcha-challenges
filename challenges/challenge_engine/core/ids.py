"""Deterministic ID and neutral asset filename generation."""

from __future__ import annotations

import hashlib
import string

_BASE36_ALPHABET = string.digits + string.ascii_lowercase

LEVEL_PREFIX_MAP: dict[str, str] = {
    "level_1_street_grid": "lvl1",
    "level_2a_hard_street_grid": "lvl2a",
    "level_2b_checker_shadow": "lvl2b",
    "level_3a_tangled_cables": "lvl3a",
    "level_3b_degraded_vision": "lvl3b",
}


def _int_to_base36(value: int, length: int = 6) -> str:
    chars: list[str] = []
    base = len(_BASE36_ALPHABET)
    for _ in range(length):
        value, rem = divmod(value, base)
        chars.append(_BASE36_ALPHABET[rem])
    return "".join(reversed(chars))


def generate_challenge_id(
    level_key: str,
    seed: int,
    extra_discriminator: str = "",
    subtype: str | None = None,
) -> str:
    """Generate a deterministic, answer-agnostic challenge ID like 'lvl1_x82k91' or 'lvl3a_laser_x82k91'."""
    prefix = LEVEL_PREFIX_MAP.get(level_key, "chl")
    if subtype:
        if "laser" in subtype:
            prefix = f"{prefix}_laser"
        elif "conveyor" in subtype:
            prefix = f"{prefix}_conveyor"
        elif "pipe" in subtype:
            prefix = f"{prefix}_pipe"
        elif "cable" in subtype:
            prefix = f"{prefix}_cables"
        else:
            prefix = f"{prefix}_{subtype[:6]}"
    payload = f"{level_key}:{seed}:{subtype or ''}:{extra_discriminator}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    numeric = int.from_bytes(digest[:8], byteorder="big", signed=False)
    token = _int_to_base36(numeric, length=6)
    return f"{prefix}_{token}"


def index_to_alpha_label(index: int) -> str:
    """Convert 0-based index to neutral lowercase label ('a', 'b', ..., 'z', 'aa', ...)."""
    if index < 0:
        raise ValueError(f"Index must be non-negative, got {index}")
    chars: list[str] = []
    n = index
    while True:
        n, rem = divmod(n, 26)
        chars.append(string.ascii_lowercase[rem])
        if n == 0:
            break
        n -= 1
    return "".join(reversed(chars))


def asset_relpath_for_index(index: int, ext: str = "webp") -> str:
    """Return neutral relative asset path such as 'assets/a.webp'."""
    ext = ext.lstrip(".")
    label = index_to_alpha_label(index)
    return f"assets/{label}.{ext}"
