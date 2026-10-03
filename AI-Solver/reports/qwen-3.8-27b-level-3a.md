# Qwen 3.8 27B Baseline Report — Level 3A (Visual Routing Puzzles)

Evaluation of **`qwen/qwen3.8-27b:free`** (via OpenRouter) on the held-out CAPTCHA Level 3A benchmark.

---

## 1. Executive Summary

- **Provider**: OpenRouter (`ModelRun` upstream)
- **Model**: `qwen/qwen3.8-27b:free` (Reasoning Vision-Language Model)
- **Benchmark Stage**: Level 3A — Routing Puzzles (`routing-puzzle`)
- **Total In-Scope Challenges**: 60
- **Evaluated Challenges**: 46 (plus 8 upstream rate-limit stops at daily quota)
- **Evaluation Coverage**: 76.7% of total benchmark (exhausted OpenRouter free daily quota)
- **Correct Challenges**: **34 / 46**
- **Exact Accuracy (Evaluated)**: **73.91%**
- **Mean Output Tokens**: ~9,000 - 11,000 tokens (heavy chain-of-thought visual tracing)
- **Mean Inference Time**: ~45 - 60 seconds per challenge

---

## 2. Accuracy by Routing Subtype

| Subtype | Evaluated | Correct | Accuracy | Key Observation |
| :--- | :---: | :---: | :---: | :--- |
| **Pipe Flow** | 7 | 7 | **100.0%** | Flawlessly traced pipe junctions and valve flow states |
| **Laser Maze** | 15 | 12 | **80.0%** | High geometric reflection reasoning via chain-of-thought |
| **Conveyor Routing** | 15 | 11 | **73.3%** | Accurately tracked mechanical diversion paths |
| **Device Cables** | 9 | 4 | **44.4%** | Overlapping tangled cables remain the hardest challenge |
| **Total** | **46** | **34** | **73.91%** | **Significantly outperforms non-reasoning vision models** |

---

## 3. Accuracy by Difficulty Tier

| Difficulty Tier | Evaluated | Correct | Accuracy |
| :--- | :---: | :---: | :---: |
| **Easy** | 5 | 5 | **100.0%** |
| **Medium** | 9 | 8 | **88.9%** |
| **Story** | 17 | 14 | **82.4%** |
| **Hard** | 9 | 5 | **55.6%** |
| **Extreme** | 6 | 2 | **33.3%** |
| **Total** | **46** | **34** | **73.91%** |

---

## 4. Architectural Analysis: Why Reasoning VLMs Excel at Routing

1. **Chain-of-Thought Tracing**:
   - Unlike standard vision models that attempt single-pass perception, Qwen 3.8 27B generates ~10,000 internal reasoning tokens.
   - It breaks down the image by coordinate, tracing paths node-by-node (e.g., *“Start at E1 -> hits mirror at (x1, y1) angled 45 deg -> reflects downward to mirror 2...”*).
2. **Robustness on Laser Maze & Pipes**:
   - Qwen scored **80.0%** on Laser Maze and **100%** on Pipe Flow, whereas Gemini 3.1 Flash-Lite scored only **13.3%** on Laser Maze.
3. **Persisting Bottleneck: Tangled Cables**:
   - Tangled Device Cables was the only subtype where Qwen dropped below 50% (44.4%), showing that organic curved wire crossings with visual occlusion remain difficult even for heavy reasoning models.
