"""Exact challenge outcomes only; no hidden per-tile labels are available."""

import math
import statistics

from .contracts import ChallengeResult


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


STAGE_MAPPING: dict[str, str] = {
    "street-grid": "Level 1",
    "hard-street-grid": "Level 2A",
    "checker-shadow": "Level 2B",
    "routing-puzzle": "Level 3A",
    "degraded-vision": "Level 3B",
}


def _group_summary(subset: list[ChallengeResult]) -> dict:
    correct = sum(row.correct is True for row in subset)
    incorrect = sum(row.correct is False for row in subset)
    evaluated = correct + incorrect
    completed_inference = [
        row.inference_time_ms
        for row in subset
        if row.prediction is not None and row.inference_time_ms is not None
    ]
    return {
        "challenge_count": len(subset),
        "evaluated_count": evaluated,
        "correct_count": correct,
        "incorrect_count": incorrect,
        "exact_challenge_accuracy": correct / evaluated if evaluated else None,
        "mean_inference_time_ms": _mean(completed_inference),
        "median_inference_time_ms": _median(completed_inference),
    }


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

    by_level: dict[int, dict] = {}
    for level in sorted({row.level for row in results}):
        by_level[level] = _group_summary([row for row in results if row.level == level])

    by_variant: dict[str, dict] = {}
    for variant in sorted({row.variant for row in results}):
        by_variant[variant] = _group_summary([row for row in results if row.variant == variant])

    by_subtype: dict[str, dict] = {}
    subtypes = sorted({row.subtype for row in results if row.subtype is not None})
    for st in subtypes:
        by_subtype[st] = _group_summary([row for row in results if row.subtype == st])

    by_difficulty: dict[str, dict] = {}
    diffs = sorted({row.difficulty for row in results if row.difficulty is not None})
    for df in diffs:
        by_difficulty[df] = _group_summary([row for row in results if row.difficulty == df])

    by_resolution: dict[int, dict] = {}
    resolutions = sorted({row.resolution for row in results if row.resolution is not None})
    for res in resolutions:
        by_resolution[res] = _group_summary([row for row in results if row.resolution == res])

    by_series: dict[str, dict] = {}
    series_ids = sorted({row.series_id for row in results if row.series_id is not None})
    for s_id in series_ids:
        by_series[s_id] = _group_summary([row for row in results if row.series_id == s_id])

    subtype_by_difficulty: dict[str, dict[str, dict]] = {}
    for st in subtypes:
        st_rows = [row for row in results if row.subtype == st]
        st_diffs = sorted({row.difficulty for row in st_rows if row.difficulty is not None})
        if st_diffs:
            subtype_by_difficulty[st] = {
                df: _group_summary([row for row in st_rows if row.difficulty == df])
                for df in st_diffs
            }

    by_stage: dict[str, dict] = {}
    for variant, stage_name in STAGE_MAPPING.items():
        stage_rows = [row for row in results if row.variant == variant]
        if stage_rows:
            by_stage[stage_name] = _group_summary(stage_rows)

    stage_accuracies = [
        s["exact_challenge_accuracy"]
        for s in by_stage.values()
        if s["exact_challenge_accuracy"] is not None
    ]
    macro_stage_accuracy = _mean(stage_accuracies)

    level_accuracies = [
        s["exact_challenge_accuracy"]
        for s in by_level.values()
        if s["exact_challenge_accuracy"] is not None
    ]
    variant_accuracies = [
        s["exact_challenge_accuracy"]
        for s in by_variant.values()
        if s["exact_challenge_accuracy"] is not None
    ]

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
        "by_stage": by_stage,
        "macro_stage_accuracy": macro_stage_accuracy,
        "by_numeric_level": by_level,
        "by_level": by_level,
        "by_variant": by_variant,
        "by_subtype": by_subtype,
        "by_difficulty": by_difficulty,
        "by_resolution": by_resolution,
        "by_series": by_series,
        "subtype_by_difficulty": subtype_by_difficulty,
        "macro_level_accuracy": _mean(level_accuracies),
        "macro_variant_accuracy": _mean(variant_accuracies),
    }
