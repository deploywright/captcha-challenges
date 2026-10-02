"""Public wire contracts and prediction/result contracts; no evaluation secrets."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from .errors import ChallengeContractError, ModelResponseError
from .security import assert_public_json

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]+$", min_length=1)]
Milliseconds = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Answer = list[StrictInt] | str | StrictInt


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class ChallengeUI(PublicModel):
    rows: Annotated[int, Field(gt=0)] | None = None
    columns: Annotated[int, Field(gt=0)] | None = None
    selectionMode: str | None = None
    options: list[str] | None = None


class PublicChallenge(PublicModel):
    id: Identifier
    level: int
    variant: str
    subtype: str | None = None
    difficulty: str | None = None
    type: str
    instruction: Annotated[str, Field(min_length=1)]
    seed: int
    assets: Annotated[list[str], Field(min_length=1)]
    ui: ChallengeUI


class CatalogEntry(PublicModel):
    id: Identifier
    level: int
    variant: str
    challengeUrl: str


class SubmissionResponse(PublicModel):
    correct: bool
    challengeId: Identifier
    variant: str
    solveTimeMs: Milliseconds | None = None


class SolverPrediction(BaseModel):
    model_config = ConfigDict(strict=True)
    challenge_id: Identifier
    answer: Answer
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    solver_name: str
    model_name: str
    inference_time_ms: Milliseconds
    raw_response: str | None = None
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None
    api_request_count: Annotated[int, Field(ge=0)] = 0
    usage_complete: bool = True
    parsing_status: str = "valid"


class VLMSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    selected_indices: list[StrictInt]
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None


class ChallengeResult(BaseModel):
    challenge_id: str
    variant: str
    level: int
    solver: str
    model: str
    prediction: Answer | None = None
    correct: bool | None = None
    confidence: float | None = None
    asset_count: int = 0
    predicted_positive_count: int | None = None
    asset_download_time_ms: Milliseconds | None = None
    inference_time_ms: Milliseconds | None = None
    submission_time_ms: Milliseconds | None = None
    total_time_ms: Milliseconds = 0.0
    submission_status: int | None = None
    model_status: int | None = None
    provider_error_code: str | None = None
    error: str | None = None
    error_type: str | None = None
    status: str = "pending"
    parsing_status: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    api_request_count: int = 0
    usage_complete: bool = True


def parse_challenge(data: Any) -> PublicChallenge:
    assert_public_json(data)
    try:
        return PublicChallenge.model_validate(data)
    except ValidationError:
        raise ChallengeContractError("Invalid public challenge contract") from None


def parse_catalog(data: Any) -> list[CatalogEntry]:
    assert_public_json(data)
    if not isinstance(data, list):
        raise ChallengeContractError("Catalog must be a JSON array")
    try:
        entries = [CatalogEntry.model_validate(item) for item in data]
    except ValidationError:
        raise ChallengeContractError("Invalid public catalog entry") from None
    if len({entry.id for entry in entries}) != len(entries):
        raise ChallengeContractError("Duplicate challenge IDs in catalog")
    return entries


def validate_indices(indices: Any, asset_count: int) -> list[int]:
    if not isinstance(indices, list) or any(type(item) is not int for item in indices):
        raise ModelResponseError("Selection must be a list of integer zero-based indices")
    if any(item < 0 or item >= asset_count for item in indices):
        raise ModelResponseError("Selection index is outside the public asset range")
    if len(set(indices)) != len(indices):
        raise ModelResponseError("Selection contains duplicate indices")
    return sorted(set(indices))


def validate_street_grid(challenge: PublicChallenge, assets: list[bytes]) -> None:
    if challenge.variant != "street-grid" or challenge.type != "image-selection":
        raise ChallengeContractError("v0.1 supports street-grid image-selection only")
    if len(assets) != len(challenge.assets) or not assets or any(not x for x in assets):
        raise ChallengeContractError("Asset count or content does not match public challenge")
    if challenge.ui.rows and challenge.ui.columns:
        if challenge.ui.rows * challenge.ui.columns != len(assets):
            raise ChallengeContractError("Public grid dimensions do not match asset count")
