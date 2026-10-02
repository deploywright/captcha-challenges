# AI-Solver Zero-Shot Gemini Baseline Verification Report

Verified on 2026-10-02. The independent package, test suite, and complete held-out benchmark
evaluation sequence are verified and complete: **Gemini 3.5 Flash-Lite evaluated all 134 dynamically
discovered challenges across all five benchmark stages (Levels 1, 2A, 2B, 3A, and 3B): 60 correct,
74 incorrect, zero execution errors (100% evaluation coverage, 0 errors)**.

Overall Micro Accuracy across the 134 held-out benchmark challenges is **44.78%** (60 / 134), and
the Five-Stage Macro Accuracy is **55.81%**.

All challenge evaluations were conducted strictly via public HTTP endpoints (`/challenges/catalog.json`,
`/challenges/<id>/challenge.json`, `/challenges/<id>/assets/*`). No training, fine-tuning, few-shot
demonstrations, programmatic vision tools, or private answer access occurred. All code, configs, tests,
and reports are isolated inside `AI-Solver/`.

---

## 1. Verified Results Across All Stages

| Stage | Variant | Challenge Type | Evaluated | Correct | Accuracy | Errors | Mean Latency | Raw Run Directory |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Level 1** | `street-grid` | Image Selection | 20 | 14 | **70.0%** | 0 | 6.11 s | `results/20261002T085501003519Z_level1_vlm_30e5750e` |
| **Level 2A** | `hard-street-grid` | Image Selection | 20 | 11 | **55.0%** | 0 | 9.01 s | `results/20261002T112508284295Z_hard_street_grid_vlm_45223726` |
| **Level 2B** | `checker-shadow` | Single Choice | 6 | 6 | **100.0%** | 0 | 2.21 s | `results/20261002T112945860317Z_checker_shadow_vlm_63c123c8` |
| **Level 3A** | `routing-puzzle` | Single Choice | 60 | 26 | **43.3%** | 0 | 4.00 s | `results/20261002T113010612141Z_routing_puzzle_vlm_a2ae8ad8` |
| **Level 3B** | `degraded-vision` | Image Selection | 28 | 3 | **10.7%** | 0 | 10.89 s | `results/20261002T113705651955Z_degraded_vision_vlm_8f635ab3` |
| **Total** | — | — | **134** | **60** | **44.8%** | **0** | **6.42 s** | — |

*Note: Level 1 results reflect the frozen canonical historical baseline run (14 / 20 = 70.0%). Levels 2A, 2B, 3A, and 3B reflect the normalized rerun under explicit `ThinkingLevel.MINIMAL`.*

---

## 2. Granular Stage Breakdown

### Level 2B — Optical & Perceptual Illusions (N=6)
- **Results**: 6 / 6 correct (100.0%), mean latency 2.21 s.
- **Subtypes**: `cafe-wall` (1/1), `checker-shadow` (1/1), `ebbinghaus` (1/1), `muller-lyer` (1/1), `ponzo` (1/1), `simultaneous-contrast` (1/1).
- **Methodological Context**: Each illusion subtype currently contains one evaluated challenge (N=1 per subtype). This result should not be interpreted as a general estimate of performance on visual illusions or as evidence regarding the model's internal perceptual mechanisms. These canonical illusions are widely published and likely present in web pretraining data.

### Level 3A — Visual Routing Puzzles (N=60)
- **Results**: 26 / 60 correct (43.3%), mean latency 4.00 s.
- **By Subtype**:
  - Pipe Flow: 9 / 15 correct (60.0%)
  - Conveyor Routing: 9 / 15 correct (60.0%)
  - Laser Maze: 4 / 15 correct (26.7%)
  - Device Cables: 4 / 15 correct (26.7%)
- **By Difficulty**:
  - Easy: 6 / 8 correct (75.0%)
  - Medium: 3 / 12 correct (25.0%)
  - Story: 7 / 20 correct (35.0%)
  - Hard: 6 / 12 correct (50.0%)
  - Extreme: 4 / 8 correct (50.0%)

### Level 3B — Degraded Vision Ladder (N=28)
- **Results**: 3 / 28 correct (10.7%), mean latency 10.89 s.
- **By Resolution**:
  - 64 × 64 px: 1 / 4 (25.0%)
  - 48 × 48 px: 1 / 4 (25.0%)
  - 32 × 32 px: 1 / 4 (25.0%)
  - 24 × 24 px: 0 / 4 (0.0%)
  - 16 × 16 px: 0 / 4 (0.0%)
  - 12 × 12 px: 0 / 4 (0.0%)
  - 8 × 8 px: 0 / 4 (0.0%)
- **By Series**:
  - `series-01`: 0 / 7 (0.0%)
  - `series-02`: 3 / 7 (42.9%)
  - `series-03`: 0 / 7 (0.0%)
  - `series-04`: 0 / 7 (0.0%)

---

## 3. Package Structure and Verification Files

All benchmark and baseline components reside within `AI-Solver/`:

- **Configuration & Runner**:
  - `src/ai_solver/config.py`: Single validated `variant` definition supporting all five variants and `all`.
  - `src/ai_solver/contracts.py`: Public schema validators, zero-based index validators, single-choice option validators, leak detectors.
  - `src/ai_solver/client.py`: Public HTTP client with asset caching and status tracking.
  - `src/ai_solver/runner.py`: Benchmark runner with per-variant pacing, quota backoff, and resumability.
  - `src/ai_solver/metrics.py`: Computes micro accuracy, `by_stage`, five-stage `macro_stage_accuracy`, and granular slices.
  - `src/ai_solver/reporting.py`: Programmatic report generator producing structured Markdown from JSON metrics.
  - `run_benchmark_pipeline.py`: Reproducible pipeline script for executing and aggregating the benchmark.
- **Solvers**:
  - `src/ai_solver/solvers/gemini.py`: Google GenAI adapter using `gemini-3.5-flash-lite` with normalized `ThinkingLevel.MINIMAL`, strict JSON schema, tools/AFC disabled.
  - `src/ai_solver/solvers/level_1_vlm.py`: Provider-agnostic multimodal prompt and solver orchestrator supporting image-selection and single-choice challenges.
  - `src/ai_solver/solvers/random_baseline.py`: Deterministic pseudo-random baseline for control comparison.
- **Canonical Reports & Artifacts**:
  - `reports/gemini-zero-shot-baseline.json`: Full structured JSON metrics for the baseline.
  - `reports/gemini-zero-shot-baseline.md`: Programmatically generated Markdown report with cross-tabulation matrices.

---

## 4. Test Suite and Static Analysis

The test suite thoroughly verifies all solver contracts, adapters, metric calculations, and report generation:

```bash
uv run pytest
# 157 passed, 1 skipped (opt-in public network integration test)

uv run ruff check .
# All checks passed!

uv run ruff format --check .
# 27 files already formatted
```

The live public network integration test was executed and verified:

```bash
uv run pytest tests/test_integration.py -s
# Public integration: 20 street-grid challenges; 180 assets
# 1 passed in 46.35s
```

---

## 5. Scientific Protocol Guarantees

1. **Zero-Shot Protocol**: No solver-specific training, fine-tuning, few-shot examples, or prompt engineering from graded feedback was used. Prompts were frozen before evaluation (`image-selection-v1`, `single-choice-v1`).
2. **Public-Only Interface**: All challenges and assets were retrieved strictly via public HTTP endpoints. No internal challenge generators, ground-truth label files (`answer.json`), or secret keys were accessed.
3. **No Retries of Graded Failures**: Predictions were submitted exactly once per challenge. Transport and rate-limit errors were handled strictly at the provider API boundary with exponential backoff.
4. **Canonical Level 1 Preservation**: The Level 1 baseline was preserved without post-hoc cherry-picking or rerun (14 / 20 = 70.0%).
5. **Programmatic Reporting**: All figures in `gemini-zero-shot-baseline.md` derive deterministically from `gemini-zero-shot-baseline.json` via `ai_solver.reporting`.
