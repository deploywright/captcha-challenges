# Zero-Shot Gemini 3.5 Flash Lite Baseline Report

Comprehensive baseline evaluation of **Gemini 3.5 Flash Lite** across the full held-out CAPTCHA benchmark (Levels 1, 2A, 2B, 3A, and 3B).

---

## 1. Executive Summary

This evaluation measures the zero-shot baseline capability of a modern, general-purpose commercial multimodal model (**`gemini-3.5-flash-lite`**) when confronted with the full CAPTCHA challenge suite with **zero training**, **zero fine-tuning**, **zero access to BDD100K training splits**, and **zero private benchmark access**.

- **Provider**: Google GenAI
- **Model**: `gemini-3.5-flash-lite`
- **Total Challenges**: 134
- **Coverage**: 100% (134 / 134 evaluated)
- **Execution Errors**: 0
- **Overall Micro Accuracy**: **43.28%** (58 / 134 correct)
- **Macro Level Accuracy**: **54.45%**
- **Macro Variant Accuracy**: **54.86%**

---

## 2. Top-Level Benchmark Results

| Level | Variant | Type | Challenges | Correct | Accuracy | Errors | Mean Inference |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Level 1** | `street-grid` | Image Selection | 20 | 14 | **70.0%** | 0 | 6.11 s |
| **Level 2A** | `hard-street-grid` | Image Selection | 20 | 10 | **50.0%** | 0 | 2.27 s |
| **Level 2B** | `checker-shadow` | Single Choice | 6 | 6 | **100.0%** | 0 | 1.45 s |
| **Level 3A** | `routing-puzzle` | Single Choice | 60 | 24 | **40.0%** | 0 | 1.56 s |
| **Level 3B** | `degraded-vision` | Image Selection | 28 | 4 | **14.29%** | 0 | 9.49 s |
| **Total / Overall** | — | — | **134** | **58** | **43.28%** | **0** | **2.97 s** |

*Note: Level 1 results represent the frozen canonical baseline from `results/20261002T085501003519Z_level1_vlm_30e5750e/`.*

---

## 3. Level 2B — Optical & Perceptual Illusions

Level 2B challenges evaluate whether visual models succumb to classical human optical illusions. While the human perceptual system falls prey to contrast and perspective context, the zero-shot VLM proved robust against all six canonical optical illusions.

| Subtype | Illusion Name | Challenge Question | Outcome | Inference Time |
| :--- | :--- | :--- | :---: | :---: |
| `cafe-wall` | Café Wall Illusion | *Are the horizontal mortar lines dividing the rows parallel?* | **Correct** (1/1) | 1.44 s |
| `checker-shadow` | Adelson Checker Shadow | *Are squares A and B the same shade?* | **Correct** (1/1) | 1.84 s |
| `ebbinghaus` | Ebbinghaus Illusion | *Are the two orange center circles the same size?* | **Correct** (1/1) | 1.25 s |
| `muller-lyer` | Müller-Lyer Illusion | *Are horizontal lines A and B the same length?* | **Correct** (1/1) | 1.74 s |
| `ponzo` | Ponzo Illusion | *Are horizontal bars A and B the same length?* | **Correct** (1/1) | 1.30 s |
| `simultaneous-contrast` | Simultaneous Contrast | *Are squares A and B the same shade of grey?* | **Correct** (1/1) | 1.13 s |
| **Level 2B Total** | **All 6 Canonical Illusions** | — | **6 / 6 (100.0%)** | **1.45 s** |

**Key Takeaway**: The multimodal model does not suffer from human psychophysical contrast adaptation, correctly verifying invariant geometric properties (parallelism, length, luminance, diameter).

---

## 4. Level 3A — Visual Routing Puzzles

Level 3A evaluates spatial tracing and visual graph routing across 4 distinct routing puzzle subtypes and 5 difficulty tiers.

### Breakdown by Subtype

| Subtype | Challenges | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: |
| **Pipe Flow** | 15 | 10 | **66.67%** | 1.83 s |
| **Conveyor Routing** | 15 | 6 | **40.00%** | 1.42 s |
| **Laser Maze** | 15 | 6 | **40.00%** | 1.62 s |
| **Device Cables** | 15 | 2 | **13.33%** | 1.54 s |
| **Total** | **60** | **24** | **40.00%** | **1.56 s** |

### Breakdown by Difficulty Tier

| Difficulty Tier | Challenges | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: |
| **Easy** | 8 | 7 | **87.50%** | 1.47 s |
| **Medium** | 12 | 5 | **41.67%** | 1.53 s |
| **Story Mode** | 20 | 7 | **35.00%** | 1.50 s |
| **Hard** | 12 | 5 | **41.67%** | 1.48 s |
| **Extreme** | 8 | 0 | **0.00%** | 2.01 s |

### Subtype × Difficulty Cross-Tabulation Matrix (Correct / Total)

| Subtype | Easy | Medium | Story | Hard | Extreme | Total Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Conveyor Routing** | 1 / 2 (50%) | 2 / 3 (67%) | 3 / 5 (60%) | 0 / 3 (0%) | 0 / 2 (0%) | **6 / 15 (40.0%)** |
| **Device Cables** | 1 / 2 (50%) | 0 / 3 (0%) | 1 / 5 (20%) | 0 / 3 (0%) | 0 / 2 (0%) | **2 / 15 (13.3%)** |
| **Laser Maze** | 2 / 2 (100%) | 1 / 3 (33%) | 0 / 5 (0%) | 2 / 3 (67%) | 1 / 2 (50%) | **6 / 15 (40.0%)** |
| **Pipe Flow** | 2 / 2 (100%) | 2 / 3 (67%) | 3 / 5 (60%) | 3 / 3 (100%) | 0 / 2 (0%) | **10 / 15 (66.7%)** |
| **Total** | **7 / 8 (87.5%)** | **5 / 12 (41.7%)** | **7 / 20 (35.0%)** | **5 / 12 (41.7%)** | **0 / 8 (0.0%)** | **24 / 60 (40.0%)** |

**Key Takeaways**:
1. **Easy Routing is Solvable**: At low path length and minimal decoys, the model succeeds on 87.5% of puzzles.
2. **Dense Tracing Fails**: Device Cables proved exceptionally difficult (13.33% accuracy), showing that tracing overlapping curvilinear paths is a major weakness for zero-shot attention.
3. **The Extreme Cliff**: On `extreme` difficulty, zero-shot Gemini achieved **0.0% accuracy** (0 / 8 correct). Long-horizon sequential tracing without programmatic path-following causes catastrophic error accumulation.

---

## 5. Level 3B — Degraded Vision (Resolution Ladder)

Level 3B tests semantic object recognition under severe visual degradation, stepping down from 64px to 8px across 4 unique image series.

### Performance by Resolution (Ladder)

| Tile Resolution | Challenges | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: |
| **64 × 64 px** | 4 | 1 | **25.0%** | 2.23 s |
| **48 × 48 px** | 4 | 2 | **50.0%** | 3.18 s |
| **32 × 32 px** | 4 | 1 | **25.0%** | 48.88 s* |
| **24 × 24 px** | 4 | 0 | **0.0%** | 3.83 s |
| **16 × 16 px** | 4 | 0 | **0.0%** | 2.23 s |
| **12 × 12 px** | 4 | 0 | **0.0%** | 2.76 s |
| **8 × 8 px** | 4 | 0 | **0.0%** | 3.32 s |
| **Total** | **28** | **4** | **14.29%** | **9.49 s** |

*\*Note: High mean inference at 32px includes provider retry backoff during quota pacing.*

### Performance by Image Series

| Series | Resolution Steps | Correct | Accuracy |
| :--- | :---: | :---: | :---: |
| **`series-01`** | 64, 48, 32, 24, 16, 12, 8 | 0 / 7 | **0.0%** |
| **`series-02`** | 64, 48, 32, 24, 16, 12, 8 | 3 / 7 | **42.86%** |
| **`series-03`** | 64, 48, 32, 24, 16, 12, 8 | 1 / 7 | **14.29%** |
| **`series-04`** | 64, 48, 32, 24, 16, 12, 8 | 0 / 7 | **0.0%** |

**Key Takeaway**:
- **Sharp Resolution Cutoff**: The model exhibits a steep capability cliff below 32px. For all tiles resized below 32×32 px (24px, 16px, 12px, 8px), zero-shot Gemini scored **0 / 16 (0.0% accuracy)**.
- While humans can recognize vehicles and road signs at 16–24px using low-frequency holistic shapes, current zero-shot VLM patch encoders fail to extract discriminative features from extreme low-resolution inputs.

---

## 6. Storytelling & Human-vs-AI Comparison Insights

For presentation, documentation, and YouTube video storytelling:

1. **The "Superhuman" Illusion Defense (Level 2B)**:
   - *Humans*: Strongly perceive the optical illusion (e.g. Square B looks lighter, lines look different lengths).
   - *Gemini*: Scores 100% (6/6). It directly perceives the pixel ground truth and remains impervious to human perceptual bias.
2. **The "Distracted Driver" Drop (Level 1 → Level 2A)**:
   - When moving from clean street scenes (`street-grid`: 70%) to adverse conditions like night, glare, and rain (`hard-street-grid`: 50%), the model loses 20 percentage points of accuracy.
3. **The "Maze Blindness" (Level 3A)**:
   - Simple mazes and pipe paths are easy (87.5%), but as soon as cables cross or paths require 5+ sequential branch choices, the AI drops to 0% on extreme challenges. Unlike humans who trace lines with their eyes or fingers, the model's global attention mechanism blurs dense paths.
4. **The "Pixelation Ceiling" (Level 3B)**:
   - A human with 20/20 vision can often guess "that's a bus" even on a 16px blurry icon. Gemini fails completely below 32px (0% across all 16 challenges).

---

## 7. Scientific Integrity & Protocol Guarantees

- **No Retries of Inaccurate Answers**: Every graded response was recorded on first attempt. Only network/quota transient errors were retried.
- **No Private Answer Leakage**: All challenges were fetched strictly via public HTTP endpoints (`/challenges/catalog.json`, `/challenges/<id>/challenge.json`, `/challenges/<id>/assets/*`).
- **Held-Out Split**: All BDD100K challenges in the benchmark derive from `source_split = "val"`, completely isolated from any potential training data.
- **Frozen Canonical Level 1**: Preserved exact 14 / 20 (70.0%) result from the verified baseline run.
- **Run Artifacts Available**:
  - Level 1: `results/20261002T085501003519Z_level1_vlm_30e5750e/`
  - Level 2A: `results/20261002T101240698279Z_hard_street_grid_vlm_dffa1758/`
  - Level 2B: `results/20261002T101455913741Z_checker_shadow_vlm_cd021901/`
  - Level 3A: `results/20261002T101524234508Z_routing_puzzle_vlm_13d329b9/`
  - Level 3B: `results/20261002T102307601966Z_degraded_vision_vlm_9bfa68f1/`
