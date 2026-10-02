"""Exact challenge outcomes only; no hidden per-tile labels are available."""

import math
import statistics

from .contracts import ChallengeResult


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def aggregate_metrics(
    results: list[ChallengeResult],
    *,
    input_price_per_million: float | None = None,
    output_price_per_million: float | None = None,
) -> dict:
    correct = sum(row.correct is True for row in results)
    incorrect = sum(row.correct is False for row in results)
    evaluated = correct + incorrect
    errors = sum(row.error_type is not None for row in results)
    inference = [row.inference_time_ms for row in results if row.inference_time_ms is not None]
    completed_inference = [
        row.inference_time_ms
        for row in results
        if row.prediction is not None and row.inference_time_ms is not None
    ]
    total = [row.total_time_ms for row in results]
    input_tokens = [row.input_tokens for row in results if row.input_tokens is not None]
    output_tokens = [row.output_tokens for row in results if row.output_tokens is not None]
    usage_complete = all(
        row.api_request_count == 0
        or (row.usage_complete and row.input_tokens is not None and row.output_tokens is not None)
        for row in results
    )
    cost = None
    if (
        input_tokens
        and output_tokens
        and usage_complete
        and input_price_per_million is not None
        and output_price_per_million is not None
    ):
        cost = (
            sum(input_tokens) * input_price_per_million
            + sum(output_tokens) * output_price_per_million
        ) / 1_000_000
    return {
        "challenge_count": len(results),
        "evaluated_count": evaluated,
        "correct_count": correct,
        "incorrect_count": incorrect,
        "error_count": errors,
        "solver_error_count": sum(row.status == "solver_error" for row in results),
        "dry_run_count": sum(row.status == "dry_run" for row in results),
        "exact_challenge_accuracy": correct / evaluated if evaluated else None,
        "evaluation_coverage": evaluated / len(results) if results else None,
        "inference_sample_count": len(completed_inference),
        "mean_inference_time_ms": _mean(completed_inference),
        "median_inference_time_ms": _median(completed_inference),
        "p95_inference_time_ms": (
            sorted(completed_inference)[math.ceil(0.95 * len(completed_inference)) - 1]
            if completed_inference
            else None
        ),
        "mean_inference_attempt_time_ms": _mean(inference),
        "mean_total_time_ms": _mean(total),
        "median_total_time_ms": _median(total),
        "input_tokens": sum(input_tokens) if input_tokens else None,
        "output_tokens": sum(output_tokens) if output_tokens else None,
        "usage_complete": usage_complete,
        "estimated_api_request_count": sum(row.api_request_count for row in results),
        "estimated_cost_usd": cost,
        "p95_method": "nearest-rank",
    }
