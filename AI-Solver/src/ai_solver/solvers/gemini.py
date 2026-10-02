"""Google GenAI adapter; only public instructions and inline image tiles are sent."""

import os
import time
from typing import Any

import httpx

from ..client import RETRY_STATUSES
from ..contracts import VLMSelection, VLMSingleChoice
from ..errors import ModelError
from .base import ProviderResponse
from .level_1_vlm import image_mime_type, single_choice_prompt, tile_prompt


class GeminiVisionProvider:
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
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ModelError("Set GEMINI_API_KEY in the environment or local .env")
            try:
                from google import genai
                from google.genai import types
            except ImportError:
                raise ModelError("Install the Gemini extra: pip install -e '.[gemini]'") from None
            client = genai.Client(
                api_key=api_key,
                vertexai=False,
                http_options=types.HttpOptions(
                    timeout=int(timeout * 1000),
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        self._client = client

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def infer(
        self,
        instruction: str,
        assets: list[bytes],
        *,
        recovery: bool = False,
        options: list[str] | None = None,
    ) -> ProviderResponse:
        from google.genai import errors, types

        if options is not None:
            parts = [
                types.Part.from_text(
                    text=single_choice_prompt(instruction, options, recovery=recovery)
                )
            ]
            for asset in assets:
                parts.append(types.Part.from_bytes(data=asset, mime_type=image_mime_type(asset)))
            schema = VLMSingleChoice.model_json_schema()
            schema["properties"]["confidence"] = {"type": "null"}
        else:
            parts = [
                types.Part.from_text(text=tile_prompt(instruction, len(assets), recovery=recovery))
            ]
            for index, asset in enumerate(assets):
                parts.append(types.Part.from_text(text=f"Tile {index}"))
                parts.append(types.Part.from_bytes(data=asset, mime_type=image_mime_type(asset)))
            schema = VLMSelection.model_json_schema()
            schema["properties"]["confidence"] = {"type": "null"}

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        calls = 0
        for attempt in range(self.max_retries + 1):
            calls += 1
            status_code = None
            status = None
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=[types.Content(role="user", parts=parts)],
                    config=config,
                )
            except httpx.TransportError:
                failure = ModelError("Gemini provider transport failed")
                retryable = True
            except errors.APIError as exc:
                status_code = getattr(exc, "code", None)
                failure = ModelError("Gemini provider HTTP failure", status_code=status_code)
                # Status enum only; never echo the message, key, or error response body.
                status = getattr(exc, "status", None)
                if status in {
                    "RESOURCE_EXHAUSTED",
                    "UNAVAILABLE",
                    "INVALID_ARGUMENT",
                    "PERMISSION_DENIED",
                    "UNAUTHENTICATED",
                    "NOT_FOUND",
                    "INTERNAL",
                    "DEADLINE_EXCEEDED",
                }:
                    failure.provider_error_code = status
                retryable = status_code in RETRY_STATUSES
            else:
                usage = getattr(response, "usage_metadata", None)
                input_tokens = getattr(usage, "prompt_token_count", None)
                total_tokens = getattr(usage, "total_token_count", None)
                output_tokens = getattr(usage, "candidates_token_count", None)
                # Total minus prompt includes reported reasoning tokens, with no tools enabled.
                if total_tokens is not None and input_tokens is not None:
                    output_tokens = total_tokens - input_tokens
                candidates = getattr(response, "candidates", None) or []
                complete = len(candidates) == 1 and candidates[0].finish_reason == "STOP"
                return ProviderResponse(
                    text=(response.text or "") if complete else "",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    api_request_count=calls,
                )
            if not retryable or attempt == self.max_retries:
                failure.api_request_count = calls
                raise failure from None
            if status_code == 429 or status == "RESOURCE_EXHAUSTED":
                self._sleep(5.0 * (attempt + 1))
            else:
                self._sleep(min(0.5 * 2**attempt, 8))
        raise AssertionError("Unreachable Gemini retry state")
