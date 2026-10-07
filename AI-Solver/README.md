# AI-Solver — Autonomous CAPTCHA Perception & Reasoning Engine

An independent, multi-tier evaluation suite and autonomous solver for the CAPTCHA Visual Perception Benchmark. Python 3.11+.

> 🎯 **Master Benchmark Scorecard:** **82.8% Global Accuracy (111 / 134 Challenges Solved)**  
> 🏆 **Level 3A Routing Performance:** **100.0% (60 / 60 Challenges Solved)**  
> 🔍 **Level 3B Degraded Vision:** **60.7% Exact Set Match / 75.2% Average F1**  
> 🛡️ **Zero Private Access:** Strictly complies with public challenge contracts (`challenge.json` + `assets/*.webp`). Fully verified by `test_no_private_access.py`.

```text
               Public Challenge Contract (challenge.json + assets)
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
       [VLM Foundation Layer]                 [Heuristic & Ray Tracing]
   Gemini 3.1 / 3.5 Flash-Lite                • Optical Ray Tracing (Laser Maze)
   Qwen 3.8 27B / GPT-4.1 mini                • Fluid Network Flow (Pipe Flow)
   (Level 1 & Level 2A Street Grids)          • Endpoint Arc Matching (Device Cables)
                                              • Exit Geometry OCR (Conveyor Routing)
                                              • Squint Bicubic Filter (Degraded Vision)
                                     │
                                     ▼
                      Public Submission & Metrics
          (Exact Challenge Accuracy, Recall, F1, Latency & Cost)
```

---

## 📊 Solver Performance Across All 5 Benchmark Stages

| Stage | Puzzle Type | Approach / Solver Module | Evaluated | Accuracy | Highlights |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Level 1** | `street-grid` | Zero-shot VLM (Structured Outputs) | 20 | **85.0%** (17/20) | Identifies vehicles, pedestrians & traffic lights in $3\times 3$ grid. |
| **Level 2A** | `hard-street-grid` | Zero-shot VLM (Micro-CoT) | 20 | **55.0%** (11/20) | Solves occluded, nighttime, and distant targets in $4\times 4$ grid. |
| **Level 2B** | `checker-shadow` | Photometric Luminance Sampling | 6 | **100.0%** (6/6) | Bypasses human Adelson illusion via objective pixel luminance analysis. |
| **Level 3A** | `routing-puzzle` | Domain Heuristics & Optical Ray-Tracers | 60 | **100.0%** (60/60) | **100% on all 4 subtypes:**<br>• `laser-maze`: 15/15 (45° mirror ray trace & sensor OCR)<br>• `pipe-flow`: 15/15 (Open valve network tracing)<br>• `conveyor-routing`: 15/15 (Exit bin routing & template OCR)<br>• `device-cables`: 15/15 (Endpoint palette & pin arc sampling) |
| **Level 3B** | `degraded-vision` | Squint Bicubic Filtering + Dilation | 28 | **60.7%** (17/28)<br>*(F1 = 75.2%)* | Recovers low-frequency light contours across 8px–64px ladder. |
| **Total** | **All Stages** | **Integrated AI Engine** | **134** | **82.8%** (111/134) | Complete benchmark master run. |

---

## 🛠️ Installation & Setup

From the repository root:

```bash
cd AI-Solver
python -m pip install -e ".[gemini,test]"
```

Copy `.env.example` to `.env` and set your credentials:

```env
CAPTCHA_BASE_URL=https://captcha-challenges-web.deploywright.workers.dev
CAPTCHA_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.1-flash-lite
```

*(Note: Secrets are never accepted in YAML or stored in run metadata. `.env` is ignored by Git).*

---

## 🚀 Execution Commands

### 1. Running Test Suites
Verify all 161 test cases, contract validators, and isolation guardrails:

```bash
python -m pytest
```

### 2. Solving a Single Challenge via CLI
```bash
# Solve a specific challenge using VLM / heuristics without submission:
python -m ai_solver.cli solve lvl3a_laser_2fplq0 --solver vlm

# Explicit submission to production API:
python -m ai_solver.cli solve lvl3a_laser_2fplq0 --solver vlm --submit
```

### 3. Benchmarking Subsets via CLI
```bash
# Run benchmark on public street-grid:
python -m ai_solver.cli benchmark --variant street-grid --solver vlm --limit 5

# Reproducible random baseline:
python -m ai_solver.cli benchmark --variant street-grid --solver random --seed 42
```

### 4. Running the Full 134-Challenge Benchmark Runner
Compiles all 134 challenge predictions and generates the master benchmark record:

```bash
python run_full_134_benchmark.py
```

Outputs:
- `reports/creator-vs-gemini/all-134-challenges-benchmark.json`
- `reports/creator-vs-gemini/all-134-challenges-benchmark.md`

---

## 🔒 Contract Isolation & Security Guardrails

The solver enforces strict benchmark hygiene:
1. **Zero Private Metadata Access:** `tests/test_no_private_access.py` uses AST inspection to verify that `ai_solver` never imports `challenge_engine` or accesses private answers (`answer.json`).
2. **Public Allowlist Only:** The HTTP client permits only public endpoints:
   - `GET /challenges/catalog.json`
   - `GET /challenges/<id>/challenge.json`
   - `GET /challenges/<id>/assets/<image>`
   - `POST /api/challenges/<id>/submit`
3. **Leak Detection:** Any attempt by the server to return private fields (`correctSelection`, `routing`, `answer`) triggers an immediate `PUBLIC DATA LEAK DETECTED` abort.
