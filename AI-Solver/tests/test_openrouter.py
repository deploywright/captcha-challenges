import json
from unittest.mock import MagicMock

import pytest

from ai_solver.errors import ModelError
from ai_solver.solvers.level_1_vlm import Level1VLMSolver
from ai_solver.solvers.openrouter import OpenRouterVisionProvider


def test_openrouter_missing_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ModelError, match="OPENROUTER_API_KEY"):
        OpenRouterVisionProvider()


def test_openrouter_single_choice_inference(challenge, assets):
    challenge.variant = "routing-puzzle"
    challenge.type = "single-choice"
    challenge.ui.options = ["Server A", "Server B", "Server C"]
    challenge.assets = challenge.assets[:1]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": json.dumps({"selected_option_index": 2, "confidence": None})}}
        ],
        "usage": {"prompt_tokens": 150, "completion_tokens": 20},
    }
    mock_client.post.return_value = mock_response

    provider = OpenRouterVisionProvider(
        model_name="qwen/qwen3.8-27b:free",
        client=mock_client,
    )
    result = Level1VLMSolver(provider).solve(challenge, assets[:1])

    assert result.answer == 2
    assert result.confidence is None
    assert result.input_tokens == 150
    assert result.output_tokens == 20
    assert result.api_request_count == 1
    assert mock_client.post.called


def test_openrouter_retry_on_429(challenge, assets):
    challenge.variant = "routing-puzzle"
    challenge.type = "single-choice"
    challenge.ui.options = ["Option 1", "Option 2"]
    challenge.assets = challenge.assets[:1]

    mock_client = MagicMock()
    err_response = MagicMock()
    err_response.status_code = 429
    err_response.json.return_value = {"error": {"message": "Rate limited", "code": 429}}

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = {
        "choices": [
            {"message": {"content": json.dumps({"selected_option_index": 0, "confidence": None})}}
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10},
    }
    mock_client.post.side_effect = [err_response, ok_response]

    provider = OpenRouterVisionProvider(
        model_name="qwen/qwen3.8-27b:free",
        client=mock_client,
        max_retries=3,
        sleep=lambda _: None,
    )
    result = Level1VLMSolver(provider).solve(challenge, assets[:1])
    assert result.answer == 0
    assert mock_client.post.call_count == 2
