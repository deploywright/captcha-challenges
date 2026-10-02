# Production session comparison

The reviewable diagnostic artifacts are [candidate-vs-gemini.pending.md](candidate-vs-gemini.pending.md), [JSON](candidate-vs-gemini.pending.json), and [figure](candidate-vs-gemini.pending.png). Production D1 has no completed `creator` session. Its sole completed non-smoke session is stored as `main`, with ID `73fac77a-7985-4755-a26d-16ea9046541f`. The user explicitly excluded this record from Creator Baseline attribution.

A correct completed `human-v1` record stored in `creator` must be identified before generating the attributed `creator-vs-gemini.json` and `.md`. The stored `main` record remains unchanged and unattributed. Matching the supplied UI accuracy does not establish participant identity.

Run these commands from the repository root:

```powershell
python reports/creator-vs-gemini/generate_comparison.py --unattributed-draft
python -m unittest discover -s reports/creator-vs-gemini -p test_comparison.py -v
```

The generator refuses main-cohort attribution and has no confirmation override. The anonymous diagnostic draft can be regenerated with `--unattributed-draft`.

Generation requires Python, NumPy and Matplotlib. Tests additionally use SciPy for an independent exact binomial calculation. Inputs are the frozen canonical aggregate JSON, its five referenced raw run directories, the public challenge catalog, and `.tmp/creator-comparison-production-audit.json`. That ignored local production snapshot contains submitted participant responses and must remain private. Reproduction on another checkout requires an authorized read-only export; reports alone cannot reconstruct those private input rows.

Generation performs no network requests, model inference, submissions or database writes. Source hashes are recorded in report provenance. Public artifacts contain correctness outcomes and public challenge metadata, without submitted responses, model predictions, credentials, participant identifiers or answer keys. The `creator` JSON keys preserve the requested schema; `report_status`, `analysis_label`, `identity_confirmation` and the actual `cohort` identify the pending attribution explicitly.

[Production revalidation](production-revalidation.json) records an earlier read-only D1 check: the requested trial audit fields, excluding submitted responses, remained identical to the private snapshot. [Session investigation](creator-session-investigation.md) and its [JSON evidence](creator-session-investigation.json) contain newer D1, deployment, and controlled browser evidence. No provider credentials or benchmark rerun are needed for this analysis.
