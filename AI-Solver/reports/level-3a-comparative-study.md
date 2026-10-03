# Level 3A Routing Puzzles — Multi-Model Comparative Evaluation

Comparative analysis of multimodal models on the held-out CAPTCHA Level 3A (Visual Routing Puzzles) benchmark:
1. **Gemini 3.1 Flash-Lite** (Google GenAI, Fast Non-Reasoning Vision)
2. **Gemini 3.5 Flash-Lite** (Google GenAI, Minimal Reasoning Baseline)
3. **Qwen 3.8 27B** (OpenRouter, Deep Reasoning VLM with Chain-of-Thought)

---

## 1. Top-Level Comparison

| Model | Architecture | Provider | Evaluated | Correct | Exact Accuracy | Mean Inference Time | Token Usage / Query |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Qwen 3.8 27B** | Reasoning Vision | OpenRouter (free) | 46 | 34 | **73.91%** | 52.4 s | ~10,000 output tokens |
| **Gemini 3.5 Flash-Lite** | Minimal Reasoning | Google GenAI | 60 | 26 | **43.33%** | 4.00 s | ~35 output tokens |
| **Gemini 3.1 Flash-Lite** | Fast Vision | Google GenAI | 60 | 17 | **28.33%** | 6.29 s | ~20 output tokens |

---

## 2. Accuracy by Puzzle Subtype

| Subtype | Gemini 3.1 Flash-Lite | Gemini 3.5 Flash-Lite | Qwen 3.8 27B (Reasoning) |
| :--- | :---: | :---: | :---: |
| **Pipe Flow** | 11 / 15 (**73.3%**) | 9 / 15 (**60.0%**) | 7 / 7 (**100.0%**) |
| **Conveyor Routing** | 2 / 15 (**13.3%**) | 9 / 15 (**60.0%**) | 11 / 15 (**73.3%**) |
| **Laser Maze** | 2 / 15 (**13.3%**) | 4 / 15 (**26.7%**) | 12 / 15 (**80.0%**) |
| **Device Cables** | 2 / 15 (**13.3%**) | 4 / 15 (**26.7%**) | 4 / 9 (**44.4%**) |
| **Overall Accuracy** | **28.3%** | **43.3%** | **73.9%** |

---

## 3. Accuracy by Difficulty Tier

| Difficulty Tier | Gemini 3.1 Flash-Lite | Gemini 3.5 Flash-Lite | Qwen 3.8 27B |
| :--- | :---: | :---: | :---: |
| **Easy** | 3 / 8 (37.5%) | 6 / 8 (75.0%) | 5 / 5 (**100.0%**) |
| **Medium** | 6 / 12 (50.0%) | 3 / 12 (25.0%) | 8 / 9 (**88.9%**) |
| **Story Mode** | 4 / 20 (**20.0%**) | 7 / 20 (**35.0%**) | 14 / 17 (**82.4%**) |
| **Hard** | 4 / 12 (33.3%) | 6 / 12 (50.0%) | 5 / 9 (**55.6%**) |
| **Extreme** | 0 / 8 (**0.0%**) | 4 / 8 (50.0%) | 2 / 6 (**33.3%**) |

---

## 4. Key Insights

1. **Reasoning Models (CoT) vs Feedforward Vision**:
   - Routing puzzles (especially Laser Maze and Conveyor Routing) require multi-hop spatial tracking.
   - Non-reasoning feedforward models (Gemini 3.1 Flash-Lite) essentially guess when paths cross, dropping to **13.3%** on Laser Maze and Conveyor.
   - Deep reasoning models (Qwen 3.8 27B) break the path down step-by-step in chain-of-thought, achieving **80.0%** on Laser Maze and **73.3%** on Conveyor.
2. **The Hardest Frontier: Tangled Device Cables**:
   - Overlapping curved wires with occlusion proved the hardest challenge across all models. Even Qwen 3.8 27B dropped to **44.4%** on Device Cables.
3. **Story Mode Difficulty**:
   - For fast human/bot interactions (feedforward models), the new Story Mode successfully reduces accuracy down to **20.0%**, establishing a robust CAPTCHA defense.
