"""Difficulty must describe measured topology, across seeds and all subtypes."""

from collections import Counter, deque
import json

import numpy as np
import pytest
from pydantic import ValidationError

from challenge_engine.core.exporter import export_challenge_bundle
from challenge_engine.core.schemas import Level3AConfig, PublicChallenge, ROUTING_DIFFICULTY_PRESETS
from challenge_engine.core.validation import FORBIDDEN_PUBLIC_KEYS, validate_single_challenge_dir
from challenge_engine.levels.level_3a.laser_maze import LaserMazeGenerator
from challenge_engine.levels.level_3a.topology import reachable_tanks
from scripts.generate_level_3a_batch import DIFFICULTY_SCHEDULE
from test_level_3a_routing_puzzles import SUBTYPE_CLASSES

DIFFICULTIES = ["easy", "medium", "story", "hard", "extreme"]
SEEDS = [101, 202, 303, 404, 505]


@pytest.mark.parametrize("subtype,cls", SUBTYPE_CLASSES)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
@pytest.mark.parametrize("seed", SEEDS)
def test_measured_complexity(subtype, cls, difficulty, seed):
    bundle = cls(Level3AConfig(difficulty=difficulty)).generate_one(seed)
    r = bundle.private_answer.routing
    p = ROUTING_DIFFICULTY_PRESETS[subtype][difficulty]
    pub = bundle.public_challenge
    assert pub.difficulty == r["difficulty"] == difficulty
    assert not FORBIDDEN_PUBLIC_KEYS.intersection(pub.model_dump())
    if subtype == "laser-maze":
        start = tuple(r["emitter"]["perimeter"])
        direction = tuple(r["emitter"]["direction"])
        start = tuple(start[i] + direction[i] for i in range(2))
        mirrors = {tuple(m["cell"]): m["orientation"] for m in r["mirrors"]}
        _, hits, exit_pos = LaserMazeGenerator(Level3AConfig())._simulate_ray(*r["gridDimensions"], start, direction, mirrors)
        assert p["reflections"][0] <= len(hits) == r["reflectionCount"] <= p["reflections"][1]
        assert len(mirrors) == r["mirrorCount"] == r["totalMirrorCount"]
        assert p["distractors"][0] <= len(mirrors) - len(set(hits)) == r["distractorMirrorCount"] <= p["distractors"][1]
        assert r["targetCount"] == len(pub.ui.options) == p["targets"]
        assert r["gridDimensions"] == list(p["grid"])
        assert list(exit_pos) == r["targets"][bundle.private_answer.answer]
        gen = LaserMazeGenerator(Level3AConfig(difficulty=difficulty))
        boxes = [gen._emitter_box(*r["gridDimensions"], tuple(r["emitter"]["perimeter"]))]
        boxes.extend(gen._target_box(*r["gridDimensions"], tuple(pos)) for pos in r["targets"].values())
        assert all(gen._boxes_separate(a, b) for i, a in enumerate(boxes) for b in boxes[i+1:])
    elif subtype == "conveyor-routing":
        graph = r["switchGraph"]
        current = "m0"
        path = []
        while current in graph:
            assert current not in path
            path.append(current)
            n = graph[current]
            assert n["left"] != n["right"]
            current = n[n["state"]]
        assert path + [current] == r["solutionPath"]
        assert len(path) == r["routeDecisionDepth"] == p["routeDecisionDepth"]
        assert len(graph) == r["totalSwitchCount"] == p["totalSwitchCount"]
        assert len(r["decoyPaths"]) == r["decoyBranchCount"] == p["decoyBranchCount"]
        assert all(len(branch) >= 2 for branch in r["decoyPaths"])
        assert r["binCount"] == len(pub.ui.options) == p["bins"]
    elif subtype == "pipe-flow":
        assert reachable_tanks(r["source"], r["edges"], r["tanks"]) == {bundle.private_answer.answer}
        # Compute the open shortest path independently, and count real fittings
        # with >=3 connected edges instead of trusting the recorded path length.
        degree = Counter()
        adjacency = {}
        for e in r["edges"]:
            degree.update([e["u"], e["v"]])
            if e["valve"] == "OPEN":
                adjacency.setdefault(e["u"], []).append(e["v"])
                adjacency.setdefault(e["v"], []).append(e["u"])
        queue = deque([(r["source"], [])])
        seen = set()
        while queue:
            node, path = queue.popleft()
            if node in seen:
                continue
            seen.add(node)
            path = path + [node]
            if node in r["tanks"]:
                break
            queue.extend((child, path) for child in adjacency.get(node, []))
        assert path == r["solutionPath"]
        assert sum(degree[n] >= 3 for n in path) == r["solutionDecisionDepth"] == p["solutionDecisionDepth"]
        assert sum(d >= 3 for d in degree.values()) == r["totalJunctionCount"] == p["totalJunctionCount"]
        closed = [e for e in r["edges"] if e["valve"] == "CLOSED"]
        assert len(closed) == r["criticalClosedValveCount"] == p["criticalClosedValveCount"]
        for e in closed:
            assert e["u"].startswith("d")  # never block the main junction's first branch
            opened = [dict(edge, valve="OPEN") if edge["id"] == e["id"] else edge for edge in r["edges"]]
            assert len(reachable_tanks(r["source"], opened, r["tanks"])) > 1
        assert len(r["tanks"]) == r["tankCount"] == p["tanks"]
        assert len(r["decoyPaths"]) == r["decoyBranchCount"] == p["decoyBranchCount"]
    else:
        assert p["cableCountRange"][0] <= len(r["connections"]) == r["cableCount"] <= p["cableCountRange"][1]
        assert p["waypointRange"][0] <= r["waypointColumnCount"] <= p["waypointRange"][1]
        assert p["answerOptionCountRange"][0] <= len(pub.ui.options) == r["answerOptionCount"] <= p["answerOptionCountRange"][1]


@pytest.mark.parametrize("subtype,cls", SUBTYPE_CLASSES)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_deterministic_difficulty_export(subtype, cls, difficulty, tmp_path):
    generator = cls(Level3AConfig(difficulty=difficulty))
    a, b = generator.generate_one(101), generator.generate_one(101)
    assert a.public_challenge == b.public_challenge
    assert a.private_answer == b.private_answer
    assert np.array_equal(np.asarray(next(iter(a.assets.values()))), np.asarray(next(iter(b.assets.values()))))
    directory = export_challenge_bundle(a, tmp_path, update_manifest=False)
    raw = json.loads((directory / "challenge.json").read_text())
    assert PublicChallenge.model_validate(raw).difficulty == difficulty
    result = validate_single_challenge_dir(directory, check_determinism=True)
    assert result.passed, result.errors


@pytest.mark.parametrize("subtype,cls", SUBTYPE_CLASSES)
def test_generated_complexity_monotonicity(subtype, cls):
    key = {"laser-maze": "reflectionCount", "conveyor-routing": "routeDecisionDepth",
           "pipe-flow": "solutionDecisionDepth", "device-cables": "cableCount"}[subtype]
    values = [[cls(Level3AConfig(difficulty=d)).generate_one(seed).private_answer.routing[key]
               for seed in SEEDS] for d in DIFFICULTIES]
    means = [sum(v) / len(v) for v in values]
    assert means[0] < means[1] < means[2] <= means[3] < means[4]
    for earlier, later in zip(values, values[1:]):
        assert max(earlier) <= min(later)


def test_story_schema_and_schedule():
    assert Level3AConfig(difficulty="story").difficulty == "story"
    with pytest.raises(ValidationError):
        Level3AConfig(difficulty="invented")
    assert DIFFICULTY_SCHEDULE == [("easy", 2), ("medium", 3), ("story", 5), ("hard", 3), ("extreme", 2)]


@pytest.mark.parametrize("subtype,overrides,expected", [
    ("conveyor-routing", {"conveyorRouting": {"routeDecisionDepth": 5, "totalSwitchCount": 12, "decoyBranches": 3, "binCount": 4}}, {"routeDecisionDepth": 5, "totalSwitchCount": 12, "decoyBranchCount": 3, "binCount": 4}),
    ("pipe-flow", {"pipeFlow": {"solutionDecisionDepth": 5, "totalJunctionCount": 9, "decoyBranchCount": 3, "closedValves": 3, "tankCount": 4}}, {"solutionDecisionDepth": 5, "totalJunctionCount": 9, "decoyBranchCount": 3, "criticalClosedValveCount": 3, "tankCount": 4}),
])
def test_explicit_topology_overrides_are_applied_and_reproducible(subtype, overrides, expected, tmp_path):
    cls = dict(SUBTYPE_CLASSES)[subtype]
    bundle = cls(Level3AConfig(difficulty="story", **overrides)).generate_one(101)
    assert all(bundle.private_answer.routing[key] == value for key, value in expected.items())
    directory = export_challenge_bundle(bundle, tmp_path, update_manifest=False)
    result = validate_single_challenge_dir(directory, check_determinism=True)
    assert result.passed, result.errors


def test_pipe_rejects_invalid_reachability_and_retries(monkeypatch):
    from challenge_engine.levels.level_3a import pipe_flow
    original = pipe_flow.reachable_tanks
    calls = []
    def fail_first_two(source, edges, tanks):
        calls.append(edges)
        if len(calls) == 1:
            return set()
        if len(calls) == 2:
            return set(tanks.values())
        return original(source, edges, tanks)
    monkeypatch.setattr(pipe_flow, "reachable_tanks", fail_first_two)
    bundle = pipe_flow.PipeFlowGenerator(Level3AConfig(difficulty="story")).generate_one(101)
    r = bundle.private_answer.routing
    assert r["generationAttempt"] == 2
    assert original(r["source"], r["edges"], r["tanks"]) == {bundle.private_answer.answer}
