import json
from unittest.mock import Mock

import pytest

from ai_solver.config import RunConfig
from ai_solver.contracts import CatalogEntry, SolverPrediction, SubmissionResponse
from ai_solver.errors import ModelResponseError, NetworkError, PublicDataLeakError, SubmissionError
from ai_solver.runner import BenchmarkRunner


def setup_runner(tmp_path, challenge, assets, *, dry_run=False):
    client = Mock(base_url="https://benchmark.example")
    entry = CatalogEntry(
        id=challenge.id,
        level=1,
        variant="street-grid",
        challengeUrl=f"/challenges/{challenge.id}/challenge.json",
    )
    client.get_catalog.return_value = [entry]
    client.get_challenge.return_value = challenge
    client.download_assets.return_value = assets
    client.submit.return_value = (
        SubmissionResponse(correct=False, challengeId=challenge.id, variant=challenge.variant),
        200,
    )
    solver = Mock(name="solver")
    solver.name, solver.model_name = "test", "fake"
    solver.solve.return_value = SolverPrediction(
        challenge_id=challenge.id,
        answer=[0, 3],
        solver_name="test",
        model_name="fake",
        inference_time_ms=12.0,
    )
    config = RunConfig(base_url=client.base_url, output_dir=tmp_path, dry_run=dry_run)
    return BenchmarkRunner(client, solver, config), client, solver


def test_one_prediction_wrong_answer_no_adaptation_jsonl(tmp_path, challenge, assets):
    runner, client, solver = setup_runner(tmp_path, challenge, assets)
    output, summary = runner.run()
    solver.solve.assert_called_once_with(challenge, assets)
    client.submit.assert_called_once()
    rows = [json.loads(line) for line in (output / "predictions.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["prediction"] == [0, 3] and row["correct"] is False
    assert row["submission_status"] == 200
    assert row["asset_count"] == 9
    assert row["inference_time_ms"] == 12
    assert row["submission_time_ms"] >= 0 and row["asset_download_time_ms"] >= 0
    assert summary["incorrect_count"] == 1 and summary["exact_challenge_accuracy"] == 0
    metadata = json.loads((output / "run.json").read_text())
    assert metadata["discovered_challenge_count"] == metadata["challenge_count"] == 1
    assert metadata["status"] == "completed"
    assert json.loads((output / "summary.json").read_text())["evaluated_count"] == 1


def test_dry_run_never_submits(tmp_path, challenge, assets):
    runner, client, solver = setup_runner(tmp_path, challenge, assets, dry_run=True)
    output, summary = runner.run()
    client.submit.assert_not_called()
    solver.solve.assert_called_once()
    assert summary["exact_challenge_accuracy"] is None
    assert summary["dry_run_count"] == 1
    assert json.loads((output / "predictions.jsonl").read_text())["correct"] is None


def test_failure_continues(tmp_path, challenge, assets):
    runner, client, solver = setup_runner(tmp_path, challenge, assets)
    second = challenge.model_copy(update={"id": "second"})
    client.get_catalog.return_value.append(
        CatalogEntry(
            id="second",
            level=1,
            variant="street-grid",
            challengeUrl="/challenges/second/challenge.json",
        )
    )
    client.get_challenge.side_effect = [NetworkError("failed first"), second]
    solver.solve.return_value.challenge_id = "second"
    client.submit.return_value = (
        SubmissionResponse(correct=True, challengeId="second", variant="street-grid"),
        200,
    )
    output, summary = runner.run()
    assert client.get_challenge.call_count == 2
    assert solver.solve.call_count == client.submit.call_count == 1
    assert len((output / "predictions.jsonl").read_text().splitlines()) == 2
    assert summary["error_count"] == 1
    assert summary["correct_count"] == 1 and summary["evaluation_coverage"] == 0.5


def test_solver_error_not_submitted(tmp_path, challenge, assets):
    runner, client, solver = setup_runner(tmp_path, challenge, assets)
    solver.solve.side_effect = ModelResponseError("invalid structured output")
    output, summary = runner.run()
    client.submit.assert_not_called()
    row = json.loads((output / "predictions.jsonl").read_text())
    assert row["status"] == "solver_error" and row["prediction"] is None
    assert row["error_type"] == "ModelResponseError"
    assert summary["solver_error_count"] == 1


@pytest.mark.parametrize("phase", ["get_catalog", "get_challenge", "download_assets", "submit"])
def test_leak_aborts_entire_run(tmp_path, challenge, assets, phase):
    runner, client, solver = setup_runner(tmp_path, challenge, assets)
    getattr(client, phase).side_effect = PublicDataLeakError()
    with pytest.raises(PublicDataLeakError):
        runner.run()
    output = next(tmp_path.iterdir())
    metadata = json.loads((output / "run.json").read_text())
    assert metadata["status"] == "failed"
    assert metadata["error"] == "PUBLIC DATA LEAK DETECTED"
    assert json.loads((output / "summary.json").read_text())["status"] == "failed"
    assert (output / "predictions.jsonl").read_text() == ""


def test_submission_error_keeps_prediction_and_status(tmp_path, challenge, assets):
    runner, client, _ = setup_runner(tmp_path, challenge, assets)
    client.submit.side_effect = SubmissionError("Submission HTTP failure", status_code=503)
    row = runner.evaluate(challenge.id, submit=True)
    assert row.prediction == [0, 3]
    assert row.correct is None and row.submission_status == 503
    assert row.submission_time_ms >= 0 and row.inference_time_ms == 12


def test_unexpected_error_does_not_log_secrets(tmp_path, challenge, assets):
    runner, _, solver = setup_runner(tmp_path, challenge, assets)
    solver.solve.side_effect = RuntimeError("sk-secret-sensitive-data")
    output, _ = runner.run()
    assert "sk-secret" not in (output / "predictions.jsonl").read_text()


def test_no_prediction_adaptation_after_wrong_answer(tmp_path, challenge, assets):
    runner, client, solver = setup_runner(tmp_path, challenge, assets)
    second = challenge.model_copy(update={"id": "second"})
    client.get_catalog.return_value.append(
        CatalogEntry(
            id="second",
            level=1,
            variant="street-grid",
            challengeUrl="/challenges/second/challenge.json",
        )
    )
    client.get_challenge.side_effect = [challenge, second]
    second_prediction = solver.solve.return_value.model_copy(update={"challenge_id": "second"})
    solver.solve.side_effect = [solver.solve.return_value, second_prediction]
    client.submit.side_effect = [
        client.submit.return_value,
        (SubmissionResponse(correct=False, challengeId="second", variant="street-grid"), 200),
    ]
    _, summary = runner.run()
    assert summary["incorrect_count"] == 2
    assert solver.solve.call_count == client.submit.call_count == 2
    assert [call.args[0].id for call in solver.solve.call_args_list] == [challenge.id, "second"]
    assert all(call.args[1] == assets and not call.kwargs for call in solver.solve.call_args_list)


def test_unexpected_catalog_error_has_failed_metadata(tmp_path, challenge, assets):
    runner, client, _ = setup_runner(tmp_path, challenge, assets)
    client.get_catalog.side_effect = RuntimeError("sk-secret")
    with pytest.raises(Exception, match="Unexpected benchmark failure"):
        runner.run()
    output = next(tmp_path.iterdir())
    metadata = (output / "run.json").read_text()
    assert "sk-secret" not in metadata
    assert json.loads(metadata)["status"] == "failed"


def test_provider_quota_failure_diagnostics(tmp_path, challenge, assets):
    from ai_solver.errors import ModelError

    runner, client, solver = setup_runner(tmp_path, challenge, assets)
    failure = ModelError("Model provider HTTP failure", status_code=429)
    failure.provider_error_code = "credit_balance_exhausted"
    failure.api_request_count = 1
    solver.solve.side_effect = failure
    output, summary = runner.run()
    client.submit.assert_not_called()
    row = json.loads((output / "predictions.jsonl").read_text())
    assert row["model_status"] == 429
    assert row["provider_error_code"] == "credit_balance_exhausted"
    assert row["prediction"] is None and row["parsing_status"] == "not_received"
    assert summary["status"] == "completed_with_errors"
