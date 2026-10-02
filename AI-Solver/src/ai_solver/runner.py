"""One independent prediction per challenge, append-only results and safe metrics."""

import json
import subprocess
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .client import BenchmarkClient
from .config import RunConfig
from .contracts import CatalogEntry, ChallengeResult, PublicChallenge, validate_indices
from .errors import ModelError, ModelResponseError, PublicDataLeakError, SolverError
from .metrics import aggregate_metrics
from .solvers.base import Solver


def infer_illusion_subtype(instruction: str) -> str:
    lower = instruction.lower()
    if "mortar" in lower or "parallel" in lower or "row" in lower:
        return "cafe-wall"
    if "orange" in lower or "center circle" in lower or "size" in lower:
        return "ebbinghaus"
    if "shade of grey" in lower:
        return "simultaneous-contrast"
    if "shade" in lower or "square" in lower:
        return "checker-shadow"
    if "bar" in lower:
        return "ponzo"
    if "horizontal line" in lower:
        return "muller-lyer"
    return "checker-shadow"


def select_entries(
    catalog: list[CatalogEntry],
    variant: str,
    limit: int | None = None,
) -> list[CatalogEntry]:
    if variant == "all":
        entries = catalog
    elif variant in ("routing-puzzle", "tangled-cables"):
        entries = [
            entry for entry in catalog if entry.variant in ("routing-puzzle", "tangled-cables")
        ]
    else:
        entries = [entry for entry in catalog if entry.variant == variant]
    return entries if limit is None else entries[:limit]


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class BenchmarkRunner:
    def __init__(
        self,
        client: BenchmarkClient,
        solver: Solver,
        config: RunConfig,
        *,
        progress: Callable[[str], None] | None = None,
    ):
        self.client = client
        self.solver = solver
        self.config = config
        self.progress = progress or (lambda _: None)

    def evaluate(
        self,
        entry: CatalogEntry | str,
        *,
        submit: bool,
    ) -> ChallengeResult:
        start = time.perf_counter()
        row = ChallengeResult(
            challenge_id=entry.id if isinstance(entry, CatalogEntry) else entry,
            variant=entry.variant if isinstance(entry, CatalogEntry) else self.config.variant,
            level=entry.level if isinstance(entry, CatalogEntry) else 1,
            solver=self.solver.name,
            model=self.solver.model_name,
        )
        phase = "challenge"
        phase_start = start
        try:
            challenge: PublicChallenge = self.client.get_challenge(entry)
            row.variant, row.level = challenge.variant, challenge.level
            if isinstance(entry, CatalogEntry):
                row.subtype = entry.subtype
                row.difficulty = entry.difficulty
                row.resolution = entry.resolution
                row.series_id = entry.seriesId
            if challenge.level == 2 and challenge.variant == "checker-shadow" and not row.subtype:
                row.subtype = infer_illusion_subtype(challenge.instruction)
            phase = "assets"
            phase_start = time.perf_counter()
            assets = self.client.download_assets(challenge)
            row.asset_download_time_ms = (time.perf_counter() - phase_start) * 1000
            row.asset_count = len(assets)
            phase = "inference"
            phase_start = time.perf_counter()
            prediction = self.solver.solve(challenge, assets)
            if prediction.challenge_id != challenge.id:
                raise ModelResponseError("Solver prediction ID mismatch")
            if challenge.type == "image-selection":
                prediction.answer = validate_indices(prediction.answer, len(assets))
            row.prediction = prediction.answer
            row.confidence = prediction.confidence
            row.inference_time_ms = prediction.inference_time_ms
            row.predicted_positive_count = (
                len(prediction.answer) if isinstance(prediction.answer, list) else None
            )
            row.input_tokens, row.output_tokens = prediction.input_tokens, prediction.output_tokens
            row.api_request_count = prediction.api_request_count
            row.usage_complete = prediction.usage_complete
            row.parsing_status = prediction.parsing_status
            if submit:
                phase = "submission"
                phase_start = time.perf_counter()
                response, row.submission_status = self.client.submit(challenge, prediction)
                row.submission_time_ms = (time.perf_counter() - phase_start) * 1000
                row.correct = response.correct
                row.status = "evaluated"
            else:
                row.status = "dry_run"
        except PublicDataLeakError:
            raise
        except Exception as exc:
            # Persist only typed safe messages; arbitrary exception text could contain secrets.
            elapsed = (time.perf_counter() - phase_start) * 1000
            row.error_type = (
                type(exc).__name__ if isinstance(exc, SolverError) else "UnexpectedError"
            )
            row.error = str(exc) if isinstance(exc, SolverError) else "Unexpected challenge failure"
            row.status = "solver_error" if phase == "inference" else "error"
            if phase == "assets":
                row.asset_download_time_ms = elapsed
            elif phase == "inference":
                row.inference_time_ms = getattr(exc, "inference_time_ms", None) or elapsed
                row.parsing_status = (
                    "invalid"
                    if isinstance(exc, ModelResponseError)
                    else "not_received"
                    if isinstance(exc, ModelError)
                    else "error"
                )
                row.api_request_count = getattr(exc, "api_request_count", 0)
                row.input_tokens = getattr(exc, "input_tokens", None)
                row.output_tokens = getattr(exc, "output_tokens", None)
                row.usage_complete = False
                row.model_status = getattr(exc, "status_code", None)
                row.provider_error_code = getattr(exc, "provider_error_code", None)
            elif phase == "submission":
                row.submission_time_ms = elapsed
                row.submission_status = getattr(exc, "status_code", None)
        row.total_time_ms = (time.perf_counter() - start) * 1000
        return row

    def run(self) -> tuple[Path, dict]:
        started = datetime.now(UTC)
        variant_tag = self.config.variant.replace("-", "_")
        resumed_dir: Path | None = None
        if self.config.resume and self.config.output_dir.exists():
            candidates = [
                p
                for p in sorted(self.config.output_dir.iterdir(), reverse=True)
                if p.is_dir() and (p / "run.json").exists()
            ]
            for cand in candidates:
                try:
                    meta = json.loads((cand / "run.json").read_text(encoding="utf-8"))
                    if (
                        meta.get("variant") == self.config.variant
                        and meta.get("solver") == self.solver.name
                    ):
                        resumed_dir = cand
                        break
                except Exception:
                    pass

        if resumed_dir is not None:
            output = resumed_dir
            metadata = json.loads((output / "run.json").read_text(encoding="utf-8"))
            run_id = metadata["run_id"]
        else:
            suffix = f"{variant_tag}_{self.config.solver}_{uuid.uuid4().hex[:8]}"
            run_id = f"{started:%Y%m%dT%H%M%S%fZ}_{suffix}"
            output = self.config.output_dir / run_id
            output.mkdir(parents=True, exist_ok=False)
            if self.config.variant in ("checker-shadow", "routing-puzzle"):
                prompt_version = "single-choice-v1"
            elif self.config.variant in ("street-grid", "hard-street-grid", "degraded-vision"):
                prompt_version = "image-selection-v1"
            else:
                prompt_version = "v1-mixed"
            metadata = {
                "run_id": run_id,
                "started_at": started.isoformat(),
                "base_url": self.client.base_url,
                "solver": self.solver.name,
                "model": self.solver.model_name,
                "variant": self.config.variant,
                "challenge_count": 0,
                "discovered_challenge_count": None,
                "git_commit": _git_commit(),
                "config": self.config.model_dump(mode="json"),
                "status": "running",
                "package_version": "0.1.0",
                "prompt_version": prompt_version,
            }
            _write_json(output / "run.json", metadata)

        completed_by_id: dict[str, ChallengeResult] = {}
        pred_path = output / "predictions.jsonl"
        if pred_path.exists():
            for line in pred_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        res = ChallengeResult.model_validate_json(line)
                        if res.status in ("evaluated", "dry_run") and not res.error:
                            completed_by_id[res.challenge_id] = res
                    except Exception:
                        pass
            if resumed_dir is not None:
                clean_content = "".join(
                    r.model_dump_json() + "\n" for r in completed_by_id.values()
                )
                pred_path.write_text(clean_content, encoding="utf-8")

        rows: list[ChallengeResult] = list(completed_by_id.values())
        fatal: SolverError | None = None
        mode = "a" if resumed_dir is not None else "x"
        with pred_path.open(mode, encoding="utf-8") as predictions:
            try:
                catalog = self.client.get_catalog()
                discovered = select_entries(catalog, self.config.variant)
                entries = select_entries(catalog, self.config.variant, self.config.limit)
                metadata["discovered_challenge_count"] = len(discovered)
                metadata["challenge_count"] = len(entries)
                _write_json(output / "run.json", metadata)
                self.progress(
                    f"Discovered {len(discovered)} {self.config.variant} challenges; "
                    f"running {len(entries)}"
                )
                for idx, entry in enumerate(entries):
                    if entry.id in completed_by_id:
                        self.progress(
                            f"{entry.id}: resumed; correct={completed_by_id[entry.id].correct}"
                        )
                        continue
                    row = self.evaluate(entry, submit=not self.config.dry_run)
                    self.progress(f"{entry.id}: {row.status}; correct={row.correct}")
                    if self.config.request_interval_seconds > 0 and idx < len(entries) - 1:
                        time.sleep(self.config.request_interval_seconds)
                    rows.append(row)
                    predictions.write(row.model_dump_json() + "\n")
                    predictions.flush()
            except SolverError as exc:
                fatal = exc
                metadata["error_type"] = type(exc).__name__
                metadata["error"] = str(exc)
            except Exception:
                fatal = SolverError("Unexpected benchmark failure")
                metadata["error_type"] = "UnexpectedError"
                metadata["error"] = str(fatal)
            finally:
                metadata["status"] = (
                    "failed"
                    if fatal
                    else "completed_with_errors"
                    if any(row.error_type for row in rows)
                    else "completed"
                )
                metadata["finished_at"] = datetime.now(UTC).isoformat()
                _write_json(output / "run.json", metadata)
                summary = aggregate_metrics(
                    rows,
                    input_price_per_million=self.config.input_price_per_million,
                    output_price_per_million=self.config.output_price_per_million,
                )
                summary.update(
                    {
                        "run_id": run_id,
                        "status": metadata["status"],
                        "requested_challenge_count": metadata["challenge_count"],
                    }
                )
                _write_json(output / "summary.json", summary)
        if fatal:
            self.progress(f"Run failed; safe partial results: {output}")
            raise fatal
        return output, summary
