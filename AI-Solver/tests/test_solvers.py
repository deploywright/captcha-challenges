import json
from types import SimpleNamespace

import httpx
import pytest

from ai_solver.errors import ModelError, ModelResponseError
from ai_solver.solvers.base import ProviderResponse
from ai_solver.solvers.level_1_vlm import Level1VLMSolver, OpenAIVisionProvider
from ai_solver.solvers.random_baseline import RandomBaseline


class FakeProvider:
    model_name = "fake-vision"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def infer(self, instruction, assets, *, recovery):
        self.calls.append((instruction, len(assets), recovery))
        return ProviderResponse(next(self.responses), input_tokens=100, output_tokens=10)


def test_single_inference_all_tiles(challenge, assets):
    provider = FakeProvider(['{"selected_indices":[8,0,3],"confidence":null}'])
    prediction = Level1VLMSolver(provider).solve(challenge, assets)
    assert prediction.answer == [0, 3, 8]
    assert prediction.confidence is None
    assert provider.calls == [(challenge.instruction, 9, False)]
    assert prediction.api_request_count == 1
    assert prediction.input_tokens == 100
    assert prediction.inference_time_ms >= 0


@pytest.mark.parametrize(
    "bad",
    [
        "invalid JSON",
        '{"selected_indices":[9],"confidence":null}',
        '{"selected_indices":[1,1],"confidence":null}',
        '{"selected_indices":[true],"confidence":null}',
        '{"selected_indices":[1.0],"confidence":null}',
        '{"selected_indices":["1"],"confidence":null}',
        '{"selected_indices":[],"confidence":2}',
    ],
)
def test_one_format_recovery(challenge, assets, bad):
    provider = FakeProvider([bad, '{"selected_indices":[0],"confidence":null}'])
    result = Level1VLMSolver(provider).solve(challenge, assets)
    assert result.answer == [0]
    assert [x[2] for x in provider.calls] == [False, True]
    assert result.parsing_status == "recovered"
    assert result.input_tokens == 200 and result.api_request_count == 2


def test_invalid_recovery_fails_no_prediction(challenge, assets):
    provider = FakeProvider(["bad", "still bad"])
    with pytest.raises(ModelResponseError) as error:
        Level1VLMSolver(provider).solve(challenge, assets)
    assert len(provider.calls) == 2
    assert error.value.api_request_count == 2
    assert error.value.input_tokens == 200
    assert error.value.inference_time_ms >= 0


def test_random_deterministic_without_answer_count(challenge, assets):
    solver = RandomBaseline(seed=42)
    answer = solver.solve(challenge, assets).answer
    assert answer == RandomBaseline(seed=42).solve(challenge, assets).answer
    assert solver.solve(challenge, assets).answer == answer
    assert RandomBaseline(probability=0).solve(challenge, assets).answer == []
    assert RandomBaseline(probability=1).solve(challenge, assets).answer == list(range(9))


def test_openai_modern_multimodal_request(challenge, assets):
    pytest.importorskip("openai")
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(
            output_text=json.dumps({"selected_indices": [0], "confidence": None}),
            usage=SimpleNamespace(input_tokens=123, output_tokens=12),
        )

    provider = OpenAIVisionProvider(
        "test-model", client=SimpleNamespace(responses=SimpleNamespace(create=create))
    )
    result = Level1VLMSolver(provider).solve(challenge, assets)
    request = requests[0]
    content = request["input"][0]["content"]
    assert request["model"] == "test-model"
    assert request["store"] is False
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["text"]["format"]["strict"] is True
    assert sum(x["type"] == "input_image" for x in content) == 9
    assert [x["text"] for x in content if x.get("text", "").startswith("Tile ")] == [
        f"Tile {i}" for i in range(9)
    ]
    assert "zero-based" in content[0]["text"]
    assert challenge.instruction in content[0]["text"]
    assert "BDD100K" not in content[0]["text"]
    assert "seed" not in content[0]["text"]
    assert result.input_tokens == 123


@pytest.mark.parametrize("status,expected", [(429, 2), (503, 2), (400, 1), (401, 1), (500, 1)])
def test_provider_retry_policy(assets, status, expected):
    openai = pytest.importorskip("openai")
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        raise openai.APIStatusError(
            "secret error body",
            response=httpx.Response(
                status, request=httpx.Request("POST", "https://api.openai.com/v1/responses")
            ),
            body={},
        )

    provider = OpenAIVisionProvider(
        "test",
        max_retries=1,
        sleep=lambda _: None,
        client=SimpleNamespace(responses=SimpleNamespace(create=create)),
    )
    with pytest.raises(ModelError) as error:
        provider.infer("Select buses", assets, recovery=False)
    assert len(calls) == expected
    assert error.value.api_request_count == expected
    assert "secret" not in str(error.value)


def test_sdk_http_wire_contract(challenge, assets):
    openai = pytest.importorskip("openai")
    requests = []

    def handler(request):
        requests.append(request)
        assert request.method == "POST" and request.url.path == "/v1/responses"
        body = json.loads(request.content)
        assert "text" in body and "response_format" not in body
        assert body["text"]["format"]["schema"]["additionalProperties"] is False
        text = '{"selected_indices":[0,8],"confidence":null}'
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "test-model",
                "error": None,
                "incomplete_details": None,
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": text, "annotations": []}],
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        sdk = openai.OpenAI(api_key="fake-unit-test-key", max_retries=0, http_client=http)
        provider = OpenAIVisionProvider("test-model", client=sdk)
        prediction = Level1VLMSolver(provider).solve(challenge, assets)
    assert prediction.answer == [0, 8] and prediction.api_request_count == 1
    assert len(requests) == 1 and prediction.usage_complete


def test_recovery_missing_usage_stays_incomplete(challenge, assets):
    provider = FakeProvider([])
    responses = iter(
        [
            ProviderResponse("invalid", input_tokens=100, output_tokens=10),
            ProviderResponse('{"selected_indices":[],"confidence":null}'),
        ]
    )
    provider.infer = lambda *args, **kwargs: next(responses)
    prediction = Level1VLMSolver(provider).solve(challenge, assets)
    assert prediction.input_tokens == 100 and prediction.api_request_count == 2
    assert not prediction.usage_complete


def test_provider_transport_retry(assets):
    openai = pytest.importorskip("openai")
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        raise openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com"))

    provider = OpenAIVisionProvider(
        "test",
        max_retries=1,
        sleep=lambda _: None,
        client=SimpleNamespace(responses=SimpleNamespace(create=create)),
    )
    with pytest.raises(ModelError) as error:
        provider.infer("Select buses", assets, recovery=False)
    assert len(calls) == 2 and error.value.api_request_count == 2


@pytest.mark.parametrize(
    "code",
    [
        "insufficient_quota",
        "credit_balance_exhausted",
        "project_spend_limit_exceeded",
        "organization_spend_limit_exceeded",
        "organization_usage_limit_exceeded",
        "billing_hard_limit_reached",
    ],
)
def test_provider_quota_errors_not_retried(assets, code):
    openai = pytest.importorskip("openai")
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        raise openai.APIStatusError(
            "private provider message",
            response=httpx.Response(
                429, request=httpx.Request("POST", "https://api.openai.com/v1/responses")
            ),
            body={"code": code},
        )

    provider = OpenAIVisionProvider(
        "test",
        max_retries=2,
        sleep=lambda _: None,
        client=SimpleNamespace(responses=SimpleNamespace(create=create)),
    )
    with pytest.raises(ModelError) as error:
        provider.infer("Select buses", assets, recovery=False)
    assert len(calls) == error.value.api_request_count == 1
    assert error.value.provider_error_code == code
    assert "private" not in str(error.value)
