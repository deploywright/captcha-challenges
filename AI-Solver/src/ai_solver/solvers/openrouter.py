"""OpenRouter Vision Provider adapter."""

import os
import time
from typing import Any

import httpx

from ..client import RETRY_STATUSES
from ..errors import ModelError
from .base import ProviderResponse
from .level_1_vlm import image_data_url, single_choice_prompt, tile_prompt

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterVisionProvider:
    def __init__(
        self,
        model_name: str = "qwen/qwen3.8-27b:free",
        *,
        timeout: float = 60.0,
        max_retries: int = 3,
        client: Any = None,
        sleep=time.sleep,
        api_key: str | None = None,
    ):
        self.model_name = model_name
        self.max_retries = max_retries
        self._sleep = sleep
        self._owns_client = client is None

        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key and client is None:
            raise ModelError("Set OPENROUTER_API_KEY in the environment or local .env")
        self._api_key = key

        if client is None:
            self._client = httpx.Client(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/deploywright/captcha-challenges",
                    "X-Title": "CAPTCHA Benchmark",
                },
            )
        else:
            self._client = client

    def close(self) -> None:
        if self._owns_client and hasattr(self._client, "close"):
            self._client.close()

    def infer(
        self,
        instruction: str,
        assets: list[bytes],
        *,
        recovery: bool = False,
        options: list[str] | None = None,
    ) -> ProviderResponse:
        if options is not None:
            prompt = single_choice_prompt(instruction, options, recovery=recovery)
            content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            for asset in assets:
                content.append({"type": "image_url", "image_url": {"url": image_data_url(asset)}})
        else:
            prompt = tile_prompt(instruction, len(assets), recovery=recovery)
            content = [{"type": "text", "text": prompt}]
            for index, asset in enumerate(assets):
                content.append({"type": "text", "text": f"Tile {index}"})
                content.append({"type": "image_url", "image_url": {"url": image_data_url(asset)}})

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        calls = 0
        for attempt in range(self.max_retries + 1):
            calls += 1
            retryable = False
            status_code = None
            try:
                if hasattr(self._client, "post"):
                    resp = self._client.post(OPENROUTER_API_URL, json=payload)
                else:
                    raise ModelError("Invalid client object for OpenRouterVisionProvider")

                status_code = resp.status_code
                if status_code != 200:
                    data = {}
                    try:
                        data = resp.json()
                    except Exception:
                        pass
                    err_info = data.get("error") if isinstance(data, dict) else {}
                    err_code = err_info.get("code") if isinstance(err_info, dict) else None
                    err_msg = err_info.get("message", "") if isinstance(err_info, dict) else ""

                    failure = ModelError(
                        f"OpenRouter provider HTTP failure: {status_code}",
                        status_code=status_code,
                    )
                    if err_code:
                        failure.provider_error_code = str(err_code)

                    retryable = status_code in RETRY_STATUSES or status_code >= 500
                    if (
                        status_code in {401, 402, 403, 404}
                        or "quota" in str(err_msg).lower()
                        or "credits" in str(err_msg).lower()
                    ):
                        retryable = False

                    if not retryable or attempt == self.max_retries:
                        failure.api_request_count = calls
                        raise failure

                    delay = (
                        min(4.0 * (attempt + 1), 20.0)
                        if status_code == 429
                        else min(0.5 * (2**attempt), 8.0)
                    )
                    self._sleep(delay)
                    continue

                res_json = resp.json()
                choices = res_json.get("choices", [])
                if not choices:
                    raw_text = ""
                else:
                    raw_text = choices[0].get("message", {}).get("content", "") or ""

                text = raw_text.strip()
                if text.startswith("```"):
                    lines = text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    text = "\n".join(lines).strip()

                usage = res_json.get("usage", {})
                input_tokens = usage.get("prompt_tokens")
                output_tokens = usage.get("completion_tokens")

                return ProviderResponse(
                    text=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    api_request_count=calls,
                )

            except httpx.TransportError:
                failure = ModelError("OpenRouter provider transport failed")
                if attempt == self.max_retries:
                    failure.api_request_count = calls
                    raise failure from None
                self._sleep(min(0.5 * (2**attempt), 8.0))
            except ModelError:
                raise
            except Exception as exc:
                failure = ModelError(f"OpenRouter unexpected error: {exc}")
                failure.api_request_count = calls
                raise failure from None

        raise AssertionError("Unreachable provider retry state")
