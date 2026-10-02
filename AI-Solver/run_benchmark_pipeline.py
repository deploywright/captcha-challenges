"""Orchestrates the normalized zero-shot Gemini baseline benchmark execution."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ai_solver.client import BenchmarkClient
from ai_solver.config import RunConfig
from ai_solver.contracts import ChallengeResult
from ai_solver.metrics import aggregate_metrics
from ai_solver.reporting import update_report_files
from ai_solver.runner import BenchmarkRunner
from ai_solver.solvers.gemini import GeminiVisionProvider
from ai_solver.solvers.level_1_vlm import Level1VLMSolver

BASE_DIR = Path(__file__).resolve().parent

STAGES = [
    {
        "variant": "hard-street-grid",
        "stage_name": "Level 2A (hard-street-grid)",
        "request_interval_seconds": 1.5,
        "max_retries": 4,
    },
    {
        "variant": "checker-shadow",
        "stage_name": "Level 2B (checker-shadow)",
        "request_interval_seconds": 1.0,
        "max_retries": 4,
    },
    {
        "variant": "routing-puzzle",
        "stage_name": "Level 3A (routing-puzzle)",
        "request_interval_seconds": 2.0,
        "max_retries": 4,
    },
    {
        "variant": "degraded-vision",
        "stage_name": "Level 3B (degraded-vision)",
        "request_interval_seconds": 1.5,
        "max_retries": 4,
    },
]

CANONICAL_LEVEL1_DIR = BASE_DIR / "results" / "20261002T085501003519Z_level1_vlm_30e5750e"


def main() -> int:
    load_dotenv(BASE_DIR / ".env")
    base_url = os.environ.get(
        "CAPTCHA_BASE_URL", "https://captcha-challenges-web.deploywright.workers.dev"
    )
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        return 1

    print("==================================================================")
    print("  GEMINI 3.5 FLASH-LITE ZERO-SHOT BASELINE BENCHMARK EXECUTION  ")
    print("==================================================================")
    print(f"Base URL: {base_url}")
    print("Thinking Level: MINIMAL")
    print(f"Canonical Level 1 Run: {CANONICAL_LEVEL1_DIR.relative_to(BASE_DIR)}")
    print("------------------------------------------------------------------")

    run_dirs: dict[str, Path] = {
        "Level 1 (street-grid)": CANONICAL_LEVEL1_DIR,
    }

    # Run remaining stages sequentially
    for stage in STAGES:
        variant = stage["variant"]
        stage_name = stage["stage_name"]
        interval = stage["request_interval_seconds"]
        retries = stage["max_retries"]

        print(f"\n>>> Starting Stage: {stage_name} (variant={variant})")
        config = RunConfig(
            base_url=base_url,
            variant=variant,
            provider="gemini",
            model="gemini-3.5-flash-lite",
            timeout=30.0,
            max_retries=retries,
            request_interval_seconds=interval,
            dry_run=False,
            resume=False,
            output_dir=BASE_DIR / "results",
        )

        provider = GeminiVisionProvider(
            config.model,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        solver = Level1VLMSolver(provider)

        with BenchmarkClient(
            config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        ) as client:
            runner = BenchmarkRunner(
                client,
                solver,
                config,
                progress=lambda msg, v=variant: print(f"[{v}] {msg}", file=sys.stderr),
            )
            output_dir, summary = runner.run()

        corr = summary["correct_count"]
        ev = summary["evaluated_count"]
        acc = summary["exact_challenge_accuracy"]
        acc_pct = f"{acc * 100:.1f}%" if acc is not None else "N/A"
        errs = summary["error_count"]
        print(f"Completed {stage_name}: Output -> {output_dir.relative_to(BASE_DIR)}")
        print(f"Summary: {corr}/{ev} correct ({acc_pct}), {errs} errors")

        if errs > 0:
            print(f"WARNING: Stage {stage_name} had {errs} errors!", file=sys.stderr)

        run_dirs[stage_name] = output_dir

    print("\n------------------------------------------------------------------")
    print("All benchmark stages executed. Aggregating results...")

    # Load canonical Level 1 results
    all_results: list[ChallengeResult] = []
    l1_pred_file = CANONICAL_LEVEL1_DIR / "predictions.jsonl"
    if not l1_pred_file.exists():
        print(f"ERROR: Canonical Level 1 file not found: {l1_pred_file}", file=sys.stderr)
        return 1

    for line in l1_pred_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            all_results.append(ChallengeResult.model_validate_json(line))
    print(f"Loaded {len(all_results)} canonical Level 1 predictions.")

    # Load predictions from each stage
    for stage in STAGES:
        stage_name = stage["stage_name"]
        pred_file = run_dirs[stage_name] / "predictions.jsonl"
        stage_count = 0
        for line in pred_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                all_results.append(ChallengeResult.model_validate_json(line))
                stage_count += 1
        print(f"Loaded {stage_count} predictions from {stage_name}.")

    print(f"Total aggregated predictions: {len(all_results)}")
    if len(all_results) != 134:
        print(f"WARNING: Expected 134 predictions, found {len(all_results)}!", file=sys.stderr)

    # Compute aggregate metrics
    metrics = aggregate_metrics(all_results)

    # Build report data
    report_data = {
        "benchmark": "CAPTCHA-Challenges Commercial VLM Baseline",
        "provider": "Google GenAI",
        "model": "gemini-3.5-flash-lite",
        "thinking_level": "MINIMAL",
        "mode": "zero-shot",
        "total_challenges": 134,
        "evaluated_challenges": len(all_results),
        "correct_challenges": sum(r.correct is True for r in all_results),
        "incorrect_challenges": sum(r.correct is False for r in all_results),
        "error_count": sum(r.status != "evaluated" or r.error is not None for r in all_results),
        "micro_accuracy": metrics["exact_challenge_accuracy"],
        "macro_stage_accuracy": metrics["macro_stage_accuracy"],
        "macro_level_accuracy": metrics.get("macro_level_accuracy"),
        "macro_variant_accuracy": metrics.get("macro_variant_accuracy"),
        "run_artifacts": {
            label: str(p.relative_to(BASE_DIR).as_posix()) for label, p in run_dirs.items()
        },
        "metrics": metrics,
    }

    # Write JSON report
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "gemini-zero-shot-baseline.json"
    md_path = reports_dir / "gemini-zero-shot-baseline.md"

    json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Wrote structured baseline JSON -> {json_path}")

    # Generate Markdown report
    update_report_files(json_path, md_path)
    print(f"Generated Markdown report -> {md_path}")

    print("\n==================================================================")
    print("  FINAL AGGREGATE BASELINE SUMMARY")
    print("==================================================================")
    print(f"Total Evaluated: {report_data['evaluated_challenges']} / 134")
    print(f"Total Correct:   {report_data['correct_challenges']}")
    print(f"Micro Accuracy:  {report_data['micro_accuracy'] * 100:.2f}%")
    print(f"Macro Accuracy:  {report_data['macro_stage_accuracy'] * 100:.2f}%")
    for stage_name, s_data in metrics.get("by_stage", {}).items():
        acc = s_data.get("exact_challenge_accuracy")
        acc_str = f"{acc * 100:.1f}%" if acc is not None else "N/A"
        c_cnt = s_data.get("correct_count", 0)
        tot_cnt = s_data.get("challenge_count", 0)
        print(f"  {stage_name:12}: {c_cnt}/{tot_cnt} ({acc_str})")
    print("==================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
