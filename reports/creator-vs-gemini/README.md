# Creator vs AI Models Benchmark Reports

This directory contains comparative benchmark reports and visual analytics between the **Human Creator Baseline** and AI vision-language models evaluated on the CAPTCHA challenges.

## Available Reports & Visualizations

### 1. Multi-Model Benchmark & Efficiency Frontier (Level 3A Routing Puzzle)
- **Full Report:** [creator-vs-ai-models.md](creator-vs-ai-models.md)
- **Structured Data:** [creator-vs-ai-models.json](creator-vs-ai-models.json)
- **Visual Analytics Dashboard (4-Panel):** [creator-vs-ai-models.png](creator-vs-ai-models.png) ([SVG](creator-vs-ai-models.svg))
- **Executive Scorecard:** [creator-vs-ai-models-summary.png](creator-vs-ai-models-summary.png) ([SVG](creator-vs-ai-models-summary.svg))
- **Generator Script:** `python reports/creator-vs-gemini/generate_multi_model_comparison.py`

Compares **Human Creator** (88.9% on Level 3A) against **Qwen 3.8 27B** (73.9% via Deep CoT), **Gemini 3.5 Flash-Lite** (43.3% Zero-Shot Baseline), **Gemini 3.1 Flash-Lite Enhanced** (33.3% with Guided Micro-CoT & Thinking LOW, exhibiting a **3x jump in Laser Maze** and **0% → 37.5% in Extreme**), and **Gemini 3.1 Base** (28.3%).

---

### 2. Canonical Creator vs Gemini Baseline (Matched 40-Challenge Audit)
- **Full Report:** [creator-vs-gemini.md](creator-vs-gemini.md)
- **Structured Data:** [creator-vs-gemini.json](creator-vs-gemini.json)
- **Visual Chart:** [creator-vs-gemini.png](creator-vs-gemini.png) ([SVG](creator-vs-gemini.svg))
- **Generator Script:** `python reports/creator-vs-gemini/generate_comparison.py`

The participant directly confirmed session `73fac77a-7985-4755-a26d-16ea9046541f` as their completion through the production Creator Baseline URL. The session remains stored as `cohort=main`; the report uses `analysis_role=creator` under the exact, versioned attribution record in [creator-attribution.json](creator-attribution.json).

The session predates production Creator cohort support. Investigation reproduced the landing-page bug: an active session cookie could be resumed from another cohort URL. The UI now resumes only a same-cohort session and explains active cross-cohort conflicts; the server continues to reject a cross-cohort start with HTTP 409. No production D1 rows were modified or relabeled. Main and all-cohort aggregate summaries exclude this exact creator-role record and report the exclusion count; raw exports retain the stored cohort and add `analysis_role`.

The final generator accepts the historical main record only when the exact confirmed session ID and all saved completion invariants match: human-v1, completed, 40 assigned/finalized trials, 30 correct, 3 skips including 1 timeout, 7.7-second median as displayed, frozen stage quotas, and 40 unique challenge IDs. It has no generic main-session attribution override.

Run these commands from the repository root:

```powershell
python reports/creator-vs-gemini/generate_comparison.py
python -m unittest discover -s reports/creator-vs-gemini -p test_comparison.py -v
python reports/creator-vs-gemini/generate_multi_model_comparison.py
```

Generation uses the ignored read-only D1 audit snapshot, committed attribution record, public challenge catalog, frozen Gemini aggregate, and its raw run directories. It performs no network requests, model inference, submissions, or database writes. Source hashes are recorded in the report. Public artifacts contain correctness outcomes and public challenge metadata, without submitted responses, model predictions, credentials, token hashes, participant IDs, or answer keys. The ignored audit snapshot contains participant response data and must remain private.

[Production revalidation](production-revalidation.json) and [session investigation](creator-session-investigation.md) document read-only D1 checks, deployment timing, and the reproduced routing cause.
