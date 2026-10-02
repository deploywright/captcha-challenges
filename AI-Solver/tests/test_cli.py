import json

import pytest

from ai_solver import cli
from ai_solver.config import RunConfig, load_config, normalize_base_url
from ai_solver.contracts import ChallengeResult


def test_config_cli_overrides_environment_and_yaml(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("base_url: https://yaml.example\nseed: 7\nsolver: random\n")
    monkeypatch.setenv("CAPTCHA_BASE_URL", "https://environment.example/")
    assert load_config({}, path).base_url == "https://environment.example"
    config = load_config({"base_url": "https://cli.example///", "seed": 42}, path)
    assert config.base_url == "https://cli.example" and config.seed == 42
    assert config.solver == "random"


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp",
        "https://user:secret@example.com",
        "https://x/a",
        "https://x?secret=x",
        "https://x#fragment",
        "https://x:invalid",
    ],
)
def test_invalid_base_url(url):
    with pytest.raises(ValueError):
        normalize_base_url(url)


def test_missing_config_never_echoes_secrets(monkeypatch):
    monkeypatch.delenv("CAPTCHA_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="base_url"):
        load_config({})
    with pytest.raises(ValueError) as error:
        load_config({"base_url": "https://example.com", "api_key": "sk-secret"})
    assert "sk-secret" not in str(error.value)


@pytest.mark.parametrize(
    "submit,dry_run,expected", [(False, False, False), (True, False, True), (True, True, False)]
)
def test_single_challenge_explicit_submit(monkeypatch, capsys, submit, dry_run, expected):
    calls = []

    def evaluate(self, entry, *, submit):
        calls.append((entry, submit))
        return ChallengeResult(
            challenge_id=entry,
            variant="street-grid",
            level=1,
            solver="random",
            model="bernoulli",
            prediction=[0],
        )

    monkeypatch.setattr(cli.BenchmarkRunner, "evaluate", evaluate)
    argv = ["solve", "test", "--base-url", "https://benchmark.example", "--solver", "random"]
    if submit:
        argv.append("--submit")
    if dry_run:
        argv.append("--dry-run")
    assert cli.main(argv) == 0
    assert calls == [("test", expected)]
    assert json.loads(capsys.readouterr().out)["prediction"] == [0]


def test_config_bounds():
    with pytest.raises(ValueError):
        RunConfig(base_url="https://example.com", limit=0)
