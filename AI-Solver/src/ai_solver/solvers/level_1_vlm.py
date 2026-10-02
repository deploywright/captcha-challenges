"""Zero-shot tile selection and one OpenAI Responses API provider adapter."""

import base64
import os
import time
from typing import Any

from pydantic import ValidationError

from ..client import RETRY_STATUSES
from ..contracts import (
    PublicChallenge,
    SolverPrediction,
    VLMSelection,
    validate_indices,
    validate_street_grid,
)
from ..errors import ModelError, ModelResponseError
from .base import ProviderResponse, VisionProvider

_NONRETRY_PROVIDER_CODES = {
    "insufficient_quota",
    "billing_hard_limit_reached",
    "credit_balance_exhausted",
    "organization_spend_limit_exceeded",
    "project_spend_limit_exceeded",
    "organization_usage_limit_exceeded",
}
_SAFE_PROVIDER_CODES = _NONRETRY_PROVIDER_CODES | {
    "rate_limit_exceeded",
    "slow_down",
    "server_is_overloaded",
    "model_not_found",
    "invalid_api_key",
    "unsupported_country_region_territory",
}


def tile_prompt(instruction: str, count: int, *, recovery: bool = False) -> str:
    prompt = f"""You are solving an image-selection CAPTCHA benchmark.
Task:
{instruction}

You are given {count} image tiles. Tiles are numbered from 0 to {count - 1}.
Inspect each image independently.
Return the zero-based indices of every tile that visibly contains the requested target.
- Do not assume every tile contains the target.
- Do not select a tile based only on context.
- Select a tile only if the target is visually present.
- Include partially visible targets when they are genuinely identifiable.
- Return zero-based indices only, without duplicates.
- Return JSON only with selected_indices and confidence.
- Use confidence: null; no calibrated selection confidence is provided by this API.
"""
    if recovery:
        prompt += (
            "This is the single output-format recovery request. Return an integer array, "
            f"all indices in [0, {count - 1}], no duplicates, and confidence: null."
        )
    return prompt


def image_data_url(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith((b"GIF87a", b"GIF89a")):
        mime = "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ModelError("Public tile is not a supported image format")
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


class OpenAIVisionProvider:
    def __init__(
        self,
        model_name: str,
        *,
        timeout: float = 60,
        max_retries: int = 2,
        client: Any = None,
        sleep=time.sleep,
    ):
        self.model_name = model_name
        self.max_retries = max_retries
        self._sleep = sleep
        self._owns_client = client is None
        if client is None:
            if not os.getenv("OPENAI_API_KEY"):
                raise ModelError("Set OPENAI_API_KEY in the environment or local .env")
            try:
                from openai import OpenAI
            except ImportError:
                raise ModelError(
                    "Install the provider extra: pip install -e '.[openai]' "
                ) from None
            # Disable SDK retries so only our documented transport/status policy applies.
            client = OpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                timeout=timeout,
                max_retries=0,
            )
        self._client = client

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def infer(self, instruction: str, assets: list[bytes], *, recovery: bool) -> ProviderResponse:
        from openai import APIConnectionError, APIStatusError

        content = [
            {"type": "input_text", "text": tile_prompt(instruction, len(assets), recovery=recovery)}
        ]
        for index, asset in enumerate(assets):
            content.append({"type": "input_text", "text": f"Tile {index}"})
            content.append(
                {"type": "input_image", "image_url": image_data_url(asset), "detail": "high"}
            )
        schema = VLMSelection.model_json_schema()
        # Calibrated confidence is not available. Enforce null at the provider boundary.
        schema["properties"]["confidence"] = {"type": "null"}
        calls = 0
        for attempt in range(self.max_retries + 1):
            calls += 1
            try:
                response = self._client.responses.create(
                    model=self.model_name,
                    input=[{"role": "user", "content": content}],
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "tile_selection",
                            "strict": True,
                            "schema": schema,
                        }
                    },
                    store=False,
                    max_output_tokens=1024,
                )
            except APIConnectionError:
                failure = ModelError("Model provider transport failed")
                retryable = True
            except APIStatusError as exc:
                failure = ModelError("Model provider HTTP failure", status_code=exc.status_code)
                # Only known machine codes are safe diagnostics; never persist error bodies.
                code = getattr(exc, "code", None)
                if code in _SAFE_PROVIDER_CODES:
                    failure.provider_error_code = code
                retryable = exc.status_code in RETRY_STATUSES
                if code in _NONRETRY_PROVIDER_CODES:
                    retryable = False
            else:
                usage = getattr(response, "usage", None)
                # Refusals/truncation become invalid output, eligible for one format recovery.
                return ProviderResponse(
                    text=(response.output_text or "")
                    if getattr(response, "status", "completed") == "completed"
                    else "",
                    input_tokens=getattr(usage, "input_tokens", None),
                    output_tokens=getattr(usage, "output_tokens", None),
                    api_request_count=calls,
                )
            if not retryable or attempt == self.max_retries:
                failure.api_request_count = calls
                raise failure from None
            self._sleep(min(0.5 * 2**attempt, 8))
        raise AssertionError("Unreachable provider retry state")


def _sum_known(previous: int | None, current: int | None) -> int | None:
    if current is None:
        return previous
    return (previous or 0) + current


class Level1VLMSolver:
    name = "level-1-vlm-zero-shot"

    def __init__(self, provider: VisionProvider):
        self.provider = provider
        self.model_name = provider.model_name

    def solve(self, challenge: PublicChallenge, assets: list[bytes]) -> SolverPrediction:
        start = time.perf_counter()
        validate_street_grid(challenge, assets)
        calls = 0
        input_tokens = output_tokens = None
        usage_complete = True
        for recovery in (False, True):
            try:
                response = self.provider.infer(challenge.instruction, assets, recovery=recovery)
            except ModelError as exc:
                exc.api_request_count += calls
                exc.input_tokens = _sum_known(input_tokens, exc.input_tokens)
                exc.output_tokens = _sum_known(output_tokens, exc.output_tokens)
                exc.inference_time_ms = (time.perf_counter() - start) * 1000
                raise
            calls += response.api_request_count
            usage_complete = (
                usage_complete
                and response.api_request_count == 1
                and response.input_tokens is not None
                and response.output_tokens is not None
            )
            input_tokens = _sum_known(input_tokens, response.input_tokens)
            output_tokens = _sum_known(output_tokens, response.output_tokens)
            try:
                selection = VLMSelection.model_validate_json(response.text)
                indices = validate_indices(selection.selected_indices, len(assets))
            except (ValidationError, ModelResponseError):
                if not recovery:
                    continue
                failure = ModelResponseError("Invalid model selection after one format recovery")
                failure.api_request_count = calls
                failure.input_tokens = input_tokens
                failure.output_tokens = output_tokens
                failure.inference_time_ms = (time.perf_counter() - start) * 1000
                raise failure from None
            return SolverPrediction(
                challenge_id=challenge.id,
                answer=indices,
                confidence=selection.confidence,
                solver_name=self.name,
                model_name=self.model_name,
                inference_time_ms=(time.perf_counter() - start) * 1000,
                raw_response=response.text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                api_request_count=calls,
                usage_complete=usage_complete,
                parsing_status="recovered" if recovery else "valid",
            )
        raise AssertionError("Unreachable solver recovery state")
