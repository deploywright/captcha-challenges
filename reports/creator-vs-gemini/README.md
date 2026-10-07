# Creator vs AI Models Benchmark Reports

This directory contains comparative benchmark reports, analytical datasets, and visual analytics between the **Human Creator Baseline** and AI vision-language models evaluated across the CAPTCHA challenges.

## 📊 Available Reports & Visualizations

### 1. Master Benchmark: All 134 Challenges (Global Monorepo Evaluation)
- **Full Report:** [all-134-challenges-benchmark.md](all-134-challenges-benchmark.md)
- **Structured Dataset:** [all-134-challenges-benchmark.json](all-134-challenges-benchmark.json)
- **Visual Analytics Dashboard:** [all-134-challenges-benchmark.png](all-134-challenges-benchmark.png) ([SVG](all-134-challenges-benchmark.svg))
- **Generator Script:** `python reports/creator-vs-gemini/generate_134_benchmark_report.py`

**Key Findings:** Comprehensive evaluation across all 5 benchmark stages (Level 1, 2A, 2B, 3A, 3B). The integrated AI Solver achieves **111 / 134 correct (82.8% global accuracy)**, demonstrating complete mastery over Level 3A (100%) and Level 2B (100%), and robust perception on Level 3B (60.7% exact match / 75.2% F1).

---

### 2. Level 3 Complete Comparison: Level 3A Routing + Level 3B Degraded Vision
- **Full Report:** [level-3-complete-comparison.md](level-3-complete-comparison.md)
- **Visual Analytics Dashboard (4-Panel):** [level-3-complete-comparison.png](level-3-complete-comparison.png) ([SVG](level-3-complete-comparison.svg))
- **Generator Script:** `python reports/creator-vs-gemini/generate_complete_level3_dashboard.py`

**Key Findings:** Unified analysis of the hardest 88 challenges (60 Level 3A + 28 Level 3B). Compares Human Creator vs Baseline Gemini vs Enhanced Gemini vs Qwen 27B Deep CoT across all subtypes, difficulty tiers, and resolution ladders.

---

### 3. Level 3B Dedicated Study: Degraded Vision & Squint Bicubic Filtering
- **Full Report:** [level-3b-creator-vs-ai.md](level-3b-creator-vs-ai.md)
- **Structured Data:** [level-3b-benchmark-results.json](level-3b-benchmark-results.json)
- **Visual Chart:** [level-3b-creator-vs-ai.png](level-3b-creator-vs-ai.png) ([SVG](level-3b-creator-vs-ai.svg))
- **Generator Script:** `python reports/creator-vs-gemini/generate_level_3b_report.py`

**Key Findings:** Solves the high-frequency mosaic artifact breakdown in low resolutions (8px–24px). Reconstructs natural motorcycle light contours, boosting 8px detection from 0% to 62.8% F1 (outperforming humans who skipped extreme downsampling).

---

### 4. Multi-Model Benchmark & Efficiency Frontier (Level 3A Routing Puzzle)
- **Full Report:** [creator-vs-ai-models.md](creator-vs-ai-models.md)
- **Structured Data:** [creator-vs-ai-models.json](creator-vs-ai-models.json)
- **Visual Analytics Dashboard (4-Panel):** [creator-vs-ai-models.png](creator-vs-ai-models.png) ([SVG](creator-vs-ai-models.svg))
- **Executive Scorecard:** [creator-vs-ai-models-summary.png](creator-vs-ai-models-summary.png) ([SVG](creator-vs-ai-models-summary.svg))
- **Generator Script:** `python reports/creator-vs-gemini/generate_multi_model_comparison.py`

Compares **Human Creator** (88.9% on Level 3A audit subset) against **Qwen 3.8 27B** (73.9% via Deep CoT), **Gemini 3.5 Flash-Lite** (43.3% Zero-Shot Baseline), **Gemini 3.1 Flash-Lite Enhanced** (100% with domain visual ray-tracers), and **Gemini 3.1 Base** (28.3%).

---

### 5. Canonical Creator vs Gemini Baseline (Matched 40-Challenge Audit)
- **Full Report:** [creator-vs-gemini.md](creator-vs-gemini.md)
- **Structured Data:** [creator-vs-gemini.json](creator-vs-gemini.json)
- **Visual Chart:** [creator-vs-gemini.png](creator-vs-gemini.png) ([SVG](creator-vs-gemini.svg))
- **Generator Script:** `python reports/creator-vs-gemini/generate_comparison.py`

The participant directly confirmed session `73fac77a-7985-4755-a26d-16ea9046541f` as their completion through the production Creator Baseline URL. The session remains stored as `cohort=main`; the report uses `analysis_role=creator` under the exact, versioned attribution record in [creator-attribution.json](creator-attribution.json).

---

## 🚀 Regenerating All Reports

Run from repository root:

```bash
# 1. Master 134-Challenge Benchmark:
python reports/creator-vs-gemini/generate_134_benchmark_report.py

# 2. Unified Level 3 Dashboard:
python reports/creator-vs-gemini/generate_complete_level3_dashboard.py

# 3. Level 3B Degraded Vision Study:
python reports/creator-vs-gemini/generate_level_3b_report.py

# 4. Multi-Model Level 3A Comparison:
python reports/creator-vs-gemini/generate_multi_model_comparison.py

# 5. Creator Matched Audit:
python reports/creator-vs-gemini/generate_comparison.py
python -m unittest discover -s reports/creator-vs-gemini -p test_comparison.py -v
```
