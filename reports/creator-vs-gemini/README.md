# Creator vs Gemini

The final report is [creator-vs-gemini.md](creator-vs-gemini.md), with structured metrics in [creator-vs-gemini.json](creator-vs-gemini.json) and comparison figures beside them. The participant directly confirmed session `73fac77a-7985-4755-a26d-16ea9046541f` as their completion through the production Creator Baseline URL. The session remains stored as `cohort=main`; the report uses `analysis_role=creator` under the exact, versioned attribution record in [creator-attribution.json](creator-attribution.json).

The session predates production Creator cohort support. Investigation reproduced the landing-page bug: an active session cookie could be resumed from another cohort URL. The UI now resumes only a same-cohort session and explains active cross-cohort conflicts; the server continues to reject a cross-cohort start with HTTP 409. No production D1 rows were modified or relabeled. Main and all-cohort aggregate summaries exclude this exact creator-role record and report the exclusion count; raw exports retain the stored cohort and add `analysis_role`.

The final generator accepts the historical main record only when the exact confirmed session ID and all saved completion invariants match: human-v1, completed, 40 assigned/finalized trials, 30 correct, 3 skips including 1 timeout, 7.7-second median as displayed, frozen stage quotas, and 40 unique challenge IDs. It has no generic main-session attribution override.

Run these commands from the repository root:

```powershell
python reports/creator-vs-gemini/generate_comparison.py
python -m unittest discover -s reports/creator-vs-gemini -p test_comparison.py -v
```

Generation uses the ignored read-only D1 audit snapshot, committed attribution record, public challenge catalog, frozen Gemini aggregate, and its five raw run directories. It performs no network requests, model inference, submissions, or database writes. Source hashes are recorded in the report. Public artifacts contain correctness outcomes and public challenge metadata, without submitted responses, model predictions, credentials, token hashes, participant IDs, or answer keys. The ignored audit snapshot contains participant response data and must remain private.

[Production revalidation](production-revalidation.json) and [session investigation](creator-session-investigation.md) document read-only D1 checks, deployment timing, and the reproduced routing cause. No benchmark rerun was performed.
