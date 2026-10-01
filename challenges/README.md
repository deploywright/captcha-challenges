# CAPTCHA Challenge Engine (`Challenges/`)

Deterministic visual CAPTCHA generator, dataset filter, packager, and validator for the Human-vs-AI benchmark.

This package operates strictly within `Challenges/` and is completely decoupled from `Web/` (presentation layer) and `AI-Solver/` (evaluation solver).

---

## 1. Critical Data-Split Policy (Held-Out Benchmark Isolation)

Because an AI solver (`AI-Solver/`) will be trained later, **challenge data must never overlap with AI training data**:

| BDD100K Official Split | Local Directory | Project Role | Allowed Usage |
| :--- | :--- | :--- | :--- |
| **`train`** (70,000 images) | `data/bdd100k/bdd100k/images/100k/train/` | `future_ai_training` | **RESERVED EXCLUSIVELY FOR FUTURE AI TRAINING** (training + internal validation subsets). **NEVER** used by `Challenges/`. |
| **`val`** (10,000 images) | `data/bdd100k/bdd100k/images/100k/val/` + `data/bdd100k/labels/det_20/det_val.json` | `held_out_benchmark` | **RESERVED EXCLUSIVELY FOR CHALLENGE GENERATION** (`Level 1`, `Level 2A`, `Level 3B`). Frozen Human-vs-AI benchmark. |

### Built-in Leakage Guardrails
1. **Adapter Enforcement (`BDD100KDataset`)**: Accepts only `split="val"`. Raises `BDD100KDataSplitError` if `split != "val"`, if pointed at a `train` directory, or if any discovered image/annotation path contains `train`.
2. **Private Provenance Metadata**: Every generated BDD100K challenge (`answer.json`) and tile records:
   ```json
   {
     "dataset": "BDD100K",
     "source_dataset": "BDD100K",
     "source_split": "val",
     "project_role": "held_out_benchmark",
     "source_image_id": "b766079c-62ff02f3.jpg",
     "source_path": "bdd100k/images/100k/val/b766079c-62ff02f3.jpg",
     "sequence_id": "b766079c"
   }
   ```
3. **Benchmark Manifest (`generated/benchmark_manifest.json` & `data/bdd100k/benchmark_manifest.json`)**: Automatically maintained on export, recording every unique BDD100K `val` image (`source_image_id`, `source_path`, `sequence_id`, `used_by`, `challenge_ids`) used across `level-1`, `level-2a`, and `level-3b`.
4. **Automated Validation (`validation.py`)**: Fails validation if any Level 1, 2A, or 3B challenge or benchmark manifest item has `source_split != "val"` or references `train`.

---

## 2. Challenge Structure & Data Strategy

Only **one** challenge level (`Level 3A — Tangled Cables`) uses full procedural synthesis. All other levels use real datasets, an existing external visual asset, or controlled transformations of real BDD100K `val` images:

| Level | Internal Key | Variant | Source Strategy |
| :--- | :--- | :--- | :--- |
| **Level 1** | `level_1_street_grid` | `street-grid` | **Real BDD100K (`val` split only)**: Selects easy, clearly visible daytime examples (`3×3` grid, default target `motorcycle`) using BDD100K bounding box area, aspect ratio, occlusion, truncation, and weather/timeofday annotations. Rejects microscopic (`< 28 px`) and orphan-rider ambiguous samples. |
| **Level 2A** | `level_2a_hard_street_grid` | `hard-street-grid` | **Real BDD100K (`val` split only)**: Selects harder real-world street scenes (`4×4` or `5×5` grid) featuring smaller targets, partial occlusion, truncation, night/dawn/dusk, rain/fog, dense traffic, and confusable distractors (`bicycle`, `rider`) while filtering out microscopic/unrecognizable specks. |
| **Level 2B** | `level_2b_checker_shadow` | `checker-shadow` | **Static External Asset**: Packages the existing Edward H. Adelson (1995) Checker Shadow Illusion image (`assets/level-2b/checker-shadow.png`) and documented provenance (`assets/level-2b/metadata.json`). No procedural synthesis. |
| **Level 3A** | `level_3a_tangled_cables` | `tangled-cables` | **Procedural Generation (Graph-First)**: Generates a 1-to-1 bijection between `server_1..N` and `port_1..N`, routes smooth monotone-X Bezier cables, verifies bounds/intersections, and renders over/under bridges. |
| **Level 3B** | `level_3b_degraded_vision` | `degraded-vision` | **Real BDD100K (`val` split only) + Controlled Degradation**: Takes copies of real BDD100K `val` images and applies controlled `downsample -> nearest-neighbor upscale` across the resolution ladder `64, 48, 32, 24, 16, 12, 8` without modifying original BDD100K files. |

---

## 3. CLI Usage

Run all commands from `Challenges/`:

```bash
# Check dataset & asset readiness and BDD100K val class statistics
python -m challenge_engine status

# Generate 20 Level 1 challenges from BDD100K val
python -m challenge_engine generate --level 1 --count 20 --seed 100

# Generate 20 Level 2A hard challenges from BDD100K val
python -m challenge_engine generate --level 2a --count 20 --seed 100

# Package Level 2B (static Adelson Checker Shadow asset)
python -m challenge_engine generate --level 2b --count 1 --seed 100

# Generate Level 3A (procedural Tangled Cables)
python -m challenge_engine generate --level 3a --count 4 --seed 100 --difficulty hard

# Generate Level 3B multi-resolution series across the full ladder (64,48,32,24,16,12,8)
python -m challenge_engine generate --level 3b --count 4 --seed 100 --resolutions 64,48,32,24,16,12,8

# Validate all generated challenges and the benchmark manifest
python -m challenge_engine validate generated/

# Run full pytest suite
python -m pytest -v
```
