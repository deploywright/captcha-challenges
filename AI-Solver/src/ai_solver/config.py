"""Non-secret configuration; credentials are read only by the provider."""

import math
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

DEFAULT_MODELS = {"gemini": "gemini-3.5-flash-lite", "openai": "gpt-4.1-mini-2025-04-14"}


def normalize_base_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
        or parts.path.rstrip("/")
    ):
        raise ValueError("CAPTCHA_BASE_URL must be an HTTP(S) origin without credentials or path")
    try:
        _ = parts.port
    except ValueError:
        raise ValueError("Invalid benchmark port") from None
    return urlunsplit((parts.scheme, parts.netloc.lower(), "", "", ""))


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    base_url: str
    variant: Literal["street-grid"] = "street-grid"
    solver: Literal["vlm", "random"] = "vlm"
    provider: Literal["gemini", "openai"] = "gemini"
    model: str = Field(min_length=1)
    output_dir: Path = Path("results")
    limit: int | None = Field(default=None, gt=0)
    seed: int = 42
    timeout: float = Field(default=60, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    selection_probability: float = Field(default=0.33, ge=0, le=1)
    dry_run: bool = False
    input_price_per_million: float | None = Field(default=None, ge=0)
    output_price_per_million: float | None = Field(default=None, ge=0)

    _base_url = field_validator("base_url")(normalize_base_url)

    @model_validator(mode="before")
    @classmethod
    def provider_default_model(cls, values):
        if isinstance(values, dict):
            values = values.copy()
            provider = values.get("provider", "gemini")
            if "model" not in values and provider in DEFAULT_MODELS:
                values["model"] = DEFAULT_MODELS[provider]
        return values

    @field_validator("timeout", "selection_probability")
    @classmethod
    def finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Configuration numbers must be finite")
        return value


def load_config(overrides: dict, config_path: Path | None = None) -> RunConfig:
    values: dict = {}
    if config_path is not None:
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            raise ValueError("Unable to read YAML configuration") from None
        if not isinstance(data, dict):
            raise ValueError("Configuration must be a YAML mapping")
        values.update(data)
    if os.getenv("CAPTCHA_BASE_URL"):
        values["base_url"] = os.environ["CAPTCHA_BASE_URL"]
    if os.getenv("CAPTCHA_PROVIDER"):
        values["provider"] = os.environ["CAPTCHA_PROVIDER"]
    provider = overrides.get("provider") or values.get("provider", "gemini")
    model_variable = "GEMINI_MODEL" if provider == "gemini" else "OPENAI_MODEL"
    if os.getenv(model_variable):
        values["model"] = os.environ[model_variable]
    values.update({key: value for key, value in overrides.items() if value is not None})
    try:
        return RunConfig.model_validate(values)
    except ValidationError as exc:
        # Do not echo arbitrary input values (e.g. an accidentally supplied credential).
        fields = ", ".join(".".join(map(str, error["loc"])) for error in exc.errors())
        raise ValueError(f"Invalid configuration fields: {fields}") from None
