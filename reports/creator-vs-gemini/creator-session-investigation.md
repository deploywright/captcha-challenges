# Creator session storage investigation

Production D1 checked at 2026-10-02T18:15:50.452Z. Database: `captcha-human-benchmark` (`a88c2d6f-d809-4de4-beeb-ebf11347dc26`).

**No completed creator session exists:** completed human-v1 creator records = 0; creator records across all statuses = 0. The main record is not attributed to the user and must not be used as the Creator Baseline.

## Production records

| Cohort | Status | Sessions |
| --- | --- | ---: |
| main | completed | 1 |
| pilot | abandoned | 1 |
| smoke | abandoned | 1 |
| smoke | completed | 3 |

No creator assignment revision or challenge-exposure rows are present. The deployed schema permits creator and has the creator-specific unique index. The missing session is not explained by an unapplied creator schema migration.

## Timeline of the unattributed main record

This timeline describes an anonymous production record, not the creator's identity.

| Event | UTC |
| --- | --- |
| Main record created | 2026-10-02T15:50:39.080Z |
| Creator schema migration applied | 2026-10-02 16:23:36 UTC |
| Creator-support Worker deployed | 2026-10-02T16:25:20.996214Z |
| Main record completed | 2026-10-02T17:25:47.183Z |

Creator-support version: `ed26276e-ee49-486d-815c-917423858a43`. Current deployment versions: `ed26276e-ee49-486d-815c-917423858a43` (100%).

The main record was created before creator support existed. Its first trial was interrupted and finalized much later; those timing fields do not identify a participant or prove which URL was visited.

## Confirmed mechanisms

1. **Before creator deployment:** the old landing route accepted only pilot as an alternative to main. A creator query therefore fell back to main. This is verified in the pre-extension Git source, not by reproducing a historical deployment.
2. **Current landing recovery:** the URL selects the Creator Baseline notice, but the landing page fetches the cookie-bound session without a requested-cohort check. Its active-session branch offers Resume for any active cohort. The completed-session branch checks the cohort; the active-session branch does not.
3. **Resume navigation:** Resume opens `/human-benchmark/run`, which loads the cookie-bound session. It does not create, convert, or transfer a session to creator.
4. **Current fresh start:** Start sends the requested creator cohort, and server creation stores that value. A creator-start request with an active main cookie is rejected with HTTP 409; the server does not silently create a new main session.

The interface can therefore promise Creator Baseline storage while actually resuming an existing main session. This is a confirmed UI mismatch. It explains how visiting the Creator URL can end with main data without any database relabeling, but the historical path taken by the user remains unverified.

## Controlled production browser reproduction

The deployed HTML and JavaScript were loaded, but every participant API request was intercepted and fulfilled locally. No real session cookie was supplied. Completion values in these checks were synthetic, not a newly completed benchmark.

| Mocked initial state | Creator notice | Start visible | Mocked creator-start requests | Result |
| --- | --- | --- | ---: | --- |
| Unauthenticated browser | true | true | 1 | Creator baseline complete |
| Active main session | true | false | 0 | Benchmark complete |

[Screenshot: Creator notice with main-session Resume](creator-url-main-resume.png).

## Raw-row diagnostic validation

The excluded main record `73fac77a-7985-4755-a26d-16ea9046541f` has 40 assigned and 40 finalized trials, 40 unique positions and 40 unique challenge IDs. Raw outcomes: 30/40, median 7.683 seconds, 3 skips including 1 timeout; 37 answered. Session counters agree with raw rows: true.

These checks establish record consistency only. They do not establish creator identity, and the matching completion-screen values do not authorize attribution. There are no creator trial rows to validate.

## Limits and next action

D1 does not store the requested landing URL, browser navigation history, or an authenticated creator identity. The current evidence cannot determine whether the user first opened an unsupported creator query before deployment or later resumed another cohort through the misleading landing page.

No valid creator-cohort result can be generated from these records under the instruction to exclude main. The comparison remains an anonymous diagnostic draft. The generator's former main-session confirmation override has been removed, so it cannot publish that record as a Creator Baseline.

A future UI repair should check the existing cohort before offering Resume, state any cohort conflict clearly, and preserve the existing server rule and immutable assignments. Such a repair would prevent future confusion; it would not recover or change a missing historical creator record. No application code or deployment was changed during this investigation.

Production rows written: 0. Real participant API requests: 0. No migration, relabeling, model inference, or benchmark rerun was performed.

## Evidence and reproduction

[Structured investigation](creator-session-investigation.json) contains query results, deployment identity, browser checks, and source hashes. Submitted responses, provider predictions, cookies, token values, participant IDs, and private ground truth are omitted.

The relevant source files are `web/app/human-benchmark/page.tsx`, `web/components/human-benchmark/HumanBenchmarkLanding.tsx`, `web/components/human-benchmark/HumanBenchmarkPlayer.tsx`, and `web/lib/human-benchmark/api.server.ts`.

Run `node reports/creator-vs-gemini/investigate_creator_session.mjs` from the repository root after verifying the intended Wrangler account. The script runs SELECT queries only and blocks all real participant API traffic. Browser dependencies come from the existing web package. It writes investigation artifacts only.
