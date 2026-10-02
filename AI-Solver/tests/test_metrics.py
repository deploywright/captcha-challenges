import pytest

from ai_solver.contracts import ChallengeResult
from ai_solver.metrics import aggregate_metrics


def row(correct, inference, total, **kwargs):
    return ChallengeResult(
        challenge_id="test",
        variant="street-grid",
        level=1,
        solver="test",
        model="fake",
        correct=correct,
        prediction=[0],
        inference_time_ms=inference,
        total_time_ms=total,
        **kwargs,
    )


def test_exact_accuracy_and_latency():
    rows = [
        row(True, 10, 100),
        row(False, 20, 200),
        row(True, 30, 300),
        ChallengeResult(
            challenge_id="error",
            variant="street-grid",
            level=1,
            solver="test",
            model="fake",
            inference_time_ms=50,
            total_time_ms=400,
            status="solver_error",
            error_type="ModelError",
            error="failed",
        ),
    ]
    summary = aggregate_metrics(rows)
    assert summary["exact_challenge_accuracy"] == pytest.approx(2 / 3)
    assert summary["correct_count"] == 2 and summary["incorrect_count"] == 1
    assert summary["solver_error_count"] == 1 and summary["evaluation_coverage"] == 0.75
    assert summary["mean_inference_time_ms"] == summary["median_inference_time_ms"] == 20
    assert summary["p95_inference_time_ms"] == 30
    assert summary["mean_total_time_ms"] == summary["median_total_time_ms"] == 250
    assert not any(key in summary for key in ("precision", "recall", "F1"))


def test_empty_and_dry_run_have_no_accuracy():
    assert aggregate_metrics([])["exact_challenge_accuracy"] is None
    summary = aggregate_metrics([row(None, 10, 20, status="dry_run")])
    assert summary["evaluated_count"] == 0 and summary["exact_challenge_accuracy"] is None
    assert summary["mean_inference_time_ms"] == 10
    assert summary["estimated_cost_usd"] is None


def test_usage_and_only_explicit_prices():
    rows = [row(True, 10, 20, api_request_count=1, input_tokens=1000, output_tokens=100)]
    assert aggregate_metrics(rows)["estimated_cost_usd"] is None
    result = aggregate_metrics(rows, input_price_per_million=2, output_price_per_million=10)
    assert result["estimated_cost_usd"] == pytest.approx(0.003)
    assert result["estimated_api_request_count"] == 1


def test_missing_usage_does_not_invent_cost():
    rows = [
        row(True, 10, 20, api_request_count=1, input_tokens=100, output_tokens=10),
        row(None, 10, 20, api_request_count=1),
    ]
    result = aggregate_metrics(rows, input_price_per_million=2, output_price_per_million=10)
    assert result["usage_complete"] is False and result["estimated_cost_usd"] is None


def test_partial_recovery_usage_disables_cost():
    rows = [
        row(
            True,
            10,
            20,
            api_request_count=2,
            input_tokens=100,
            output_tokens=10,
            usage_complete=False,
        )
    ]
    result = aggregate_metrics(rows, input_price_per_million=2, output_price_per_million=10)
    assert not result["usage_complete"] and result["estimated_cost_usd"] is None
