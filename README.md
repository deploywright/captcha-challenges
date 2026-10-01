# CAPTCHA Benchmark — Human vs. AI Visual Perception Evaluation

> 🚀 **Live Production Application:** [https://captcha-challenges-web.deploywright.workers.dev/](https://captcha-challenges-web.deploywright.workers.dev/)

A standardized visual perception benchmark and evaluation suite designed to test and compare human cognitive processing against machine vision models across five difficulty tiers.

---

## 🌐 Live Web Experience

The benchmark web application is live and accessible globally:
**[https://captcha-challenges-web.deploywright.workers.dev/](https://captcha-challenges-web.deploywright.workers.dev/)**

- **Level 1 (Normal CAPTCHA):** $3\times 3$ standard street driving grid (BDD100K held-out validation images).
- **Level 2A (Hard CAPTCHA):** $4\times 4$ high-complexity street grid (glare, night scenes, distance, occlusion).
- **Level 2B (Visual Illusion):** Adelson Checker Shadow illusion testing human perceptual constancy against raw pixel luminance.
- **Level 3A (Routing Puzzles):** A family of four procedural topological routing puzzles:
  - 🔦 *Laser Maze* (optical mirror reflection ray tracing)
  - 📦 *Conveyor Routing* (mechanical diverters and destination sorting)
  - 🚰 *Pipe Flow* (deep fluid network with closed valve gate branch tracing)
  - 🔌 *Device Cables* (smooth bridge cable tracing across multiple waypoints)
- **Level 3B (Degraded Vision):** Controlled multi-resolution downsampled visual ladder testing perceptual thresholds.

---

## 🏛️ System Architecture

The project is structured into three cleanly decoupled domains:

```text
captcha-challenges/
├── Challenges/       # Deterministic Python challenge engine & dataset processors
├── Web/              # Next.js 15 presentation, interaction & grading layer (Cloudflare Workers)
└── AI-Solver/        # Future AI benchmark evaluation pipelines
```

- **`Challenges/` (Source of Truth):** Operates deterministically from held-out splits (`BDD100K val` and procedural generators). Challenge data is never mutated or regenerated on the fly.
- **`Web/` (Public Interface & Grading):** Built on Next.js 15, React 19, TypeScript, and OpenNext for Cloudflare Workers. Features automated build-time challenge synchronization and strict zero-leakage security (ground-truth answers are strictly server-only).
- **`AI-Solver/` (Independent Evaluation):** Will interact with the benchmark via standardized public challenge contracts (`challenge.json` + `assets`).

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Node.js 20+ (recommended v22+)
- Python 3.11+

### Running the Web Application
```bash
cd web
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to browse and solve challenges locally.

### Running Test Suites
```bash
# Web tests (Vitest: synchronization, zero-leak audit, grading, catalog)
cd web
npm test

# Challenge Engine tests (pytest)
cd challenges
python -m pytest
```

### Deploying to Cloudflare Workers
```bash
cd web
npx wrangler login
npm run deploy
```

---

## 🔒 Security & Benchmark Integrity
- **Held-Out Benchmark Split:** All real-world vision data is strictly drawn from `BDD100K val` (`held_out_benchmark`). The `train` split is reserved exclusively for future AI model training.
- **Zero-Leakage Automated Audits:** Automated build-time checks inspect all public files (`public/challenges/`) and guarantee that ground-truth answers, solution paths, and switch/valve states are never exposed to the client.
