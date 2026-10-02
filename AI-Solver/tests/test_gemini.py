import json
from types import SimpleNamespace

import httpx
import pytest

from ai_solver.config import RunConfig, load_config
from ai_solver.errors import ModelError, ModelResponseError
from ai_solver.solvers.gemini import GeminiVisionProvider
from ai_solver.solvers.level_1_vlm import Level1VLMSolver

genai = pytest.importorskip("google.genai")
from google.genai import errors, types  # noqa: E402


def response(text='{"selected_indices":[0,8],"confidence":null}', *, finish="STOP"):
    return SimpleNamespace(
        text=text,
        candidates=[SimpleNamespace(finish_reason=finish)],
        usage_metadata=SimpleNamespace(
            prompt_token_count=100, candidates_token_count=10, total_token_count=130
        ),
    )


def provider(generate, retries=2):
    return GeminiVisionProvider(
        "gemini-test",
        max_retries=retries,
        sleep=lambda _: None,
        client=SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )


def test_gemini_one_request_all_tiles(challenge, assets):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return response()

    result = Level1VLMSolver(provider(generate)).solve(challenge, assets)
    assert result.answer == [0, 8] and result.confidence is None
    assert result.api_request_count == 1
    assert result.input_tokens == 100 and result.output_tokens == 30
    request = calls[0]
    parts = request["contents"][0].parts
    assert request["model"] == "gemini-test"
    assert challenge.instruction in parts[0].text
    assert [p.text for p in parts if p.text and p.text.startswith("Tile ")] == [
        f"Tile {i}" for i in range(9)
    ]
    assert sum(p.inline_data is not None for p in parts) == 9
    assert all(p.inline_data.data == assets[0] for p in parts if p.inline_data)
    config = request["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["properties"]["confidence"] == {"type": "null"}
    assert config.thinking_config.thinking_level == types.ThinkingLevel.MINIMAL
    assert getattr(config, "candidate_count", None) is None
    assert config.automatic_function_calling.disable is True
    assert config.tools is None and config.cached_content is None


@pytest.mark.parametrize(
    "status,expected",
    [(429, 3), (502, 3), (503, 3), (504, 3), (400, 1), (401, 1), (403, 1), (404, 1), (500, 1)],
)
def test_gemini_retry_policy(status, expected, assets):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        raise errors.APIError(
            status,
            {
                "error": {
                    "code": status,
                    "message": "never-log-this-secret",
                    "status": "RESOURCE_EXHAUSTED",
                }
            },
        )

    with pytest.raises(ModelError) as error:
        provider(generate).infer("Select buses", assets, recovery=False)
    assert len(calls) == error.value.api_request_count == expected
    assert error.value.status_code == status
    assert "secret" not in str(error.value)


def test_gemini_transport_retry(assets):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        raise httpx.ConnectError("transport test")

    with pytest.raises(ModelError) as error:
        provider(generate, retries=1).infer("Select buses", assets, recovery=False)
    assert len(calls) == error.value.api_request_count == 2


def test_gemini_recovery_once(challenge, assets):
    responses = iter([response("bad"), response()])
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return next(responses)

    result = Level1VLMSolver(provider(generate)).solve(challenge, assets)
    assert result.api_request_count == 2 and result.parsing_status == "recovered"
    assert "single output-format recovery" in calls[1]["contents"][0].parts[0].text


def test_gemini_truncated_response_cannot_be_submitted(challenge, assets):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return response(finish="MAX_TOKENS")

    with pytest.raises(ModelResponseError) as error:
        Level1VLMSolver(provider(generate)).solve(challenge, assets)
    assert len(calls) == error.value.api_request_count == 2


def test_gemini_sdk_wire_contract(challenge, assets):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.method == "POST" and request.url.path.endswith(":generateContent")
        body = json.loads(request.content)
        assert len(body["contents"][0]["parts"]) == 19
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert "responseJsonSchema" in body["generationConfig"]
        assert "tools" not in body
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"role": "model", "parts": [{"text": response().text}]},
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 100,
                    "candidatesTokenCount": 10,
                    "thoughtsTokenCount": 20,
                    "totalTokenCount": 130,
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        sdk = genai.Client(
            api_key="fake-test-key",
            vertexai=False,
            http_options=types.HttpOptions(
                httpx_client=http, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
        result = Level1VLMSolver(GeminiVisionProvider("gemini-test", client=sdk)).solve(
            challenge, assets
        )
    assert result.answer == [0, 8] and result.output_tokens == 30
    assert len(requests) == result.api_request_count == 1


def test_provider_specific_config_defaults(monkeypatch):
    monkeypatch.delenv("CAPTCHA_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "openai-only-model")
    assert RunConfig(base_url="https://example.com").model == "gemini-3.5-flash-lite"
    assert RunConfig(base_url="https://example.com", provider="openai").model.startswith("gpt-")
    assert load_config({"base_url": "https://example.com"}).model == "gemini-3.5-flash-lite"
    assert load_config({"base_url": "https://example.com", "provider": "openai"}).model == (
        "openai-only-model"
    )
    monkeypatch.setenv("GEMINI_MODEL", "custom-gemini")
    assert load_config({"base_url": "https://example.com"}).model == "custom-gemini"
    assert load_config({"base_url": "https://example.com", "model": "cli-model"}).model == (
        "cli-model"
    )


def test_missing_gemini_key_is_safe(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ModelError, match="GEMINI_API_KEY"):
        GeminiVisionProvider("gemini-test")


def test_gemini_config_thinking_minimal_and_no_candidates(challenge, assets):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return response()

    Level1VLMSolver(provider(generate)).solve(challenge, assets)
    assert len(calls) == 1
    config = calls[0]["config"]
    assert config.thinking_config.thinking_level == types.ThinkingLevel.MINIMAL
    assert getattr(config, "candidate_count", None) is None
    assert config.automatic_function_calling.disable is True
    assert config.tools is None
