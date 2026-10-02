# AI-Solver v0.1

An independent **zero-shot VLM baseline** for the public Level 1 `street-grid`
CAPTCHA benchmark. Python 3.11+. No training or fine-tuning takes place. The model
receives only the public instruction and public image tiles.

This package does not use BDD100K labels or annotations, private answers,
generation metadata, or Challenge Engine imports. Accuracy claims require actual
evaluated results; a successful dry run does not measure accuracy.

```text
Cloudflare Benchmark
        |
        v
Public Client: catalog -> challenge -> image tiles
        |
        v
VLM Solver: one request containing every numbered tile
        |
        v
Submission API: one evaluated prediction per challenge
        |
        v
Metrics: exact challenge accuracy and separate latency measurements
```

## Install and configure

From the repository root:

```bash
cd AI-Solver
python -m pip install -e '.[openai,test]'
```

Copy `.env.example` to `.env`, set `CAPTCHA_BASE_URL` to the production origin,
and set `OPENAI_API_KEY` locally. `.env` and run outputs are ignored by Git.
Secrets are never accepted in YAML or stored in run metadata.

```env
CAPTCHA_BASE_URL=https://your-worker.workers.dev
OPENAI_API_KEY=your-local-secret
OPENAI_MODEL=gpt-4.1-mini-2025-04-14
```

The base URL is configurable; no Cloudflare hostname is embedded in the package.
Use an HTTP(S) origin, without credentials, query, fragment, or a path prefix.
Trailing slashes are normalized. Existing environment variables override `.env`;
CLI options override environment variables, which override YAML configuration.
Use `--env-file PATH` for an explicit local environment file or `--config
config.example.yaml` for YAML options. Relative output paths resolve from the
working directory. Run commands from `AI-Solver` to use its ignored `results/`.

Only the VLM provider needs the `openai` extra. For random/public-only checks:

```bash
python -m pip install -e '.[test]'
```

## Commands and staged first benchmark

`benchmark` submits by default. `--dry-run` still performs inference, which can
incur model API usage; it suppresses submission. Start with one VLM challenge,
inspect its artifacts, then five, then the full dynamically discovered set.
Do not advance when the preceding stage has errors, missing assets, invalid
indices, or a failed submission. An incorrect but valid evaluation is a measured
outcome and must not trigger another answer attempt.

```bash
# Optional one-challenge VLM dry run (model usage, no submission)
python -m ai_solver.cli benchmark --variant street-grid --solver vlm --limit 1 --dry-run

# First real VLM evaluation
python -m ai_solver.cli benchmark --variant street-grid --solver vlm --limit 1

# After confirming the first run's protocol succeeded
python -m ai_solver.cli benchmark --variant street-grid --solver vlm --limit 5

# After confirming the five-challenge run's protocol succeeded
python -m ai_solver.cli benchmark --variant street-grid --solver vlm

# Reproducible independent random baseline; default per-tile probability is 0.33
python -m ai_solver.cli benchmark --variant street-grid --solver random --seed 42

# Free public asset/inference preflight, with no submissions or provider key
python -m ai_solver.cli benchmark --solver random --seed 42 --dry-run

# Single challenge prints its prediction/result, without submission
python -m ai_solver.cli solve CHALLENGE_ID --solver vlm

# Explicit submission of the single prediction
python -m ai_solver.cli solve CHALLENGE_ID --solver vlm --submit
```

Other options: `--base-url`, `--limit`, `--model`, `--output-dir`, `--seed`,
`--timeout` (seconds per HTTP attempt), `--max-retries`, and
`--selection-probability`. `--dry-run` also overrides `solve --submit`.
`ai-solver` is an installed console-script equivalent to `python -m ai_solver.cli`.
Errors cause a nonzero exit status, while ordinary incorrect answers do not.

For the first real run, inspect `predictions.jsonl`: the current public grid
should have `asset_count: 9`, `api_request_count: 1` on a clean request,
`parsing_status: "valid"`, unique zero-based `prediction` indices,
`submission_status: 200`, and a Boolean `correct`. Transport retries and the
single allowed output-format recovery can increase the provider request count;
these are recorded rather than hidden.

## Contracts, isolation, and retry policy

The HTTP allowlist permits only same-origin public resources:

- `GET /challenges/catalog.json`
- `GET /challenges/<id>/challenge.json` via the catalog's `challengeUrl`
- `GET /challenges/<id>/assets/<image>` for the requested challenge
- `POST /api/challenges/<id>/submit`

The client rejects external origins, local-file URLs, path traversal, encoded
paths, query parameters, and redirects. Public resources are cached in memory
for the client lifetime. It never reads local generated benchmark data.
Every fetched JSON document is checked recursively before parsing, caching, or
status handling. Answer, routing, source-image, bounding-box, and similar
private fields stop the **entire run** with `PUBLIC DATA LEAK DETECTED`, including
when returned on error responses or disguised as assets. Payloads are not logged.
Submission responses contribute only their correctness flag and public protocol
fields; no correct tile selections are recorded or inferred.

The catalog's `variant == "street-grid"` determines membership; no challenge
count, target object, grid size, or answer count is hardcoded. The public
instruction supplies the target semantics. All images are numbered from zero
and sent together, with each tile labelled before its image. The model must
classify each tile independently and return a strict JSON selection schema.

Selections must be lists of actual integers (booleans, floats, and strings are
rejected), in the asset range, without duplicates. Valid selections are sorted.
One fresh structured-output recovery request is permitted for invalid output;
its prompt is fixed and receives no submission feedback. A second invalid output
is a `ModelResponseError` / `solver_error` and produces no evaluated prediction.
The OpenAI provider requires `confidence: null`, since it has no calibrated
selection confidence. Other providers may supply meaningful confidence later.

Only transport failures and HTTP 429, 502, 503, and 504 are retried, with bounded
exponential backoff. HTTP 400/401/403/404/500, invalid public contracts, and wrong
answers are not retried. The OpenAI SDK's automatic retries are disabled in favor
of this same explicit policy. Documented credit/quota/spend-limit error codes
are also not retried, even when HTTP 429; these require provider-account changes.
Known non-secret provider error codes are recorded without provider error bodies.
A transport retry resends the same submission
payload; ambiguous network failures can produce repeated delivery of that same
prediction. There is never a replacement answer or learning from correctness.
The solver has no API for receiving benchmark feedback.

Errors are typed as `NetworkError`, `ChallengeContractError`,
`AssetDownloadError`, `ModelError`, `ModelResponseError`, and `SubmissionError`.
Ordinary challenge errors are persisted and the next challenge continues.
Public-data leaks are fatal. Unexpected exception messages are redacted.

## Results and metrics

Each benchmark creates a unique directory under `results/<run-id>/`:

- `run.json`: UTC start/end, base URL, solver/model, discovered and requested
  counts, Git SHA when available, package/prompt version, and non-secret config.
- `predictions.jsonl`: one row per attempted challenge; predictions, correctness,
  status/error, asset count, parsing status, usage, and separate timings.
- `summary.json`: aggregate counts, accuracy, latency, usage, and run status.

The primary metric is **Exact Challenge Accuracy**: correct submissions divided
by valid evaluated submissions. A challenge is correct only when the server
accepts the complete selected set. Errors and dry runs have `correct: null` and
do not enter that denominator; `evaluation_coverage` and error counts expose
missing evaluations. A dry run has `exact_challenge_accuracy: null`.
No tile-level precision, recall, F1, false positives, or false negatives are
computed, because the public endpoint does not expose the needed labels.

`asset_download_time_ms`, `inference_time_ms`, `submission_time_ms`, and
`total_time_ms` are recorded separately. Inference includes provider network
time, retries, and any output recovery; it excludes benchmark asset downloads
and submission. Total includes challenge retrieval and all subsequent phases.
Successful predictions provide mean/median/p95 inference time; p95 uses nearest
rank. Failed inference durations are included in a separate attempt-time mean.
Mean and median total time include every attempted challenge.

Input/output tokens are recorded only when the provider supplies usage.
`estimated_api_request_count` counts provider attempts, including retries and
format recovery. No separate image-token amount or price is invented.
Cost remains `null` unless both token prices are explicitly supplied in YAML
and complete usage is available for every provider request. Such an estimate applies the rates
to reported totals; it does not account for unavailable cache/image billing
breakdowns. Missing usage on recovery or transport attempts disables cost estimation.

The random baseline selects each tile independently with fixed probability
`0.33` by default, without knowing the answer count. Its seed combines the user
seed and challenge ID using SHA-256, so order, limits, and preceding failures do
not change a challenge's random selection. It does not read the public challenge
seed to reconstruct generation and is never tuned using correctness feedback.

## Verification

Unit tests use mocked HTTP/provider responses. An autouse guard prevents actual
network access in unit tests. No normal test requires a key or paid API call.

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

An integration test requires explicit opt-in **and** `CAPTCHA_BASE_URL`. It
discovers all `street-grid` challenges and downloads every public image. It
never invokes a model or submits to production.

```powershell
$env:CAPTCHA_BASE_URL = 'https://your-worker.workers.dev'
$env:RUN_AI_SOLVER_INTEGRATION = '1'
python -m pytest tests/test_integration.py -q -s
```

## Provider and future scope

The OpenAI adapter uses the supported
[Responses API with structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
and [multiple image inputs](https://developers.openai.com/api/docs/guides/images-vision).
The default model is the pinned
[GPT-4.1 mini snapshot](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
`gpt-4.1-mini-2025-04-14`. Account access, quotas, refusals, and provider latency
remain external limitations. No live model result is implied by mocked tests.

`Solver` is a protocol over `PublicChallenge`, image bytes, and
`SolverPrediction`. `VisionProvider` receives only instruction text and images.
Later provider adapters or Level 2/3 solvers can implement these protocols
without replacing the generic client, runner, or metrics. v0.1 deliberately
implements only Level 1 VLM and random baselines. Training, fine-tuning, offline
label-based evaluation, engineered routing solvers, and other levels are deferred.
