"""Tests for Level 3A — The Tangled Cables bijection, route geometry, and query correctness."""

from __future__ import annotations

import pytest

from challenge_engine.core.schemas import Level3AConfig
from challenge_engine.levels.level_3a.generator import Level3ATangledCablesGenerator


@pytest.mark.parametrize(
    "difficulty,cable_count,query_type",
    [
        ("easy", None, "find_source"),
        ("medium", None, "find_destination"),
        ("hard", 30, "find_source"),
        ("extreme", None, "find_source"),
    ],
)
def test_level_3a_bijection_and_query_correctness(
    difficulty: str,
    cable_count: int | None,
    query_type: str,
) -> None:
    """Every source must map to 1 unique destination, routes must stay in bounds, and query must be exact."""
    cfg = Level3AConfig(
        difficulty=difficulty,  # type: ignore[arg-type]
        cableCount=cable_count,
        queryType=query_type,  # type: ignore[arg-type]
    )
    gen = Level3ATangledCablesGenerator(cfg)
    bundle = gen.generate_one(seed=305)

    pub = bundle.public_challenge
    priv = bundle.private_answer

    assert pub.level == 3
    assert pub.variant == "tangled-cables"
    assert priv.datasetSource == "procedural-tangled-cables"
    assert priv.connections is not None
    assert priv.query is not None
    assert priv.annotations is not None
    assert priv.annotations.controlPoints is not None
    assert priv.annotations.difficultyMetadata is not None

    n = len(priv.connections)
    if cable_count is not None:
        assert n == cable_count
    elif difficulty == "easy":
        assert 8 <= n <= 10
    elif difficulty == "medium":
        assert 12 <= n <= 20
    elif difficulty == "extreme":
        assert n >= 35

    sources = list(priv.connections.keys())
    dests = list(priv.connections.values())
    assert len(set(sources)) == n
    assert len(set(dests)) == n
    assert set(sources) == {f"server_{i + 1}" for i in range(n)}
    assert set(dests) == {f"port_{i + 1}" for i in range(n)}

    if query_type in {"find_source", "find-source"}:
        inv = {d: s for s, d in priv.connections.items()}
        assert priv.answer == inv[priv.query.target]
    else:
        assert priv.answer == priv.connections[priv.query.target]

    assert pub.ui.options is not None
    assert pub.ui.options[priv.correctSelection[0]] == priv.answer

    width, height = priv.annotations.canvasDimensions
    for src, dst in priv.connections.items():
        pts = priv.annotations.centerlines[src]
        assert len(pts) >= 10
        assert pts[0] == priv.annotations.endpointPositions["sources"][src]
        assert pts[-1] == priv.annotations.endpointPositions["destinations"][dst]
        for x, y in pts:
            assert 0.0 <= x <= width
            assert 0.0 <= y <= height
