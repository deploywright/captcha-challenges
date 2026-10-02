# Zero-Shot Gemini 3.5 Flash Lite Baseline Report

Definitive baseline evaluation of **gemini-3.5-flash-lite** across the full held-out CAPTCHA benchmark (Levels 1, 2A, 2B, 3A, and 3B).

---

## 1. Executive Summary

This evaluation measures the zero-shot baseline capability of a general-purpose commercial multimodal model when evaluated across the complete CAPTCHA challenge suite under normalized inference parameters.

- **Provider**: Google GenAI
- **Model**: `gemini-3.5-flash-lite`
- **Thinking Level**: `MINIMAL`
- **Mode**: Zero-shot (no solver-specific training, no fine-tuning)
- **Total Challenges**: 134
- **Coverage**: 134 / 134 evaluated (100.00%)
- **Execution Errors**: 0
- **Overall Micro Accuracy**: **44.78%** (60 / 134 correct)
- **Macro Stage Accuracy**: **55.81%**

---

## 2. Top-Level Benchmark Results

| Stage | Variant | Type | Challenges | Correct | Accuracy | Errors | Mean Inference |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Level 1** | `street-grid` | Image Selection | 20 | 14 | **70.0%** | 0 | 6.11 s |
| **Level 2A** | `hard-street-grid` | Image Selection | 20 | 11 | **55.0%** | 0 | 9.01 s |
| **Level 2B** | `checker-shadow` | Single Choice | 6 | 6 | **100.0%** | 0 | 2.21 s |
| **Level 3A** | `routing-puzzle` | Single Choice | 60 | 26 | **43.3%** | 0 | 4.00 s |
| **Level 3B** | `degraded-vision` | Image Selection | 28 | 3 | **10.7%** | 0 | 10.89 s |
| **Total / Overall** | — | — | **134** | **60** | **44.8%** | **0** | **6.42 s** |

*Note: Level 1 results reflect the frozen canonical baseline run (14 / 20 = 70.0%).*

---

## 3. Level 2B — Optical & Perceptual Illusions

Level 2B challenges evaluate whether visual models succumb to classical human optical illusions. Each subtype in this benchmark contains one evaluated challenge (N=1 per subtype).

| Subtype | Challenge Question | Outcome | Inference Time |
| :--- | :--- | :---: | :---: |
| `cafe-wall` | *Are the horizontal mortar lines dividing the rows parallel?* | **Correct (1/1)** | 7.01 s |
| `checker-shadow` | *Are squares A and B the same shade?* | **Correct (1/1)** | 1.51 s |
| `ebbinghaus` | *Are the two orange center circles the same size?* | **Correct (1/1)** | 1.03 s |
| `muller-lyer` | *Are horizontal lines A and B the same length?* | **Correct (1/1)** | 1.15 s |
| `ponzo` | *Are horizontal bars A and B the same length?* | **Correct (1/1)** | 1.36 s |
| `simultaneous-contrast` | *Are squares A and B the same shade of grey?* | **Correct (1/1)** | 1.23 s |

**Context & Interpretation**: Gemini answered all six illusion challenges correctly in this benchmark. Each subtype currently contains one evaluated challenge, so this result should not be interpreted as a general estimate of performance on optical illusions or as evidence about the internal perceptual mechanism used by the model. These canonical visual illusions are widely published and may be represented in general model pretraining data.

---

## 4. Level 3A — Visual Routing Puzzles

Level 3A evaluates spatial tracing and visual graph routing across 4 distinct routing puzzle subtypes and 5 difficulty tiers (60 challenges total).

### Breakdown by Subtype

| Subtype | Challenges | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: |
| **Pipe Flow** | 15 | 9 | **60.00%** | 2.71 s |
| **Conveyor Routing** | 15 | 9 | **60.00%** | 6.69 s |
| **Laser Maze** | 15 | 4 | **26.67%** | 2.86 s |
| **Device Cables** | 15 | 4 | **26.67%** | 3.74 s |

### Breakdown by Difficulty Tier

| Difficulty Tier | Challenges | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: |
| **Easy** | 8 | 6 | **75.00%** | 5.90 s |
| **Medium** | 12 | 3 | **25.00%** | 4.05 s |
| **Story** | 20 | 7 | **35.00%** | 3.92 s |
| **Hard** | 12 | 6 | **50.00%** | 2.88 s |
| **Extreme** | 8 | 4 | **50.00%** | 3.91 s |

### Subtype × Difficulty Cross-Tabulation Matrix (Correct / Total)

| Subtype | Easy | Medium | Story | Hard | Extreme | Total Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Conveyor Routing** | 2 / 2 (100%) | 1 / 3 (33%) | 2 / 5 (40%) | 2 / 3 (67%) | 2 / 2 (100%) | **9 / 15 (60.0%)** |
| **Device Cables** | 1 / 2 (50%) | 0 / 3 (0%) | 2 / 5 (40%) | 0 / 3 (0%) | 1 / 2 (50%) | **4 / 15 (26.7%)** |
| **Laser Maze** | 2 / 2 (100%) | 0 / 3 (0%) | 0 / 5 (0%) | 1 / 3 (33%) | 1 / 2 (50%) | **4 / 15 (26.7%)** |
| **Pipe Flow** | 1 / 2 (50%) | 2 / 3 (67%) | 3 / 5 (60%) | 3 / 3 (100%) | 0 / 2 (0%) | **9 / 15 (60.0%)** |
| **Total** | **6 / 8 (75.0%)** | **3 / 12 (25.0%)** | **7 / 20 (35.0%)** | **6 / 12 (50.0%)** | **4 / 8 (50.0%)** | **26 / 60 (43.3%)** |

---

## 5. Level 3B — Degraded Vision (Resolution Ladder)

Level 3B tests semantic object recognition under stepped visual degradation, stepping down from 64px to 8px across 4 unique image series (28 challenges total).

### Performance by Resolution (Ladder)

| Tile Resolution | Challenges | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: |
| **64 × 64 px** | 4 | 1 | **25.0%** | 2.90 s |
| **48 × 48 px** | 4 | 1 | **25.0%** | 3.12 s |
| **32 × 32 px** | 4 | 1 | **25.0%** | 5.36 s |
| **24 × 24 px** | 4 | 0 | **0.0%** | 3.30 s |
| **16 × 16 px** | 4 | 0 | **0.0%** | 4.03 s |
| **12 × 12 px** | 4 | 0 | **0.0%** | 3.06 s |
| **8 × 8 px** | 4 | 0 | **0.0%** | 54.45 s |

### Performance by Image Series

| Series | Resolution Steps | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: |
| **`series-01`** | 7 | 0 | **0.00%** | 17.23 s |
| **`series-02`** | 7 | 3 | **42.86%** | 20.05 s |
| **`series-03`** | 7 | 0 | **0.00%** | 3.46 s |
| **`series-04`** | 7 | 0 | **0.00%** | 2.82 s |

---

## 6. Descriptive Summary

- **Highest measured stage accuracy**: Level 2B (100.00%)
- **Lowest measured stage accuracy**: Level 3B (10.71%)
- **Largest stage-to-stage accuracy drop**: Level 2B -> Level 3A (56.7 percentage points)
- **Routing subtype with highest measured accuracy**: pipe-flow (60.00%)
- **Routing subtype with lowest measured accuracy**: laser-maze (26.67%)
- **Lowest resolution with at least one correct challenge**: 32x32 px

---

## 7. Scientific Integrity & Protocol Guarantees

- **Zero-Shot Protocol**: No model fine-tuning, few-shot demonstration, prompt engineering from graded feedback, or programmatic vision tools were used.
- **Held-Out Benchmark Split**: BDD100K validation data was held out from our solver-specific training and fine-tuning pipeline. No solver-specific training was performed in this baseline.
- **No Answer Leakage**: All challenges were fetched strictly via public HTTP endpoints (`/challenges/catalog.json`, `/challenges/<id>/challenge.json`, `/challenges/<id>/assets/*`). Server feedback was restricted to submission status codes and boolean outcome.
- **Frozen Canonical Level 1**: Preserved historical canonical result (14 / 20 = 70.0%) from `results/20261002T085501003519Z_level1_vlm_30e5750e/`.
- **No Retries of Inaccurate Answers**: Predictions were submitted exactly once per challenge. Transport and quota errors were retried strictly at the provider boundary using exponential backoff.
- **Raw Run Artifacts**:
  - Level 1 (street-grid): `results/20261002T085501003519Z_level1_vlm_30e5750e`
  - Level 2A (hard-street-grid): `results/20261002T112508284295Z_hard_street_grid_vlm_45223726`
  - Level 2B (checker-shadow): `results/20261002T112945860317Z_checker_shadow_vlm_63c123c8`
  - Level 3A (routing-puzzle): `results/20261002T113010612141Z_routing_puzzle_vlm_a2ae8ad8`
  - Level 3B (degraded-vision): `results/20261002T113705651955Z_degraded_vision_vlm_8f635ab3`
