# Level 3A difficulty repair

The Python configuration and `ROUTING_DIFFICULTY_PRESETS` define real generated
complexity. Public `challenge.json` contains the generator's difficulty; Web
sync copies it unchanged, and Story Mode selects `laser-maze` with `story`.
The existing fallback order remains story, hard, medium, any Laser Maze.

## Final presets

Laser Maze uses fixed-size mirrors and target labels. Targets avoid other
targets and the emitter using their actual rendered bounding boxes.

| Difficulty | Grid | Reflections | Targets | Distractors |
| --- | --- | --- | --- | --- |
| easy | 7×7 | 1–2 | 3 | 0–2 |
| medium | 8×8 | 3–4 | 4 | 2–4 |
| story | 10×10 | 5–6 | 5 | 4–6 |
| hard | 11×11 | 7–8 | 5 | 6–8 |
| extreme | 12×12 | 9–12 | 6 | 8–10 |

Conveyor builds the active route first. Each route switch has distinct active
and inactive children. Decoy branches contain additional switches and lead
to other bins; remaining spurs terminate. Metrics come from the generated
graph and an independent active-edge traversal.

| Difficulty | Route decisions | Total switches | Bins | Decoy branches |
| --- | --- | --- | --- | --- |
| easy | 2 | 4 | 3 | 1 |
| medium | 4 | 7 | 4 | 2 |
| story | 6 | 11 | 5 | 4 |
| hard | 8 | 14 | 5 | 5 |
| extreme | 11 | 20 | 6 | 7 |

Pipe builds a guaranteed open path and multi-segment wrong-tank branches.
Blockers occur after the first branch segment. Independent undirected BFS
requires exactly one reachable tank. Opening each critical blocker must
make another tank reachable. Invalid attempts regenerate deterministically;
the generator never repairs them by closing all non-solution edges.

| Difficulty | Solution decision depth | Junctions | Tanks | Critical closed valves | Decoy branches |
| --- | --- | --- | --- | --- | --- |
| easy | 2 | 4 | 3 | 1 | 1 |
| medium | 4 | 6 | 4 | 2 | 2 |
| story | 6 | 10 | 5 | 4 | 4 |
| hard | 8 | 14 | 5 | 6 | 6 |
| extreme | 11 | 19 | 6 | 8 | 8 |

Device Cable strokes remain 7 pixels wide at every difficulty.

| Difficulty | Cables | Waypoint columns | Answer options |
| --- | --- | --- | --- |
| easy | 5–6 | 2–3 | 4 |
| medium | 7–8 | 3–4 | 4 |
| story | 9–10 | 3–5 | 5–6 |
| hard | 10–11 | 4–5 | 5–6 |
| extreme | 11–12 | 5–6 | 6 |

## Generated data and visual QA

There are exactly 60 regenerated Level 3A samples, 15 per subtype:
2 easy, 3 medium, 5 story, 3 hard, 2 extreme.
Generation stages and validates the complete batch before replacing only
`generated/level-3a`. Normal workspace ACLs survive the staging-directory
rename on Windows, allowing Web build subprocesses to read the output.

The developer-only [visual QA report](level_3a_visual_qa.html) shows measured
complexity on every card. All 20 Story images were visually inspected:

| Subtype | Inspected seeds | Result |
| --- | --- | --- |
| Laser Maze | 305–309 | Clear emitter and non-overlapping target labels; 5–6 real reflections; plausible off-path mirrors |
| Conveyor Routing | 315–319 | Readable fixed-size switches, six active decisions, multi-segment decoys, clear crossing overpasses |
| Pipe Flow | 325–329 | Readable gates, six main-route junctions, four delayed essential blockers, separated valve labels |
| Device Cables | 335–339 | Clear highlighted query, readable endpoint labels and cable bridges, 9–10 cables, 5–6 options |

The first inspection rejected overlapping emitter/target cards and valve
labels. Generation now prevents those collisions and the samples were
regenerated and inspected again. No font, switch, valve, target, or stroke
size is reduced as difficulty increases.

## Validation evidence

Run commands from `challenges/` for Python and `web/` for npm. Logs are retained
in the repository's ignored `.tmp/` directory.

| Check | Command | Result / log |
| --- | --- | --- |
| Full Python suite | `python -m pytest -q -p no:cacheprovider --basetemp=../.tmp/pytest-final-full` | 171 passed; `.tmp/pytest-full.log` |
| Routing/difficulty suite | `python -m pytest tests/test_level_3a_routing_puzzles.py tests/test_level_3a_difficulty.py -q -p no:cacheprovider --basetemp=../.tmp/pytest-routing-final` | 137 passed; `.tmp/level-3a-tests.log` |
| Batch generation | `python -m scripts.generate_level_3a_batch` | 60 exported and validated; `.tmp/level-3a-batch.log` |
| Level 3A validation | `python -m challenge_engine.cli validate generated/level-3a` | 60 passed, zero failed; `.tmp/level-3a-validation.log` |
| Full generated-directory validation | `python -m challenge_engine.cli validate generated` | Failed: Level 3A 60/60 passed; 74 existing other-level samples fail schema validation; `.tmp/challenge-validation.log` |
| Web sync | `npm run challenges:sync` | 134 entries and private answers; zero answer leakage; `.tmp/web-sync.log` |
| Vitest | `npm run test` | 17 passed; `.tmp/vitest.log` |
| Web lint | `npm run lint` | Passed with one existing `react-hooks/exhaustive-deps` warning in `RoutingPuzzleChallenge.tsx`; `.tmp/web-lint.log` |
| Python lint | `python -m ruff check` on changed routing generators, new tests, and batch script with `--select F` | Passed; `.tmp/python-lint.log` |
| Next.js build | `npm run build` | Passed; `.tmp/next-build.log` |
| OpenNext build | `npm run build:worker` | Passed with all 134 catalog entries; worker written to `web/.open-next/worker.js`; `.tmp/opennext-build.log` |

The running development server was briefly stopped to release Windows' lock
on `.open-next/assets`, then restarted after the successful OpenNext build.

The full-directory failure is outside this repair: existing Level 1/2A/3B
answers contain crop/rendered-object fields unsupported by the current
`TilePrivateMetadata`; existing Level 2B answers include illusion variants
unsupported by the current checker-shadow schema. These generators and
outputs were left unchanged. This is not an all-green repository validation.

Tests cover the five difficulty tiers and seeds 101, 202, 303, 404, 505.
They recompute reflection hits, active Conveyor paths, Pipe shortest open
paths and junction degrees, critical blockers, cable counts, and option
counts. They also check generated monotonicity, deterministic pixels and
answers, subtype override reproduction, export, public privacy, and retries
for zero or multiple reachable tanks.

## Pipeline confirmations

- Python `Level3AConfig` accepts `story`.
- Story presets exist for all four routing subtypes and are generated by Python.
- Every generated routing `challenge.json` contains its configured difficulty.
- Web types accept exactly easy, medium, story, hard, extreme; adapter and sync
  reject invalid or missing routing difficulty without inventing a label.
- Catalog difficulty equals both Python and synced public JSON; Story
  progression returns a Story Laser Maze.
- Conveyor and Pipe difficulty alter actual decision depth and graph size.
- Complexity metrics, configuration, graphs, and solutions remain private.
  Python, Web sync, and leak tests explicitly reject their public exposure.
- The old cable preset is explicitly named
  `LEGACY_TANGLED_CABLE_DIFFICULTY_PRESETS`; it only serves the compatibility
  generator. The legacy internal level key is documented and preserved.
- Level 1, Level 2A, Level 2B, and Level 3B generators and outputs are unchanged.
  No AI-Solver or UI redesign was introduced.
