"""Security tests may name forbidden resources; runtime source may not depend on them."""

import ast
from pathlib import Path


def test_source_has_no_private_imports_or_references():
    source = Path(__file__).parents[1] / "src" / "ai_solver"
    forbidden = [
        "generated-private",
        "answer.json",
        "challenge_engine",
        "PrivateAnswer",
        "challenges/generated",
        "source_image_id",
        "source_path",
    ]
    for path in source.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"Forbidden source dependency in {path.name}: {token}"
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("web", "challenges", "challenge_engine"))
            if isinstance(node, ast.Import):
                assert all(
                    not alias.name.startswith(("web", "challenges", "challenge_engine"))
                    for alias in node.names
                )


def test_environment_and_results_ignore_rules():
    rules = (Path(__file__).parents[1] / ".gitignore").read_text()
    assert ".env" in rules and "results/*" in rules and "!results/.gitkeep" in rules
