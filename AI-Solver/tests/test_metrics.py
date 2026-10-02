import pytest

from ai_solver.contracts import ChallengeResult
from ai_solver.metrics import aggregate_metrics


def row(correct, inference, total, variant="street-grid", level=1, **kwargs):
    return ChallengeResult(
        challenge_id="test",
        variant=variant,
        level=level,
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


def test_aggregate_metrics_stages_and_macro_accuracy():
    rows = [
        # street-grid (Level 1): 2 correct, 1 incorrect -> 2/3
        row(True, 10, 100, variant="street-grid", level=1),
        row(True, 10, 100, variant="street-grid", level=1),
        row(False, 10, 100, variant="street-grid", level=1),
        # hard-street-grid (Level 2A): 1 correct, 1 incorrect -> 1/2
        row(True, 10, 100, variant="hard-street-grid", level=2),
        row(False, 10, 100, variant="hard-street-grid", level=2),
        # checker-shadow (Level 2B): 1 correct, 0 incorrect -> 1/1
        row(True, 10, 100, variant="checker-shadow", level=2),
        # routing-puzzle (Level 3A): 2 correct, 0 incorrect -> 2/2
        row(True, 10, 100, variant="routing-puzzle", level=3),
        row(True, 10, 100, variant="routing-puzzle", level=3),
        # degraded-vision (Level 3B): 0 correct, 2 incorrect -> 0/2
        row(False, 10, 100, variant="degraded-vision", level=3),
        row(False, 10, 100, variant="degraded-vision", level=3),
    ]
    summary = aggregate_metrics(rows)
    assert "by_stage" in summary
    assert "macro_stage_accuracy" in summary
    assert "by_numeric_level" in summary
    assert set(summary["by_stage"].keys()) == {
        "Level 1",
        "Level 2A",
        "Level 2B",
        "Level 3A",
        "Level 3B",
    }
    expected_macro = (2 / 3 + 0.5 + 1.0 + 1.0 + 0.0) / 5
    assert summary["macro_stage_accuracy"] == pytest.approx(expected_macro)
    # micro accuracy = 6 / 10 = 0.6
    assert summary["exact_challenge_accuracy"] == pytest.approx(0.6)
    assert summary["by_stage"]["Level 1"]["challenge_count"] == 3
    assert summary["by_stage"]["Level 1"]["correct_count"] == 2
    assert summary["by_stage"]["Level 2A"]["challenge_count"] == 2
    assert summary["by_stage"]["Level 2B"]["challenge_count"] == 1
    assert summary["by_stage"]["Level 3A"]["challenge_count"] == 2
    assert summary["by_stage"]["Level 3B"]["challenge_count"] == 2
