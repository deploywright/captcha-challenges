# Production session comparison

The reviewable artifacts are [candidate-vs-gemini.pending.md](candidate-vs-gemini.pending.md), [JSON](candidate-vs-gemini.pending.json), and [figure](candidate-vs-gemini.pending.png). Attribution is pending: production D1 has no completed `creator` session. Its sole completed non-smoke session is stored as `main`, with ID `73fac77a-7985-4755-a26d-16ea9046541f`.

Confirmation that the creator personally completed that exact session is required before generating the attributed `creator-vs-gemini.json` and `.md`. The stored cohort remains `main`; no database record is relabeled. Matching the supplied UI accuracy does not establish participant identity.

Run these commands from the repository root:

```powershell
python reports/creator-vs-gemini/generate_comparison.py --unattributed-draft
python -m unittest discover -s reports/creator-vs-gemini -p test_comparison.py -v
```

After explicit confirmation, the generator accepts `--confirmed-session-id` with the confirmed ID. Do not supply that flag merely to bypass the identity check.

Generation requires Python, NumPy and Matplotlib. Tests additionally use SciPy for an independent exact binomial calculation. Inputs are the frozen canonical aggregate JSON, its five referenced raw run directories, the public challenge catalog, and `.tmp/creator-comparison-production-audit.json`. That ignored local production snapshot contains submitted participant responses and must remain private. Reproduction on another checkout requires an authorized read-only export; reports alone cannot reconstruct those private input rows.

Generation performs no network requests, model inference, submissions or database writes. Source hashes are recorded in report provenance. Public artifacts contain correctness outcomes and public challenge metadata, without submitted responses, model predictions, credentials, participant identifiers or answer keys. The `creator` JSON keys preserve the requested schema; `report_status`, `analysis_label`, `identity_confirmation` and the actual `cohort` identify the pending attribution explicitly.

[Production revalidation](production-revalidation.json) records a subsequent read-only D1 check: the requested trial audit fields, excluding submitted responses, remain identical to the private snapshot. It also records that creator attribution is still pending. No provider credentials are needed to finish this analysis once session identity is confirmed.
