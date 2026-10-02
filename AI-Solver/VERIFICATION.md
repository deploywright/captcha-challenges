# AI-Solver v0.1 verification report

Verified on 2026-10-02 against `main` commit
`6b4cf5ed086f82d4c7dafa025956ce1145a703d1`, which matched `origin/main` when work
started. The existing `challenges/`, `web/`, and root README were unchanged.
The requested independent implementation exists; **live VLM acceptance remains
incomplete because the configured provider account has no API credits**.

## Files created

All implementation changes are inside `AI-Solver/`:

- Packaging/configuration: `pyproject.toml`, `.gitignore`, `.env.example`,
  `config.example.yaml`, `README.md`, `VERIFICATION.md`, `results/.gitkeep`.
- Package: `src/ai_solver/__init__.py`, `cli.py`, `config.py`, `contracts.py`,
  `client.py`, `runner.py`, `metrics.py`, `errors.py`, and `security.py`.
- Solvers: `src/ai_solver/solvers/__init__.py`, `base.py`,
  `random_baseline.py`, and `level_1_vlm.py`.
- Tests: `tests/conftest.py`, `test_contracts.py`, `test_client.py`,
  `test_runner.py`, `test_metrics.py`, `test_no_private_access.py`,
  `test_solvers.py`, `test_cli.py`, and `test_integration.py`.

A local `.env` sets the production origin and chosen model; its key was supplied
locally by the user. This file and benchmark run outputs are ignored by Git.
No credentials or benchmark outputs are included in the implementation deliverable.

## Provider and model

OpenAI Responses API, strict JSON Schema structured outputs, all nine tiles in
one inference request, default pinned model `gpt-4.1-mini-2025-04-14`.
The source implements a separate `VisionProvider` protocol and a generic
`Solver` protocol. A real SDK request/response round trip is unit-tested with
mocked HTTP, including the modern request shape and usage parsing.

The latest production VLM request, using the user's updated local API key,
failed with HTTP **429** and provider code
**`credit_balance_exhausted`**. Nine public assets loaded successfully; one
diagnostic provider request produced no selection, no usage, and no submission.
Its saved record is:

```text
results/20261002T082429451506Z_level1_vlm_ad2b38f4/predictions.jsonl
```

There were two earlier one-challenge attempts before the specific provider code
was exposed by the safe-code diagnostic. The initial attempt exhausted the
then-current bounded 429 retry policy (three requests); a second diagnostic
attempt made one request. No attempt yielded a prediction or evaluated answer.
The specific credit code was first captured in
`results/20261002T080702158949Z_level1_vlm_832c8420/`; after the user changed
the key, the latest attempt above independently confirmed the same account-level
failure. A resumed-goal check then tested the same locally configured key once
with automatic retries disabled and confirmed `credit_balance_exhausted` again.
It made exactly one provider request, recorded `parsing_status:
"not_received"` and `status: "completed_with_errors"`, and did not submit.
The final provider policy records known machine error codes and does not retry
documented credit, quota, or spend-limit errors. Raw provider error bodies and
secrets are excluded from result files. No five-challenge/full VLM run was started.

[Official OpenAI error guidance](https://developers.openai.com/api/docs/guides/error-codes)
identifies `credit_balance_exhausted` as exhausted prepaid API credits.
Restored API access is required before rerunning the first VLM stage.

## Test evidence

From `AI-Solver/`:

```text
python -m pytest -q
117 passed, 1 skipped

python -m ruff check .
All checks passed!

python -m ruff format --check .
22 files already formatted
```

The skipped test is the intentionally opt-in production integration test.
Normal tests block external HTTP and do not make real model calls. Coverage
includes strict contracts, dynamic variant filtering, every requested index
validation rule, HTTP allowlisting/cache/retries, wrong-answer non-retry,
one prediction per challenge, one output-format recovery, safe JSONL persistence,
latency/accuracy/cost handling, random determinism, and private-access guards.

Public integration was explicitly run with `CAPTCHA_BASE_URL` and
`RUN_AI_SOLVER_INTEGRATION=1`:

```text
python -m pytest tests/test_integration.py -q -s
Public integration: 20 street-grid challenges; 180 assets
1 passed in 68.06s
```

It performed public reads only, with no submissions or model calls. The live
catalog had 134 total entries and **20 dynamically discovered street-grid
challenges**. No population count is hardcoded in the implementation.

The package installed independently with:

```text
python -m pip install -e './AI-Solver[openai,test]'
```

A wheel was built with `pip wheel --no-deps`; its contents consist solely of
the `ai_solver` package and distribution metadata, without engine/web imports.

## Production dry run and controlled submission

```text
python -m ai_solver.cli benchmark --solver random --seed 42 --dry-run \
  --base-url https://captcha-challenges-web.deploywright.workers.dev
```

Completed all 20 challenges: 180 assets, 20 deterministic predictions, zero
errors, zero model requests, zero submissions. Accuracy correctly remains
`null`, because no evaluation occurred. Saved artifacts:

```text
results/20261002T075433793858Z_level1_random_047ab8f0/
  run.json
  predictions.jsonl
  summary.json
```

A single controlled production random-baseline submission was also exercised:

```text
python -m ai_solver.cli benchmark --solver random --seed 42 --limit 1 \
  --base-url https://captcha-challenges-web.deploywright.workers.dev
```

`lvl1_221ies`: nine assets loaded, HTTP 200, `correct=false`, one evaluated
prediction, zero errors, and no answer retry. Exact challenge accuracy for this
one random evaluation was 0/1. This is a protocol smoke test, not a VLM result
or a reliable estimate of full-population random performance. Artifacts:

```text
results/20261002T075805556431Z_level1_random_f0c51357/
```

Terminal evidence is retained in the repository's ignored `.tmp/` directory:
`ai-solver-unit-tests.log`, `ai-solver-integration.log`,
`ai-solver-dry-run.log`, `ai-solver-random-submit.log`,
`ai-solver-vlm-preflight.log`, and `ai-solver-vlm-diagnostic.log`.
The updated-key attempt also has `ai-solver-vlm-stage1.json` and
`ai-solver-vlm-stage1.progress.log`.
The resumed check has `ai-solver-vlm-resumed-stage1.json` and
`ai-solver-vlm-resumed-stage1.progress.log`.

## Remaining gate and deferred scope

After provider access is restored, use the configured local `.env`:

```bash
cd AI-Solver
python -m ai_solver.cli benchmark --variant street-grid --solver vlm --limit 1
# Inspect the successful one-challenge protocol and artifacts before advancing.
python -m ai_solver.cli benchmark --variant street-grid --solver vlm --limit 5
# Inspect the five-challenge protocol and artifacts before advancing.
python -m ai_solver.cli benchmark --variant street-grid --solver vlm
```

The live VLM selection/submission path and VLM accuracy/latency remain
unverified until these stages succeed. No VLM accuracy or token cost is invented.
Level 2/3 solvers, engineered solvers, training, fine-tuning, label-based offline
evaluation, and per-tile ground-truth metrics are intentionally deferred.
