# Gemini 3.1 Flash-Lite Baseline Report — Level 3A (Visual Routing Puzzles)

Evaluation of **`gemini-3.1-flash-lite`** on the redesigned held-out CAPTCHA Level 3A benchmark (60 challenges).

---

## 1. Executive Summary

- **Provider**: Google GenAI
- **Model**: `gemini-3.1-flash-lite`
- **Benchmark Stage**: Level 3A — Routing Puzzles (`routing-puzzle`)
- **Total Challenges**: 60
- **Evaluated**: 60 / 60 (100.0%)
- **Execution Errors**: 0 (100% clean run)
- **Exact Challenge Accuracy**: **28.33%** (17 / 60 correct)
- **Token Efficiency**: 72,652 input tokens, 1,200 output tokens (average ~20 tokens/challenge, 0 token exhaustion)
- **Mean Inference Time**: 6.29 seconds per challenge
- **Run ID**: `20261003T134401595186Z_routing_puzzle_vlm_13406160`

---

## 2. Accuracy by Routing Subtype

| Subtype | Challenges | Evaluated | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pipe Flow** | 15 | 15 | 11 | **73.33%** | 5.83 s |
| **Laser Maze** | 15 | 15 | 2 | **13.33%** | 6.54 s |
| **Device Cables** | 15 | 15 | 2 | **13.33%** | 6.97 s |
| **Conveyor Routing** | 15 | 15 | 2 | **13.33%** | 5.50 s |
| **Total** | **60** | **60** | **17** | **28.33%** | **6.29 s** |

---

## 3. Accuracy by Difficulty Tier

| Difficulty Tier | Challenges | Evaluated | Correct | Accuracy | Mean Inference Time |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Easy** | 8 | 8 | 3 | **37.50%** | 5.42 s |
| **Medium** | 12 | 12 | 6 | **50.00%** | 5.48 s |
| **Story** | 20 | 20 | 4 | **20.00%** | 7.75 s |
| **Hard** | 12 | 12 | 4 | **33.33%** | 6.33 s |
| **Extreme** | 8 | 8 | 0 | **0.00%** | 4.65 s |
| **Total** | **60** | **60** | **17** | **28.33%** | **6.29 s** |

---

## 4. Subtype × Difficulty Cross-Tabulation Matrix (Correct / Total)

| Subtype | Easy | Medium | Story | Hard | Extreme | Subtype Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pipe Flow** | 1 / 2 (50%) | 3 / 3 (100%) | 4 / 5 (80%) | 3 / 3 (100%) | 0 / 2 (0%) | **11 / 15 (73.3%)** |
| **Laser Maze** | 0 / 2 (0%) | 2 / 3 (67%) | 0 / 5 (0%) | 0 / 3 (0%) | 0 / 2 (0%) | **2 / 15 (13.3%)** |
| **Device Cables** | 1 / 2 (50%) | 0 / 3 (0%) | 0 / 5 (0%) | 1 / 3 (33%) | 0 / 2 (0%) | **2 / 15 (13.3%)** |
| **Conveyor Routing** | 1 / 2 (50%) | 1 / 3 (33%) | 0 / 5 (0%) | 0 / 3 (0%) | 0 / 2 (0%) | **2 / 15 (13.3%)** |
| **Total** | **3 / 8 (37.5%)** | **6 / 12 (50.0%)** | **4 / 20 (20.0%)** | **4 / 12 (33.3%)** | **0 / 8 (0.0%)** | **17 / 60 (28.3%)** |

---

## 5. Key Findings & Analysis

1. **Difficulty Progression is Highly Effective**:
   - The redesigned Story difficulty proved substantially harder than Easy/Medium, dropping Gemini 3.1 Flash-Lite's accuracy to **20.0%** (4/20).
   - In **Extreme** difficulty, accuracy was completely neutralized at **0.0%** (0/8).
2. **Subtype Vulnerability**:
   - Laser Maze, Device Cables, and Conveyor Routing proved nearly impenetrable for zero-shot spatial tracing, each holding the model to only **13.3%** accuracy (barely above random baseline of ~10-15%).
   - Pipe Flow had higher recognition (73.3%) on straightforward junctions, but failed on Extreme junctions.
3. **Execution Reliability**:
   - 0 errors, 100% coverage, and clean JSON responses throughout without hitting rate limits or token exhaustion.
