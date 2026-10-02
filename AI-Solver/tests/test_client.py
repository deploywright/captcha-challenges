import httpx
import pytest
from conftest import IMAGE

from ai_solver.client import BenchmarkClient
from ai_solver.contracts import CatalogEntry, SolverPrediction
from ai_solver.errors import (
    AssetDownloadError,
    ChallengeContractError,
    NetworkError,
    PublicDataLeakError,
    SubmissionError,
)

BASE = "https://benchmark.example"


def client(handler, retries=2):
    return BenchmarkClient(
        BASE + "/",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=retries,
        sleep=lambda _: None,
    )


def prediction(challenge):
    return SolverPrediction(
        challenge_id=challenge.id,
        answer=[0, 3, 8],
        solver_name="test",
        model_name="test",
        inference_time_ms=12.5,
    )


def test_download_and_cache(public_data, challenge):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("challenge.json"):
            return httpx.Response(200, json=public_data)
        if request.url.path.endswith("catalog.json"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": challenge.id,
                        "level": 1,
                        "variant": "street-grid",
                        "challengeUrl": f"/challenges/{challenge.id}/challenge.json",
                    }
                ],
            )
        return httpx.Response(200, content=IMAGE, headers={"content-type": "image/webp"})

    c = client(handler)
    entry = c.get_catalog()[0]
    assert c.get_challenge(entry) == challenge
    assert c.download_assets(challenge) == [IMAGE] * 9
    c.get_catalog()
    c.get_challenge(entry)
    c.download_assets(challenge)
    assert len(calls) == 11
    assert c.base_url == BASE


def test_wrong_answer_not_retried(challenge):
    calls = []

    def handler(request):
        import json

        calls.append(request)
        assert request.method == "POST"
        assert request.url.path == f"/api/challenges/{challenge.id}/submit"
        assert json.loads(request.content) == {"answer": [0, 3, 8], "solveTimeMs": 12.5}
        return httpx.Response(
            200,
            json={
                "correct": False,
                "challengeId": challenge.id,
                "variant": "street-grid",
                "solveTimeMs": 12.5,
            },
        )

    result, status = client(handler).submit(challenge, prediction(challenge))
    assert result.correct is False and status == 200
    assert len(calls) == 1


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_transient_retry(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status if len(calls) == 1 else 200, json=[])

    assert client(handler).get_catalog() == []
    assert len(calls) == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500, 302])
def test_nonretry_status(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status, json={"error": "test"}, headers={"location": "https://evil.example/secret"}
        )

    with pytest.raises(NetworkError):
        client(handler).get_catalog()
    assert len(calls) == 1


def test_transport_retry_exhaustion():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("test", request=request)

    with pytest.raises(NetworkError):
        client(handler).get_catalog()
    assert len(calls) == 3


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/challenges/lvl1_test/challenge.json",
        "/challenges/lvl1_test/answer.json",
        "file:///secret",
        "/challenges/lvl1_test/%63hallenge.json",
        "/challenges/lvl1_test/challenge.json?secret=1",
        "/challenges/lvl1_test/challenge.json#x",
    ],
)
def test_challenge_path_allowlist(url):
    def handler(request):
        raise AssertionError("Forbidden URL must not be requested")

    entry = CatalogEntry(id="lvl1_test", level=1, variant="street-grid", challengeUrl=url)
    with pytest.raises(ChallengeContractError):
        client(handler).get_challenge(entry)


@pytest.mark.parametrize(
    "url",
    [
        "/challenges/lvl1_test/answer.json",
        "/challenges/lvl1_test/assets/answer.json",
        "/challenges/other/assets/a.webp",
        "https://evil.example/a.webp",
        "/challenges/lvl1_test/assets/%2e%2e/a.webp",
        "/challenges/lvl1_test/assets/a.webp?x=1",
    ],
)
def test_asset_path_allowlist(challenge, url):
    challenge.assets = [url]
    with pytest.raises(ChallengeContractError):
        client(lambda _: pytest.fail("Unexpected request")).download_assets(challenge)


@pytest.mark.parametrize("status", [200, 404, 429])
def test_leak_before_status_handling_or_retries(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"details": {"answer": [1]}})

    with pytest.raises(PublicDataLeakError):
        client(handler).get_catalog()
    assert len(calls) == 1


def test_json_disguised_as_image(challenge):
    with pytest.raises(PublicDataLeakError):
        client(
            lambda _: httpx.Response(
                200, json={"targetClass": "bus"}, headers={"content-type": "image/webp"}
            )
        ).download_assets(challenge)


def test_asset_download_error(challenge):
    with pytest.raises(AssetDownloadError):
        client(lambda _: httpx.Response(200, text="not-an-image")).download_assets(challenge)


def test_submission_identity_and_error(challenge):
    with pytest.raises(SubmissionError):
        client(
            lambda _: httpx.Response(
                200, json={"correct": True, "challengeId": "other", "variant": "street-grid"}
            )
        ).submit(challenge, prediction(challenge))
    with pytest.raises(SubmissionError) as error:
        client(lambda _: httpx.Response(404, json={"error": "not found"})).submit(
            challenge, prediction(challenge)
        )
    assert error.value.status_code == 404


def test_transient_submission_retry_preserves_answer(challenge):
    calls = []

    def handler(request):
        calls.append(request.content)
        if len(calls) == 1:
            return httpx.Response(503, json={"error": "try again"})
        return httpx.Response(
            200, json={"correct": False, "challengeId": challenge.id, "variant": "street-grid"}
        )

    result, _ = client(handler).submit(challenge, prediction(challenge))
    assert result.correct is False
    assert len(calls) == 2 and calls[0] == calls[1]


def test_path_traversal_rejected_before_url_normalization(challenge):
    challenge.assets = ["/challenges/lvl1_test/assets/../assets/a.webp"]
    with pytest.raises(ChallengeContractError):
        client(lambda _: pytest.fail("Unexpected request")).download_assets(challenge)
