# Production repair and Workers deployment

Starting branch: `main`, commit `fa259a3bda7c34391eaf6f5cef4626f58c08ebb0`.
Compatibility reference: `592fe01cb8d230156a22015f3a5582108d62f486`.

The repair restores the non-Level-3A visual overhaul while preserving the active routing implementation, Story difficulty, and all 60 Level 3A outputs.

## Original failures

The original validator reported **134 total, 60 passed, 74 failed**. Every failure occurred while parsing private `answer.json`; public schema checks passed, and determinism was not reached for those 74 challenges.

| Level | Challenges failing | Private field errors |
| --- | ---: | ---: |
| 1 | 20 | 600 |
| 2A | 20 | 600 |
| 2B | 6 | 47 |
| 3B | 28 | 840 |
| Total | 74 | 2,087 |

The street/degradation errors were `extra_forbidden` for six crop/render fields:

| Field | Level 1 instances | Level 2A instances | Level 3B instances |
| --- | ---: | ---: | ---: |
| `crop_box` | 180 | 180 | 252 |
| `difficulty_budget_factors` | 180 | 180 | 252 |
| `crop_context_factor` | 60 | 60 | 84 |
| `rendered_object_size` | 60 | 60 | 84 |
| `rendered_object_width` | 60 | 60 | 84 |
| `rendered_object_height` | 60 | 60 | 84 |

Level 2B had six unsupported `illusionType` and six unsupported `explanation` fields, five unsupported `groundTruthMetric` and five unsupported `measuredValues` fields. Five non-checker illusions were each incorrectly required to provide `squareA`, `squareB`, `luminanceDifference`, `rgbMaxDifference`, and `tolerance` (25 missing-field errors).

Evidence: `.tmp/full-validation-before-repair.log` and `.tmp/full-validation-before-repair-grouping.json`.

## Changes and output decisions

| Files | Purpose |
| --- | --- |
| `challenges/challenge_engine/core/schemas.py` | Explicit crop/render fields with `extra="forbid"`; optional street targets; 3×3 Level 2A defaults and budget; heterogeneous illusion measurements and optional checker-only fields. The Level 3A schema segment is unchanged. |
| `core/image_prep.py` | Restore square context crops, natural negative crops, seeded framing, and rendered target metrics. |
| `datasets/bdd100k.py` | Restore class visibility/context profiles and target analysis while retaining the adapter and later distractor entries. Enforce Level 2A scene-factor budgets and class-specific rendered visibility. |
| `levels/level_1/generator.py`, `levels/level_2a/generator.py`, `levels/level_3b/generator.py` | Restore crop preparation and private measurements. Level 3B freezes source/crop/order across all seven resolutions. Optional target lists are honored; absent lists preserve the configured target. |
| `core/ids.py` | Preserve legacy non-routing ID payloads while retaining current subtype-aware routing IDs. |
| `levels/level_2b/generator.py`, `levels/level_2b/verification.py` | Package all six existing catalog assets, reject unknown subtypes/missing answers, and independently check the supplied measurement contract. No assets or provenance were fabricated. |
| `core/validation.py` | Subtype-aware illusion checks; reproduce recorded batch target/count/grid parameters; compare regenerated non-routing source IDs, crop boxes, and decoded image pixels. |
| `configs/level-2a.json` | 3×3, three positives, at most two difficulty factors. |
| `tests/test_overhaul_quality.py` | Nine restored quality gates covering actual generator resizing, round-shape preservation, explicit metadata, targets, defaults/budget, six illusions, seven resolutions, and public leaks. |
| `tests/conftest.py`, `tests/test_street_grid_levels.py` | Make fixture image dimensions match annotations, supply real bounded-difficulty scenes, and update the superseded generic small-object assertion to class-profile geometry. |
| `web/components/challenges/ImageGridChallenge.tsx`, `ChallengePlayer.tsx` | Restore image inspection/zoom, cached-image readiness, and 768px desktop image grids. |
| `RoutingPuzzleChallenge.tsx` | Stabilize the options dependency with `useMemo`, fixing the hook warning without changing puzzle behavior. |
| `BinaryChoiceChallenge.tsx`, `web/lib/challenges/catalog.ts` | Accurate generic illusion copy and image alternative text; correct Level 2A 3×3 copy. |

Levels 1 (20), 2B (6), and 3B (28) reproduce existing output, including decoded image pixels, and were retained. Level 3A's 189 source/schema/generated-file hashes match the baseline.

Only **20 Level 2A challenges** were regenerated. The historical implementation declared a budget without applying it; restored source now enforces two factors and class-specific rendered visibility. Existing Level 2A therefore failed the stronger deterministic checks. Regeneration preserved every ID, seed, target class, the 3×3 layout, and three positives. The benchmark manifest was rebuilt by the exporter. No generated JSON was patched by hand.

Every Level 2A positive now meets its class's rendered visibility threshold (32–50px depending on class); the minimum across the batch is **32.52px**. All tiles have at most two recorded difficulty factors. All 20 challenges were visually reviewed in `.tmp/level-2a-visual-review.jpg`; batch inputs are recorded in `.tmp/level-2a-regeneration.json`.

The final population remains **20 / 20 / 6 / 60 / 28 = 134**. Generated output remains ignored by Git under the repository's existing rules.

## Validation

| Check | Result | Evidence |
| --- | --- | --- |
| Level 3A baseline and after shared schema edit | 137 passed each time | `.tmp/phase-a-l3a-baseline.log`, `.tmp/phase-a-schema-l3a.log` |
| `python -m pytest -q -p no:cacheprovider` | 180 passed | `.tmp/phase-a-final-tests.log` |
| `python -m challenge_engine.cli validate generated` | 134/134, zero failures | `.tmp/full-validation-final.log` |
| `python -m challenge_engine.cli validate generated/level-3a` | 60/60 | `.tmp/level-3a-validation-final.log` |
| `npm run challenges:sync` | 134 synced; zero leakage | `.tmp/web-sync.log` and deployment build log |
| `npm run test` | 17 passed | `.tmp/web-test.log` |
| `npm run lint` | Zero ESLint errors/warnings | `.tmp/web-lint.log` |
| `npm run build` | Passed | `.tmp/web-build-final.log` |
| `npm run build:worker` | Passed | `.tmp/web-worker-build-final.log` |
| `npm run preview` | Local Workers runtime passed browser smoke | `.tmp/workers-preview.log`, `.tmp/preview-smoke.json` |

The local browser smoke exercised home, level selection, all five Story stages, Story Laser Maze selection, loaded images, timers, wrong/correct submission, retry with cached images, inspection and keyboard navigation, Try Another, Next Level, final replay, all six illusion submissions, and all five stages at 390×844. Desktop image grids measured 768px; mobile pages had no horizontal overflow. Five private-file probes returned 404. The browser scanned 39 public responses and found no private metadata or browser errors.

The artifact scan checked `web/public` (135 text artifacts), `.next/static` (21), `.open-next/assets` (156), and prerendered public HTML/RSC (274), with zero leaks. Private server JavaScript is intentionally excluded from the public-artifact scan. Answers remain in the server registry. Evidence: `.tmp/security-audit-final.log`.

## Measurement limits

Checker Shadow luminance is sampled from the asset. Ponzo spans, Ebbinghaus center-circle runs, simultaneous-contrast patches, and Café Wall mortar rows are checked using catalog coordinates. Müller-Lyer fins overlap shaft endpoints: validation checks documented endpoint geometry and continuous raster shaft interiors, but does not claim independent fin/shaft segmentation. Attribution and licensing are checked against the supplied catalog, not independently established from historical source publications.

## Cloudflare configuration and authentication

Wrangler **4.145.0** is installed. `wrangler whoami` confirmed existing OAuth authentication with Workers write scopes; browser login was unnecessary. Wrangler reported missing scopes for unrelated products; Workers deployment uses the existing relevant permissions.

Existing OpenNext **1.20.7** configuration is retained: `captcha-challenges-web`, `.open-next/worker.js`, `.open-next/assets` with `ASSETS`, `nodejs_compat`, compatibility date `2024-09-23`. The installed Wrangler schema and [OpenNext configuration documentation](https://opennext.js.org/cloudflare/get-started) were checked. No Pages migration, new database/storage bindings, or AI solver was introduced.

## Deployment and production verification

`npm run deploy` completed successfully after every Phase A gate and the Workers preview smoke passed.

- Worker: **captcha-challenges-web**
- URL: **https://captcha-challenges-web.realquesthq.workers.dev**
- Version: **27178075-98a4-4ce6-8df2-5558c9c283c4**
- Upload: 4,796.53 KiB; gzip 934.82 KiB
- Worker startup: 21ms
- Assets: 833 uploaded, three already present
- Runtime binding: `ASSETS` only
- Deployment evidence: `.tmp/cloudflare-deploy.log`

The production browser smoke passed home and `/challenges` (HTTP 200), public challenge JSON and its image (HTTP 200), the submission API (HTTP 200 with correct grading), the complete five-stage Story flow, wrong-answer retry, timer restart, zoom, Try Another, Next Level, final replay, all six illusion submissions, and all five mobile layouts. Story selected `lvl3a_laser_2fplq0`, a generated **laser-maze / story** challenge. Desktop image grids again measured **768px**. All five private-file paths returned **404**.

Production browser inspection scanned **43 public responses**, including HTML, JavaScript, JSON, and RSC, excluding the authorized submission responses. It found **zero private metadata leaks and zero browser errors**. The artifact scan was repeated against the final deployment build and again found zero leaks.

Evidence: `.tmp/production-smoke.json`, `.tmp/production-browser.log`, `.tmp/production-stage-1.png` through `production-stage-5.png`, and `.tmp/production-mobile.png`. Smoke automation and audit scripts are retained in `.tmp/browser_smoke.cjs` and `.tmp/security_audit.py`.

The local Next development server was temporarily stopped to release Windows locks during OpenNext builds, then restored after deployment.
