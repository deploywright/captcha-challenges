# Human Benchmark delivery and verification

Verified on 2026-10-02. The collection protocol, operational instructions, and
limitations are in [human-benchmark.md](human-benchmark.md). This report records
the implemented feature and actual acceptance evidence, rather than measured
human performance. Automated production responses belong only to `smoke`.

## Live entry points and deployment

- Main consent page: https://captcha-challenges-web.deploywright.workers.dev/human-benchmark
- Pilot consent page: https://captcha-challenges-web.deploywright.workers.dev/human-benchmark?cohort=pilot
- Authenticated resumable player: https://captcha-challenges-web.deploywright.workers.dev/human-benchmark/run
- Existing home/browsing/challenge experience remains available.

Worker `captcha-challenges-web` was deployed successfully with OpenNext Cloudflare.
The deployed version is `4d18b435-c9aa-43ce-abec-2f870139258c`, with a reported
17 ms startup and 966.72 KiB compressed Worker bundle. `ASSETS` remains bound.
Next 15.5.27, OpenNext 1.20.7, and Wrangler 4.145.0 were used.

The dedicated D1 database is `captcha-human-benchmark`, real database ID
`a88c2d6f-d809-4de4-beeb-ebf11347dc26`, binding `HUMAN_BENCHMARK_DB`.
`0001_human_benchmark.sql` was applied locally and remotely. Wrangler's remote
migration listing confirmed no migrations remain. The production admin secret
`HUMAN_BENCHMARK_ADMIN_KEY` was uploaded from ignored local `.dev.vars` using
Wrangler's protected file input. No secret value is committed or reported.

## Protocol, authentication, and stored data

Protocol **human-v1** persists all 40 ordered assignments in an atomic batch
before activating a session. It reserves exposure counts with a transactional
revision so concurrent starts cannot silently reuse a stale balancing snapshot.

| Stage | Variant | Assigned per session |
| --- | --- | ---: |
| Level 1 | street-grid | 6 |
| Level 2A | hard-street-grid | 6 |
| Level 2B | checker-shadow | 6 |
| Level 3A | routing-puzzle | 18 |
| Level 3B | degraded-vision | 4 |

All six illusions, all four routing subtypes, all five routing difficulties,
and four distinct degraded series are included. No challenge ID repeats.
Seeded ordering mixes variants and limits consecutive runs to three. Assignment
uses least-exposed candidates and deterministic tie breaking, independent of
answers. Exposure is separated by protocol and cohort.

The fixed timeout is **120,000 ms** after visual assets are ready. A monotonic
client clock records primary interaction time; presentation/final timestamps
provide the server audit interval. Refresh retains elapsed time. Submit, skip,
and timeout freeze timing once; retry sends the saved payload. Hidden tabs set
only a Boolean interruption flag. Skips and timeouts are primary failures.

A random anonymous participant UUID lives in a one-year first-party cookie.
A separate random 256-bit session token uses HttpOnly, SameSite=Lax, Path=/,
Secure on production HTTPS, with a 30-day lifetime. D1 stores only its SHA-256
hash. An opaque trial UUID and canonical payload fingerprint provide finality:
identical accepted delivery succeeds, changed replay fails, and current-trial
checks prevent arbitrary challenge selection or advancing out of order.
Same-origin mutation checks, strict 4 KiB JSON limits, answer validation, and
anonymous request windows are applied server-side.

Normalized tables store:

- `human_participants`: UUID and creation timestamp.
- `human_sessions`: anonymous IDs, hashed token, protocol/cohort, seed/revision,
  status, consent and session timestamps, coarse device/viewport categories,
  assigned/answered/skipped/timeout counters.
- `human_trials`: immutable assignment position/challenge and public metadata,
  presentation/final timestamps, submitted answer JSON, private correctness,
  skip/timeout, client/server time, interruption, and submission fingerprint.
- `human_challenge_exposure`: assigned/finalized counts by protocol/cohort/ID.
- `human_protocol_state` and `human_rate_limits`: transaction and abuse controls.

Constraints enforce unique session positions/challenges/degraded scenes, final
trial immutability, consistent terminal states, and one main session per browser
participant/protocol. Indexes support participant/current trial and analysis.
No name, email, phone, IP, location, account, social handle, full user-agent,
precise viewport dimensions, browser fingerprint, or correct answer registry
is stored. Only desktop/tablet/mobile and small/medium/large context is retained.

## Participant and admin behavior

The home CTA links to consent. Start remains disabled without consent and the
server independently requires consent. The dedicated player reuses the three
renderers with `benchmarkMode`: task instructions/assets/options remain, while
experimental badges are hidden. Zoom uses the same public stimulus, including
already degraded images. Keyboard, button labels, focus, and inspection-dialog
semantics are maintained.

The server calls the existing private `gradeSubmission`. Active responses contain
only acceptance/progress; no score, correct option, explanation, or hint is sent.
Accepted trials cannot be retried with changed answers or revisited. Refresh
resumes the frozen next incomplete trial. Only after all 40 finalize does the
participant see aggregate accuracy, median time, skip/timeout counts, and thanks.
No individual outcomes or Gemini comparison is shown. Completed main participants
see the already-completed notice. Explicit stop retains an abandoned record.

Bearer authentication with the admin secret protects these endpoints:

```text
GET /api/human-benchmark/admin/summary
GET /api/human-benchmark/admin/export.json
GET /api/human-benchmark/admin/export.csv
```

Summary defaults to completed `main` sessions, excluding pilot and smoke.
Primary accuracy includes skips/timeouts in its denominator; answered-only
accuracy is secondary. Median/nearest-rank p95 and 95% Wilson intervals accompany
overall, stage, variant, subtype, routing difficulty, degraded resolution, and
series metrics where samples exist. JSON exports page at 500 rows with a cursor;
CSV streams bounded batches and escapes spreadsheet formulas. Anonymous IDs,
protocol/cohort, assignment metadata, responses, stored outcomes, times, and
interruption are exported; credentials and identifying data are excluded.
The optional dashboard was omitted in favor of the completed API and exports.

## Local checks and balance simulation

| Check | Actual result | Retained evidence in repository root |
| --- | --- | --- |
| `npm test` | 42 passed in 7 files; includes 17 existing checks and 25 human checks | `.tmp/human-unit-tests.log` |
| Workerd/D1 integration | Real migration, concurrent starts/submits, consent/authentication, validation, skip/timeout, replay, resume, completed locking, cohort exclusion, authenticated exports passed | same unit log; `web/tests/human-api.test.ts` |
| Assignment | 100 seed invariants and 30-participant simulation passed | same unit log; `web/tests/human-assignment.test.ts` |
| Timing | 8 tests passed, including immutable zero-time skip before image readiness | same unit log; `web/tests/human-clock.test.ts` |
| Browser suite | 10 passed; 2 intentionally skipped redundant tablet/mobile full-session repetitions | `.tmp/human-browser-all.log` |
| Final timing/browser regression | 3 passed, one per desktop/tablet/mobile, after the last clock fix | `.tmp/human-browser-pending.log` |
| Browser privacy | Transitive client import audit and final built JavaScript audit passed | `.tmp/human-built-client-leak.log` |
| `npm run lint` | No warnings or errors | `.tmp/human-lint.log` |
| `npm run build` | Successful Next build, 141 static pages generated | `.tmp/human-next-build.log` |
| `npm run build:worker` | Successful final Next/OpenNext Worker build | `.tmp/human-worker-build.log` |
| Wrangler dry run | Successful packaging with D1 and ASSETS bindings | `.tmp/human-worker-dry-run.log` |
| Production dependency audit | Zero reported vulnerabilities | `.tmp/human-production-audit-dependencies.json` |

Browser tests exercised all five visual families, grid inspection of the same
image, routing zoom/expand, accessible Escape handling, no horizontal overflow,
consent, delayed asset readiness, refresh, identical saved-response retry,
automatic timeout, skip, and final aggregate-only completion. Normal challenge
mode still returns immediate feedback with Try Again/Try Another and progression.
Tests are restricted to local D1, including synthetic main fixtures.

Thirty simulated participants produced these challenge exposure bounds:

| Variant | Minimum | Maximum | Mean |
| --- | ---: | ---: | ---: |
| street-grid | 9 | 9 | 9 |
| hard-street-grid | 9 | 9 | 9 |
| checker-shadow | 30 | 30 | 30 |
| routing-puzzle | 8 | 10 | 9 |
| degraded-vision | 4 | 5 | 4.286 |

Resolution totals across the seven ladders were six counts of 17 and one count
of 18. Every routing subtype/difficulty and all 28 degraded challenges received
coverage, with no repeated degraded scene within a participant.

## Production acceptance evidence

The first complete smoke session finalized all 40 trials and checked live D1,
every assigned asset, stage quotas, authentication, secure HttpOnly cookies,
hidden active correctness, skip/timeout, identical first/last replay, changed
replay rejection, completed-session write protection, aggregate-only completion,
and authenticated summary/JSON/CSV exports. Evidence is retained in
`.tmp/human-production-smoke-api.json`.

A supplementary run explicitly waited for browser presentation acknowledgement
at desktop/tablet/mobile sizes, submitted the first response through the live
mobile UI, and checked progression before completing the remaining trials with
the controlled API driver. Its final evidence is
`.tmp/human-production-smoke.json` and `.tmp/human-production-smoke.log`.
Production screenshots are `.tmp/human-production-{desktop,tablet,mobile}.png`
and `.tmp/human-production-completed.png`.

Two production smoke sessions completed, totaling **80 finalized test trials**.
An intermediate harness attempt submitted one response successfully but failed
when reading that response after browser navigation. The harness now consumes
the response before navigating; the incomplete smoke session was retained as
`abandoned`, with its one accepted response preserved. Future failed runs also
attempt an authenticated stop. These test records are excluded from main and
abandoned records are excluded from completed-session smoke summaries. No fake
main record was created; main completed-session counts remained zero.

Independent read-only production browser checks confirmed the home CTA, disabled
then enabled consent button for both main/pilot pages, the existing normal
renderer, 401 protection for all admin routes, cross-origin rejection, and
consent rejection before any session creation. Evidence:
`.tmp/human-production-readonly.json`. No main session was created by these checks.
Authenticated default summary and both default exports were also checked live:
main has zero completed sessions/export rows, empty proportions and confidence
intervals are null, and default CSV contains only its header. Evidence:
`.tmp/human-production-main-exclusion.json`.

The remote SQL audit is retained in `.tmp/human-production-db-audit.json`, using
`.tmp/human-production-audit.sql`; it checks session/trial/exposure totals, unique
assignment positions and IDs, degraded scene isolation, routing coverage,
hash lengths, table field names, and foreign-key integrity.
The audit confirmed 40 unique positions and challenge IDs in each of the three
smoke assignments, four distinct degraded scenes/resolutions each, and all four
routing subtypes/five difficulties each. Exposure totals match 120 assigned and
81 finalized trials (80 complete-session trials plus the abandoned response).
Only smoke cohort records exist, all token hashes have 64 hex-character lengths,
and `PRAGMA foreign_key_check` returned no violations.

## Files created or modified

All source changes are under `web/`. The frozen `AI-Solver/` and `challenges/`
trees have zero changes relative to the pre-feature commit `346db82`.

- Pages/styles: `app/page.tsx`, `app/globals.css`,
  `app/human-benchmark/page.tsx`, `app/human-benchmark/run/page.tsx`.
- Participant routes: `app/api/human-benchmark/session/route.ts`,
  `present/route.ts`, `trial/route.ts`, `stop/route.ts` under the same prefix.
- Admin routes: `app/api/human-benchmark/admin/summary/route.ts`,
  `export.json/route.ts`, `export.csv/route.ts` under the same prefix.
- Player/consent: `components/human-benchmark/HumanBenchmarkPlayer.tsx`,
  `HumanBenchmarkLanding.tsx` in that directory.
- Renderer opt-in props/accessibility: `components/challenges/ImageGridChallenge.tsx`,
  `BinaryChoiceChallenge.tsx`, `RoutingPuzzleChallenge.tsx`.
- Normal JSON typing compatibility only: `components/challenges/ChallengePlayer.tsx`,
  `app/api/challenges/[challengeId]/submit/route.ts`.
- Protocol/server/analysis library: `lib/human-benchmark/protocol.ts`,
  `types.ts`, `assignment.ts`, `clock.ts`, `metrics.ts`, `security.server.ts`,
  `store.server.ts`, `service.server.ts`, `api.server.ts`, `analytics.server.ts`,
  `admin.server.ts` in that directory.
- Storage/config: `migrations/0001_human_benchmark.sql`, `wrangler.jsonc`,
  generated `env.d.ts`, `.dev.vars.example`, `.gitignore`, `package.json`,
  `package-lock.json`.
- Verification: `tests/human-api.test.ts`, `human-assignment.test.ts`,
  `human-client-leak.test.ts`, `human-clock.test.ts` in that directory;
  `vitest.config.ts`, `playwright.config.ts`, `e2e/human-benchmark.spec.ts`,
  `scripts/human-smoke.mjs`.
- Documentation: `docs/human-benchmark.md` and this verification report.

## Limitations

This is an anonymous project benchmark, not a representative population study.
Participants form a convenience sample; attrition, recruitment, cookie clearing,
and repeat browsers can bias data. Timing and independent participation rely
partly on client reporting and consent. Wilson intervals are descriptive across
trials, without participant/scene cluster adjustment. Stage weights differ from
the 134-trial Gemini baseline and require prespecified alignment in future
comparisons. Illusion public metadata lacks named subtype fields; distinct IDs
remain available for analysis. No IRB approval, representative human estimate,
or human-versus-Gemini performance claim is made.
