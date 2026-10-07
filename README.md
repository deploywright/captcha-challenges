# CAPTCHA Benchmark — Human vs. AI Visual Perception Evaluation

> 🚀 **Live Production Application:** [https://captcha-challenges-web.deploywright.workers.dev/](https://captcha-challenges-web.deploywright.workers.dev/)  
> 📊 **Master Benchmark Scorecard:** **82.8% Global AI Accuracy (111 / 134 Challenges Correct)** across all 5 tiers.  
> 🧪 **Test Suite Status:** **341 / 341 Tests Passing (100% Green)** across Challenge Engine and AI Solver suites.

A comprehensive visual perception benchmark and evaluation suite designed to test, benchmark, and compare human cognitive processing against state-of-the-art vision-language models and perceptual solvers across five difficulty tiers.

---

## 🌐 Benchmark Stages & Tiers (134 Total Challenges)

The benchmark web application is live and accessible globally:
**[https://captcha-challenges-web.deploywright.workers.dev/](https://captcha-challenges-web.deploywright.workers.dev/)**

| Level | Variant / Subtypes | Data Source & Nature | Challenges | AI Accuracy | Description |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Level 1** | `street-grid` | BDD100K `val` (Held-Out) | 20 | **85.0%** (17/20) | Standard $3\times 3$ street driving grid with common vehicle & traffic targets. |
| **Level 2A** | `hard-street-grid` | BDD100K `val` (Complex) | 20 | **55.0%** (11/20) | $4\times 4$ high-complexity street grid featuring night scenes, glare, distance, rain, and heavy occlusions. |
| **Level 2B** | `checker-shadow` | Adelson Optical Illusion | 6 | **100.0%** (6/6) | Tests human perceptual constancy vs. machine photometric luminance sampling. |
| **Level 3A** | `routing-puzzle` | 4 Procedural Generators | 60 | **100.0%** (60/60) | Multi-step topological routing puzzles across 5 difficulties (`easy`, `medium`, `hard`, `story`, `extreme`):<br>• 🔦 **Laser Maze (15/15):** $45^\circ$ optical mirror ray tracing.<br>• 📦 **Conveyor Routing (15/15):** Mechanical diverters & destination sorting.<br>• 🚰 **Pipe Flow (15/15):** Deep fluid network with closed valve branch tracing.<br>• 🔌 **Device Cables (15/15):** Smooth bridge cable tracing across multiple devices. |
| **Level 3B** | `degraded-vision` | Multi-resolution downsampling | 28 | **60.7%** (17/28)<br>*(F1 = 75.2%)* | Controlled multi-resolution degradation ladder ($64, 48, 32, 24, 16, 12, 8\text{ px}$) solved via Squint Bicubic filtering. |
| **Total** | **All 5 Stages** | **Comprehensive Benchmark** | **134** | **82.8%** (111/134) | Complete monorepo evaluation. |

---

## 🏛️ System Architecture

The project is structured into cleanly decoupled domains:

```text
captcha-challenges/
├── challenges/             # Deterministic Python challenge engine & dataset processors
│   ├── challenge_engine/   # Procedural generators, validators & dataset adapters
│   └── tests/              # 180 pytest test cases (contracts, determinism, isolation)
├── web/                    # Next.js 15 presentation, interaction & grading layer
│   ├── src/                # React 19 UI, zero-leak grading routes, OpenNext Cloudflare Workers
│   └── tests/              # Vitest test cases (session management, zero-leak audit)
├── AI-Solver/              # Autonomous AI solver & benchmarking engine
│   ├── src/ai_solver/      # Zero-shot VLM client, domain heuristics & ray tracers
│   ├── tests/              # 161 pytest test cases (isolation guardrails, mock providers)
│   └── results/            # Run records, predictions.jsonl, and execution summaries
└── reports/                # Analytical reports, visual charts, and multi-model scorecards
    └── creator-vs-gemini/  # Creator baseline vs Gemini vs Qwen 27B comparative studies
```

- **`challenges/` (Source of Truth):** Operates deterministically from frozen, held-out splits (`BDD100K val` and mathematical seeds). Challenge data is strictly reproducible and never mutated on the fly.
- **`web/` (Public Interface & Grading):** Built on Next.js 15, React 19, TypeScript, and OpenNext for Cloudflare Workers. Features automated build-time challenge synchronization and strict zero-leakage security (ground-truth answers are strictly server-only).
- **`AI-Solver/` (Independent Evaluation):** Evaluates challenges strictly via public challenge contracts (`challenge.json` + `assets/*.webp`), strictly forbidden from importing `challenge_engine` or inspecting private metadata.
- **`reports/` (Audit & Analytics):** Automated dashboard generation visualizing human creator vs AI models, speed vs accuracy frontiers, and resolution scaling.

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Node.js 20+ (recommended v22+)
- Python 3.11+
- Virtual environment with pip

### 1. Web Application
```bash
cd web
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to browse and solve challenges interactively.

### 2. Challenge Engine (CLI & Generation)
```bash
cd challenges
python -m pip install -e ".[test]"

# Check dataset & asset readiness
python -m challenge_engine status

# Run all 180 engine tests
python -m pytest
```

### 3. AI Solver & Full Benchmark Execution
```bash
cd AI-Solver
python -m pip install -e ".[gemini,test]"

# Run all 161 solver tests (includes test_no_private_access.py)
python -m pytest

# Run full 134-challenge benchmark compiler
python run_full_134_benchmark.py

# Generate complete comparative visual dashboards
python ../reports/creator-vs-gemini/generate_complete_level3_dashboard.py
python ../reports/creator-vs-gemini/generate_134_benchmark_report.py
```

---

## 🧪 Comprehensive Verification & Test Suites

The repository enforces strict continuous verification:

```bash
# Challenge Engine tests (180 passed)
python -m pytest challenges/tests

# AI-Solver tests (161 passed, 1 skipped)
python -m pytest AI-Solver/tests
```

**Total: 341 passing tests.**

---

## 🔒 Security & Benchmark Integrity
- **Held-Out Benchmark Split:** All real-world vision data is strictly drawn from `BDD100K val` (`held_out_benchmark`). The `train` split is reserved exclusively for training and is structurally blocked by dataset adapters.
- **Zero-Leakage Automated Audits:** Automated build-time checks inspect all public files (`public/challenges/`) and guarantee that ground-truth answers, solution paths, and switch/valve states are never exposed to the client.
- **No Cheating Contract:** The `AI-Solver` undergoes automated static and runtime AST analysis in `test_no_private_access.py` to guarantee zero imports or references to `challenge_engine` or private answer schemas.
