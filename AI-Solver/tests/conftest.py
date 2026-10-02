import copy

import pytest

from ai_solver.contracts import parse_challenge

IMAGE = b"RIFF\x10\x00\x00\x00WEBPsynthetic-test-image"


@pytest.fixture
def public_data():
    return {
        "schemaVersion": 1,
        "id": "lvl1_test",
        "level": 1,
        "variant": "street-grid",
        "type": "image-selection",
        "instruction": "Select all images containing a bus.",
        "seed": 49,
        "assets": [f"/challenges/lvl1_test/assets/{i}.webp" for i in range(9)],
        "ui": {"rows": 3, "columns": 3, "selectionMode": "multiple"},
    }


@pytest.fixture
def challenge(public_data):
    return parse_challenge(copy.deepcopy(public_data))


@pytest.fixture
def assets():
    return [IMAGE] * 9


@pytest.fixture(autouse=True)
def prohibit_external_network(monkeypatch, request):
    if "integration" in request.keywords:
        return
    import httpx

    def forbidden(*args, **kwargs):
        raise AssertionError("Unit tests cannot access real HTTP or model APIs")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
