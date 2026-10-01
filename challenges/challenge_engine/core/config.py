"""Configuration loading and validation utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from challenge_engine.core.schemas import (
    LEVEL_1_KEY,
    LEVEL_2A_KEY,
    LEVEL_2B_KEY,
    LEVEL_3A_KEY,
    LEVEL_3B_KEY,
    Level1Config,
    Level2AConfig,
    Level2BConfig,
    Level3AConfig,
    Level3BConfig,
    normalize_level_key,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG_FILES: dict[str, Path] = {
    LEVEL_1_KEY: PROJECT_ROOT / "configs" / "level-1.json",
    LEVEL_2A_KEY: PROJECT_ROOT / "configs" / "level-2a.json",
    LEVEL_2B_KEY: PROJECT_ROOT / "configs" / "level-2b.json",
    LEVEL_3A_KEY: PROJECT_ROOT / "configs" / "level-3a.json",
    LEVEL_3B_KEY: PROJECT_ROOT / "configs" / "level-3b.json",
}

CONFIG_MODEL_MAP: dict[str, type[BaseModel]] = {
    LEVEL_1_KEY: Level1Config,
    LEVEL_2A_KEY: Level2AConfig,
    LEVEL_2B_KEY: Level2BConfig,
    LEVEL_3A_KEY: Level3AConfig,
    LEVEL_3B_KEY: Level3BConfig,
}

ConfigT = TypeVar("ConfigT", bound=BaseModel)


def load_level_config(
    level: str,
    config_path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> BaseModel:
    """Load and validate configuration for the specified level."""
    level_key = normalize_level_key(level)
    model_cls = CONFIG_MODEL_MAP[level_key]
    resolved_path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_FILES[level_key]

    raw_data: dict[str, Any] = {}
    if resolved_path.exists():
        with resolved_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    elif config_path is not None:
        raise FileNotFoundError(f"Configuration file not found: {resolved_path}")

    if overrides:
        for k, v in overrides.items():
            if v is not None:
                raw_data[k] = v

    return model_cls.model_validate(raw_data)
