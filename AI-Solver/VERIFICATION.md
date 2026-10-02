# AI-Solver v0.1 verification report

Verified on 2026-10-02. The independent package and live acceptance sequence
are complete: **Gemini 3.5 Flash-Lite evaluated all 20 dynamically discovered
street-grid challenges: 14 correct, 6 incorrect, zero execution errors**.
Exact challenge accuracy is **70%**, with 100% evaluation coverage.

Work began from main commit `6b4cf5ed086f82d4c7dafa025956ce1145a703d1`, matching
origin/main then. Later Gemini runs record current checkout commit
`dc575e5e1513f07d1a4d1dafc294eadb43164052`. This implementation leaves
`challenges/`, `web/`, and the root README unchanged.

## Files created and extended

All deliverable files are inside `AI-Solver/`:

- Packaging/configuration: `pyproject.toml`, `.gitignore`, `.env.example`,
  `config.example.yaml`, `README.md`, `VERIFICATION.md`, `results/.gitkeep`.
- Package: `src/ai_solver/__init__.py`, `cli.py`, `config.py`, `contracts.py`,
  `client.py`, `runner.py`, `metrics.py`, `errors.py`, and `security.py`.
- Solvers: `src/ai_solver/solvers/__init__.py`, `base.py`,
  `random_baseline.py`, `level_1_vlm.py`, and `gemini.py`.
- Tests: `tests/conftest.py`, `test_contracts.py`, `test_client.py`,
  `test_runner.py`, `test_metrics.py`, `test_no_private_access.py`,
  `test_solvers.py`, `test_cli.py`, `test_integration.py`, and `test_gemini.py`.

The ignored local `.env` contains the configured production origin and locally
supplied credentials. Credentials and benchmark outputs are excluded from Git.
Each run persists `run.json`, `predictions.jsonl`, and `summary.json` separately.

## Provider, model, and commands

The working default is `gemini-3.5-flash-lite`, using Google GenAI
`models.generate_content`, inline images, and strict JSON Schema structured
output. A request contains only the public instruction and all numbered tiles.
Tools, search, file uploads, and function calling are disabled. Confidence is
`null`; no calibrated confidence is supplied. `Solver` and `VisionProvider`
remain provider-independent protocols. The optional OpenAI Responses adapter
is retained.

Install from the repository root, then configure the ignored local environment:

```bash
cd AI-Solver
python -m pip install -e '.[gemini,test]'
# Set CAPTCHA_BASE_URL and GEMINI_API_KEY locally, following .env.example.
```

The actual successful stages used these commands in order. Artifacts were
checked before advancing:

```bash
python -m ai_solver.cli benchmark --provider gemini --model gemini-3.5-flash-lite --limit 1
python -m ai_solver.cli benchmark --provider gemini --model gemini-3.5-flash-lite --limit 5
python -m ai_solver.cli benchmark --provider gemini --model gemini-3.5-flash-lite
```

Other supported paths:

```bash
python -m ai_solver.cli benchmark --solver random --seed 42 --dry-run
python -m ai_solver.cli benchmark --solver random --seed 42
python -m ai_solver.cli solve CHALLENGE_ID
python -m ai_solver.cli solve CHALLENGE_ID --submit
```

The full random submission command is documented usage; verification executed
only a controlled one-challenge random submission.

## Tests and packaging

Final checks from `AI-Solver/`:

```text
python -m pytest -q
133 passed, 1 skipped in 4.90s

python -m ruff check .
All checks passed!

python -m ruff format --check .
24 files already formatted
```

The skipped test is intentionally opt-in integration. Unit tests block external
HTTP, use mocked providers, and verify both real SDK wire contracts. They cover
public contracts, dynamic filtering, HTTP allowlisting/cache/retries, strict
zero-based indices, one format recovery, wrong-answer non-retry, one evaluated
answer, JSONL, metrics, deterministic random selection, and private-access guards.

The production integration test ran explicitly with `CAPTCHA_BASE_URL` and
`RUN_AI_SOLVER_INTEGRATION=1`:

```text
python -m pytest tests/test_integration.py -q -s
Public integration: 20 street-grid challenges; 180 assets
1 passed in 68.06s
```

It performed public reads only, with no model calls or submissions. The catalog
had 134 total entries and 20 street-grid challenges. Neither the population count
nor target object is hardcoded.

Editable installation with Gemini/test extras succeeded. `pip wheel --no-deps`
also succeeded; wheel contents are exclusively the independent `ai_solver`
package and distribution metadata, including the Gemini adapter/current default.
Wheel SHA-256:
`1f1d1b01a55432c266387f827593d4b4b9c8409915edd5016ac21c0a32804f38`.

## Production random dry run

The deterministic random dry run completed all 20 challenges and downloaded
180 assets: 20 predictions, zero errors, zero model requests, zero submissions.
Accuracy correctly remained `null`. Artifacts:

```text
results/20261002T075433793858Z_level1_random_047ab8f0/
```

A controlled `--solver random --seed 42 --limit 1` submission loaded nine assets,
returned HTTP 200 with `correct=false`, and was not retried. This is a protocol
smoke test, not a full-population random accuracy estimate. Artifacts:

```text
results/20261002T075805556431Z_level1_random_f0c51357/
```

## Real Gemini acceptance sequence

All successful stages used `gemini-3.5-flash-lite`, fixed prompt version
`level1-v1`, and the same solver behavior. Incorrect answers were recorded
without another answer attempt or any prompt/threshold change.

| Stage | Evaluated | Correct | Incorrect | Errors | Provider attempts |
| --- | ---: | ---: | ---: | ---: | ---: |
| One challenge | 1 | 1 | 0 | 0 | 1 |
| Five challenges | 5 | 3 | 2 | 0 | 5 |
| Full discovered set | 20 | 14 | 6 | 0 | 21 |

The one-challenge run loaded nine assets, returned `[4, 7, 8]`, made one model
request, and received HTTP 200 with `correct=true`. Inference was 2,850.089 ms;
total time was 5,607.990 ms. Artifacts:

```text
results/20261002T084852800173Z_level1_vlm_2262282a/
```

The five-challenge run loaded 45 assets, made five model requests, submitted
five valid selections with HTTP 200, and measured 60% exact accuracy. Artifacts:

```text
results/20261002T084951366521Z_level1_vlm_5b42a0de/
```

The full run loaded 180 assets and submitted 20 selections with HTTP 200.
The final artifact audit checked unique challenge IDs, nine assets each, unique
sorted integer indices in range 0 through 8, valid parsing, Boolean correctness,
zero errors, matching aggregates, fixed model/prompt metadata, and one persisted
evaluated selection per challenge. Artifacts:

```text
results/20261002T085501003519Z_level1_vlm_30e5750e/
  run.json
  predictions.jsonl
  summary.json
```

| Full-run metric | Value |
| --- | ---: |
| Exact challenge accuracy | 14 / 20 = 70% |
| Evaluation coverage | 100% |
| Mean inference time | 6,110.233 ms |
| Median inference time | 2,513.648 ms |
| p95 inference time, nearest rank | 9,542.949 ms |
| Mean total time | 10,320.304 ms |
| Median total time | 5,600.687 ms |
| Reported input tokens | 199,685 |
| Reported output tokens | 590 |
| Provider attempts | 21 |
| Estimated cost | null |

One challenge needed an additional provider attempt and spent 65,332.401 ms in
inference. That duration is included in the mean; no replacement answer was
evaluated. Usage for the extra attempt was unavailable, so `usage_complete` is
false and token totals cover reported usage only. Pricing was not supplied;
no cost or image billing amount is invented. Inference includes provider network
time and permitted retries, excluding benchmark downloads/submission. The stages
overlap and remain separate experiments; results are not pooled into full-run
accuracy.

## Provider limitations and earlier attempts

Before the user's switch to Gemini, OpenAI returned HTTP 429 with
`credit_balance_exhausted`, including after the key change. No prediction or
submission resulted. Its retained adapter records safe error codes and does
not retry documented credit, quota, or spend-limit errors.

Gemini 2.5 Flash initially returned HTTP 404 `NOT_FOUND`. Gemini 3.8 Flash
completed one challenge but repeatedly returned HTTP 503 `UNAVAILABLE` in the
five-challenge stage. Both its initial and retry-enabled five-challenge runs had
four provider errors, so no full run was started on that model. Separate artifacts:

```text
results/20261002T083827630339Z_level1_vlm_116ee4cd/  # Gemini 2.5 unavailable
results/20261002T084053567419Z_level1_vlm_e0908b55/  # Gemini 3.8 single
results/20261002T084228251300Z_level1_vlm_b1641297/  # Gemini 3.8 five
results/20261002T084452681072Z_level1_vlm_bb709d29/  # Gemini 3.8 five, retries
```

Flash-Lite was selected to resolve provider availability, without using accuracy
feedback to optimize the solver. The entire 1 -> 5 -> full sequence restarted
with unchanged prompt. Model availability, quotas, service failures, and network
latency remain external limitations. This 20-challenge result describes this
population/run; it does not establish broader CAPTCHA performance or a statistical
comparison with a full random baseline.

## Isolation and deferred scope

Only public catalog, challenge, image paths, and the public submission API were
used. No training, fine-tuning, private answers, annotations, generator imports,
or local generated benchmark files were used. JSON leak checks remain fatal.
No correct selections are stored or inferred from server feedback. Level 2/3,
engineered solvers, offline evaluation with labels, and per-tile precision,
recall, and F1 remain intentionally deferred.

Terminal evidence is retained in ignored `.tmp/` logs:
`ai-solver-unit-tests.log`, `ai-solver-integration.log`, `ai-solver-wheel.log`,
and `ai-solver-gemini-lite-stage1`, `ai-solver-gemini-lite-stage5`, and
`ai-solver-gemini-lite-full` JSON/progress log pairs. Earlier provider failures
and random dry-run/submission logs remain separate.
