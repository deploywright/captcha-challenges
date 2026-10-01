"""Private route-first topology and independent graph analysis for routing puzzles.

The layout keeps the existing symbol sizes. Crossings are rendered as overpasses;
only explicit node IDs represent connections.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from challenge_engine.core.random import DeterministicRNG


def build_route_network(
    rng: DeterministicRNG, depth: int, total: int, decoys: int,
    destinations: int, width: int, height: int, prefix: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[list[dict[str, Any]]]]:
    """Build the guaranteed route first, then distinct multi-segment decoy branches.

Each main node has two distinct outgoing branches. Additional nodes are real
branch fittings on decoy routes, with a capped alternative at each fitting.
"""
    if not (1 <= decoys <= depth and total >= depth + decoys and 3 <= destinations <= 6):
        raise ValueError("Topology requires depth >= decoys, total >= depth + decoys, and 3..6 destinations")
    columns = min(4, depth)
    rows = (depth + columns - 1) // columns
    row_gap = (height - 280) / rows
    if row_gap < 150 or width / columns < 180:
        raise ValueError("Canvas too small for readable topology; increase canvas dimensions")
    main = []
    for i in range(depth):
        row, col = divmod(i, columns)
        if row % 2:
            col = columns - 1 - col
        main.append({"id": f"m{i}", "x": 160 + col * (width - 320) / max(1, columns - 1),
                     "y": 160 + row * row_gap})
    labels = rng.fork("labels").shuffle([f"{prefix} {chr(65 + i)}" for i in range(destinations)])
    sinks = [{"id": f"t{i}", "label": labels[i], "idx": i,
              "x": 100 + i * (width - 200) / (destinations - 1), "y": height - 60}
             for i in range(destinations)]
    for i, node in enumerate(main):
        node["next"] = main[i + 1] if i + 1 < depth else sinks[0]
        # A long capped spur still requires tracing, rather than an immediate stop.
        node["wrong"] = {"id": f"cap_m{i}", "x": node["x"] + 65, "y": node["y"] + 100, "cap": True}
    # Exclude row-turn nodes where the main route and downward spur would overlap.
    candidates = [i for i in range(depth) if (i + 1) % columns != 0 or i == depth - 1]
    if len(candidates) < decoys:
        candidates = list(range(depth))
    branches = []
    lengths = [1] * decoys
    for i in range(total - depth - decoys):
        lengths[i % decoys] += 1
    for b, attach in enumerate(sorted(rng.fork("attachments").sample(candidates, decoys))):
        root = main[attach]
        chain = []
        for j in range(lengths[b]):
            chain.append({"id": f"d{b}_{j}", "x": root["x"] + (j * 90),
                          "y": root["y"] + 75 + j * 20})
        root["wrong"] = chain[0]
        for j, node in enumerate(chain):
            node["next"] = chain[j + 1] if j + 1 < len(chain) else sinks[1 + b % (destinations - 1)]
            node["wrong"] = {"id": f"cap_d{b}_{j}", "x": node["x"] + 35,
                             "y": node["y"] + 40, "cap": True}
        branches.append(chain)
    return main, sinks, branches


def reachable_tanks(source: str, edges: list[dict[str, Any]], tanks: dict[str, str]) -> set[str]:
    """Undirected BFS based solely on edge endpoints and valve states."""
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge["valve"] == "OPEN":
            adjacency[edge["u"]].append(edge["v"])
            adjacency[edge["v"]].append(edge["u"])
    seen = {source}
    queue = deque([source])
    while queue:
        for node in adjacency[queue.popleft()]:
            if node not in seen:
                seen.add(node)
                queue.append(node)
    return {label for node, label in tanks.items() if node in seen}


def private_graph_edges(edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Serialize graph IDs only for PRIVATE answer metadata."""
    return [{"id": e["id"], "u": e["u"]["id"], "v": e["v"]["id"], "valve": e["valve"]}
            for e in edges]
