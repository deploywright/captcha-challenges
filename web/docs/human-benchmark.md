# Human Benchmark Mode

This is an anonymous project benchmark, not a representative population study.
Participants are a convenience sample unless later recruitment establishes
otherwise. Describe results as the "human benchmark sample" or "participants in
this benchmark", rather than claims about all humans or average human intelligence.
No IRB approval or academic study status is claimed.

## Frozen protocol: human-v1

The independent human experiment uses the existing, frozen 134-challenge
benchmark. Challenge content, grading rules, and the Gemini experiment remain
unchanged. `lib/human-benchmark/protocol.ts` commits the collection rules. Change
the protocol version before any material change to assignment, timing, or scoring
after collection begins; do not silently mix different rules under human-v1.

Each session receives exactly 40 assigned trials:

| Variant | Stage | Quota |
| --- | --- | ---: |
| street-grid | Level 1 | 6 |
| hard-street-grid | Level 2A | 6 |
| checker-shadow | Level 2B | 6 |
| routing-puzzle | Level 3A | 18 |
| degraded-vision | Level 3B | 4 |

Every session includes all six frozen visual illusions. Routing covers all four
subtypes and five difficulties, preferring fresh subtype/difficulty strata and
least-exposed challenge IDs. The actual routing pools have **2/3/5/3/2 challenges
per subtype across easy/medium/story/hard/extreme**. Exactly one per stratum would
overexpose the smaller pools and undersample story. Assignment therefore prefers
least-exposed IDs first, distinct strata next, reserves subtype/difficulty
coverage, and rotates strata omissions. Fresh, equally exposed pools select 18
distinct strata; later sessions may repeat some strata to balance challenge IDs.

Level 3B selects exactly one challenge from each of four distinct `seriesId`
values. A participant never sees another resolution of the same scene in that
session. Lowest-assigned candidates within each scene take priority. Among those
candidates the algorithm maximizes resolution diversity, then prefers less-used
resolutions globally. The ladder is 64, 48, 32, 24, 16, 12, and 8 pixels.

Tie-breaking and mixed order are deterministic from a cryptographically random
session seed. The order avoids runs longer than three of the same variant when
feasible. No duplicate challenge ID is assigned. Assignment never depends on
correctness. The complete ordered list and analysis metadata are persisted
before returning the first trial.

Exposure snapshots use a protocol/cohort revision. A D1 transactional batch
reserves that revision, inserts the session and 40 trials, and increments
exposures through SQL triggers. Concurrent stale reservations roll back and
recompute; partially created sessions cannot escape. Assigned/completed exposure
counts are partitioned by protocol and cohort, so smoke/pilot/creator do not influence
main assignments. Completed exposure counts mean finalized trials, including
skips and timeouts.

## Participation and privacy

`/human-benchmark` explains 40 trials, anonymous recording, no correctness
feedback, working independently without external tools/AI/search/screenshots/
other people, voluntary stopping, and the required consent checkbox. Starting
without consent is also rejected server-side. The normal browsing experience
continues at `/challenges` and `/challenge/[challengeId]`.

Stored data contains anonymous participant/session/trial IDs, protocol/cohort,
assignment metadata, consent/session/trial timestamps, answers, private grading
outcomes, timing, and a Boolean interruption flag. Coarse technical fields are
only `device_class` (desktop/tablet/mobile) and `viewport_bucket`
(small/medium/large). These approximate the layout category, without collecting
the user-agent or precise viewport dimensions. No name, email, phone, IP,
location, account, social profile, or browser fingerprint is requested or saved.

A random participant UUID lives in an HttpOnly first-party cookie for one year.
The cryptographically random 256-bit session secret lives only in a separate
HttpOnly, SameSite=Lax, Path=/ cookie, Secure on HTTPS, for 30 days. D1 stores
only its SHA-256 hash. Browser JavaScript cannot read the session secret; public
session/participant IDs cannot authenticate an API mutation. Clearing or losing
cookies can prevent resuming a session and defeats browser-level repeat
prevention; this is deliberately not identity enforcement.

SessionStorage retains the local trial clock and an unconfirmed frozen payload
so refresh/network retry cannot change an already submitted response. It contains
no credential or correct answer. No detailed visibility/browsing history is
collected. Cloudflare's independent service-level processing is outside this
application database; Human Benchmark handlers do not log requests, cookies,
headers, answers, or exception bodies.

## Interaction and timing

`/human-benchmark/run` uses a dedicated player and the existing visual renderers
with an opt-in benchmark mode. Instructions and public images remain visible;
subtype/difficulty/seed/scene/resolution badges are hidden. Zoom enlarges the same
public asset, including the already degraded image, without retrieving a better
source. Inspection dialogs support keyboard focus, Escape, and focus trapping.

The primary client timer starts once, only after every required image has loaded.
A separate authenticated presentation call records server `presented_at`.
Submit, skip, or timeout stops the clock once; transport retries reuse the same
frozen payload/time. The limit is **120,000 ms for every trial**. Background tabs
do not pause it. Page visibility changes set only `interrupted=true`, without
automatically invalidating the response.

Refresh resumes the persisted next incomplete trial. An already presented trial
retains elapsed time; a local wall-clock snapshot reconstructs the interrupted
interval, with server elapsed as a backstop. This includes time spent refreshing
or away after initial presentation. It does not grant a fresh two-minute window.
Client timing is self-reported and can be tampered with; server elapsed is a
coarse audit measure and includes readiness-request/network latency differences.
An answer beyond the server limit is recorded as a timeout, with no success.

Broken images offer reload of the same stimulus or a final skip. A skip before
presentation is recorded with zero client time and excluded from latency samples
but remains a primary accuracy failure. An offline timeout remains frozen until
the same payload can be accepted. No new answer or hints are offered.

Leaving the page keeps an active session resumable. Explicit permanent stop marks
it abandoned; accepted data remains saved and the main session cannot restart.
Partially completed/abandoned sessions are available in exports but excluded from
completed-session headline analysis. This attrition can bias the observed sample.

## Scoring and finality

The server derives the current trial from the authenticated session, validates
answer types against public UI options or tile ranges, and calls the existing
server-only `gradeSubmission`. No private registry enters browser imports.

Active submission responses contain only `accepted`, progress, and `hasNext`.
No correctness, score, explanation, hint, ground truth, or per-trial feedback is
returned. After all 40 trials, the participant sees only overall personal accuracy,
median solve time, skips (including timeouts), and timeout count. No per-question
outcomes or Gemini comparison are shown even then.

An opaque trial UUID identifies idempotent delivery; it cannot select a different
challenge. The canonical payload fingerprint makes an identical accepted replay
safe, including delivery of the last trial after completion. A changed payload
is rejected. SQL conditional updates and triggers prevent concurrent duplicate
counts or modifications to a final trial. Completed/abandoned sessions reject
new writes. No accepted trial is shown again.

Primary exact accuracy is **correct finalized assigned trials / all finalized
assigned trials in completed sessions**. For a participant this is correct/40.
Skips and timeouts are failures and stay in the denominator. Answered-only accuracy
is explicitly secondary; it never replaces the headline metric.

Admin metrics map variants to Level 1, 2A, 2B, 3A, and 3B instead of collapsing
numeric levels. Groupings cover variant/stage, public subtype, routing difficulty,
degraded resolution, and series. Current illusion public metadata does not name
subtypes; all six are included and exports retain their distinct challenge IDs.
95% Wilson intervals are supplied where samples exist. These trial-based
intervals are descriptive and do not adjust for clustering by participant or
scene. Latency median and nearest-rank p95 include all finalized, presented
trials, including skips/timeouts; no timing is invented for unseen stimuli.

## D1 schema and local development

Binding: `HUMAN_BENCHMARK_DB`. Dedicated production database:
`captcha-human-benchmark`, ID `a88c2d6f-d809-4de4-beeb-ebf11347dc26`.

`migrations/0001_human_benchmark.sql` defines the original schema:

- `human_participants`: anonymous UUID and creation time.
- `human_sessions`: hashed token, protocol/cohort, seed/revision, status,
  consent/start/completion timestamps, coarse context, counters.
- `human_trials`: immutable position/challenge and public analysis metadata,
  presentation/final timestamps, serialized answer, private correctness,
  skip/timeout, client/server timing, interruption, submission fingerprint.
- `human_challenge_exposure`: assigned/finalized counts per challenge/cohort/protocol.
- `human_protocol_state`: transactional assignment revision.
- `human_rate_limits`: anonymous participant/session request windows.

Constraints include unique session position/challenge, unique degraded scene,
one main session per participant/protocol, fixed quota count, valid states, and
consistent skip/timeout/finality. Analysis/current-trial indexes cover protocol,
cohort, status, participant, challenge, variant, subtype/difficulty, and resolution.
No ground truth selection is stored.

Installed framework versions: Next 15.5.27, OpenNext Cloudflare 1.20.7,
Wrangler 4.145.0. Binding access uses `getCloudflareContext({async:true})`.
The existing ASSETS binding, Worker name, and compatibility settings are preserved.
The PostCSS dependency is overridden to the patched 8.5.28 line across the
dependency tree, retaining Next 15; production dependency audit is clean.
Workers invocation logs are disabled and query strings redacted. Trace support
is enabled without persistence; benchmark handlers never log credentials or payloads.

```bash
cd web
npm ci
cp .dev.vars.example .dev.vars
# Replace its admin value with a local random secret; keep .dev.vars ignored.
npx wrangler d1 migrations apply HUMAN_BENCHMARK_DB --local
npm run cf-typegen
npm run dev
```

Visit `/human-benchmark?cohort=pilot` for a local pilot. Next dev uses OpenNext's
existing local binding proxy; it does not require production D1 credentials.
Worker preview uses the same local D1 state:

```bash
npm run build:worker
npm run preview:worker
npx wrangler d1 execute HUMAN_BENCHMARK_DB --local --command "SELECT cohort,status,COUNT(*) FROM human_sessions GROUP BY cohort,status"
```

Migration application is tracked by Wrangler and can be run again safely; do not
manually execute the initial CREATE statements repeatedly against an existing DB.

## Cohorts, administration, and export

`main` is the default genuine-participant cohort and allows only one session per
browser/protocol. Pilot uses the same 40-trial interaction and is separate.
`creator` records the single-participant creator baseline using the same protocol.
`smoke` creation additionally requires the admin Bearer key. Default analysis and
export select **main only**; request `?cohort=pilot`, `smoke`, `creator`, or `all` explicitly
when needed. Never generate synthetic main data on production. Unit/browser tests
use isolated/local D1; production automated checks must use smoke.

All administration requires `Authorization: Bearer <HUMAN_BENCHMARK_ADMIN_KEY>`:

```text
GET /api/human-benchmark/admin/summary
GET /api/human-benchmark/admin/export.json
GET /api/human-benchmark/admin/export.csv
```

Summary returns aggregates only, computed in D1 without loading answers.
JSON export contains up to 500 rows plus `nextCursor`; repeat with `?cursor=...`
until null, retaining the chosen cohort parameter. CSV streams all matching rows
with bounded batches and quotes/escapes cells, neutralizing spreadsheet formulas.
Exports contain anonymous IDs, protocol/cohort, trial metadata, participant
answer (serialized JSON), stored correctness/skip/timeout, timing/interruption,
and relevant timestamps. They never include token hashes, raw cookies, seeds,
rate-limit buckets, IPs, or identity data. The optional admin dashboard is omitted;
the authenticated API and exports are the supported administration interface.

Mutation origin checks compare the browser Origin with the HTTP host/protocol
(including Next's local URL reconstruction) and reject cross-site requests.
Anonymous per-participant start/per-session mutation limits discourage obvious
repeated abuse without IP storage. They do not stop an attacker clearing cookies
or creating many anonymous browsers. The ordinary public grading endpoint remains
available outside benchmark mode; compliance with independent participation relies
on participant consent rather than strong anti-cheating enforcement.

## Checks and deployment

```bash
npm test
npm run lint
npm run build
npm run build:worker
npx playwright install chromium
npx playwright test
```

Browser tests are restricted to localhost and local D1. They cover consent,
assets-ready timing, identical delivery retry, refresh, timeout/skip, all visual
families on desktop/tablet/mobile, degraded inspection, completed-session summary,
and normal-mode verification/progression. Unit tests use workerd-backed D1 with
the real migration, test concurrent assignment/submission, and simulate 30
participants. A transitive import and built-browser-JavaScript audit checks that
private grading never enters the client bundle.

Production deployment is explicitly authorized for this feature:

```bash
npx wrangler d1 migrations apply HUMAN_BENCHMARK_DB --remote
# Configure HUMAN_BENCHMARK_ADMIN_KEY using Wrangler secret input, never CLI values.
npm run deploy
```

Controlled production verification, after deployment, uses only smoke sessions:

```bash
node scripts/human-smoke.mjs https://captcha-challenges-web.deploywright.workers.dev
```

It reads the admin key from the local environment or ignored `.dev.vars`, checks
all 40 assigned trials, desktop/tablet/mobile rendering, idempotency, completion,
and authenticated summary/exports. It verifies main completed-session counts
remain unchanged. Smoke timing/answers are test inputs, not human observations.

Binding and transaction patterns follow the installed SDK and the
[OpenNext bindings documentation](https://opennext.js.org/cloudflare/bindings)
and [D1 batch API](https://developers.cloudflare.com/d1/worker-api/d1-database/#batch).

Keep the real D1 ID/binding and existing `captcha-challenges-web`/ASSETS behavior.
Apply schema before publishing code that uses it. Configure the admin secret from
a protected local input/file, without committing it. Record deployment and smoke
evidence separately. Do not present smoke outcomes as measured human performance.

## Creator baseline

Open `/human-benchmark?cohort=creator` to personally record the project's
**single-participant creator baseline**. The landing notice explains that this
reference is stored separately from the main human sample. Consent, independent
work without AI/search/external tools/screenshots/other people, asset-ready timing,
no-feedback behavior, resume, server-side grading, quotas, and the two-minute
timeout are exactly those of human-v1. Completion is labeled "Creator baseline
complete" and shows only the existing personal aggregate statistics.

Only one creator session per anonymous participant/protocol is allowed, including
an abandoned session, just as for main. A separate partial unique index enforces
this in D1; the same participant may still have main, pilot, and creator records.
The existing active-session rule remains: finish or permanently stop an active
session in another cohort before starting creator in that browser. Accepted
records in the other cohort remain saved; no session is moved into creator.
Cookies are browser continuity rather than identity enforcement. The public URL
does not verify that the participant is the project creator; administratively
identify the actual creator's anonymous record if additional browsers use it.
No creator result should be described as representative human performance.

`migrations/0002_creator_cohort.sql` extends the two cohort CHECK constraints in
`human_sessions` and `human_protocol_state` without editing 0001. It copies rows
into replacement tables, restores the original table names/indexes/triggers,
and adds `human_one_creator`. Foreign-key checks are deferred only within the
migration transaction, following [D1 foreign-key migration guidance](https://developers.cloudflare.com/d1/sql-api/foreign-keys/).
Existing participants, trials, token hashes, exposure, state, and rate-limit data
are retained. Apply with the same local/remote Wrangler migration commands above.
No database or binding recreation is needed.

Admin summary and both exports accept `?cohort=creator`; `?cohort=all` explicitly
includes it. Default main queries exclude creator. Exposure/state for creator is
also isolated. Export fields, privacy rules, scoring formulas, quantiles, and
Wilson intervals are unchanged. The creator summary is descriptively labeled as
a single-participant baseline, not a population estimate.

For an admin-only descriptive comparison, retrieve
`/api/human-benchmark/admin/summary?cohort=creator` using the existing Bearer
authentication and read `by.stage[stage].primaryExactAccuracy`. Leave creator
values blank until the user has completed the session; do not substitute automated
smoke results or create a fake creator observation.

| Stage | Creator primary exact accuracy | Frozen Gemini zero-shot baseline |
| --- | --- | ---: |
| Level 1 | Not yet collected; read creator stage metric | 70.0% |
| Level 2A | Not yet collected; read creator stage metric | 55.0% |
| Level 2B | Not yet collected; read creator stage metric | 100.0% |
| Level 3A | Not yet collected; read creator stage metric | 43.3% |
| Level 3B | Not yet collected; read creator stage metric | 10.7% |

The creator has 6/6/6/18/4 assigned trials versus Gemini's 20/20/6/60/28.
Compare stages descriptively and keep the differing denominators visible. Do
not equate raw overall percentages without a prespecified weighting policy.
This comparison belongs in docs/admin analysis only; the participant interface
contains no Gemini results. The frozen Gemini experiment is not modified or rerun.

Production automation must **never start or complete a creator session**.
Verify creator writes locally with the real migrations and use only `smoke` for
production mutation tests. Production creator UI/admin checks remain read-only;
the user personally opens the creator URL and completes all 40 challenges.

## Limitations

The benchmark is a convenience sample with possible attrition/recruitment bias.
Cookies are anonymous continuity controls, not verified identity. Timing and
independence are not tamper-proof. All sessions have the same quotas, so stage
weights differ from the 134-challenge Gemini population; any future comparison
must align stages and use a prespecified weighting policy rather than equating
raw overall percentages. No public human-versus-Gemini claim is made here.
