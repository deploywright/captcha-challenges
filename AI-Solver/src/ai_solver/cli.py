"""CLI for independent benchmarks and explicitly submitted single challenges."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .client import BenchmarkClient
from .config import load_config
from .errors import SolverError
from .runner import BenchmarkRunner
from .solvers.level_1_vlm import Level1VLMSolver, OpenAIVisionProvider
from .solvers.random_baseline import RandomBaseline


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public-only zero-shot CAPTCHA benchmark")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("benchmark", "solve"):
        cmd = commands.add_parser(name)
        if name == "solve":
            cmd.add_argument("challenge_id")
            cmd.add_argument(
                "--submit", action="store_true", help="Explicitly submit one prediction"
            )
        cmd.add_argument("--config", type=Path)
        cmd.add_argument("--env-file", type=Path, default=Path(".env"))
        cmd.add_argument("--base-url")
        cmd.add_argument("--variant", choices=["street-grid"])
        cmd.add_argument("--solver", choices=["vlm", "random"])
        cmd.add_argument("--model")
        cmd.add_argument("--output-dir", type=Path)
        cmd.add_argument("--seed", type=int)
        cmd.add_argument("--timeout", type=float)
        cmd.add_argument("--max-retries", type=int)
        cmd.add_argument("--selection-probability", type=float)
        cmd.add_argument("--limit", type=int)
        cmd.add_argument("--dry-run", action="store_true", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    values = vars(args).copy()
    for key in ("command", "config", "env_file", "challenge_id", "submit"):
        values.pop(key, None)
    provider = None
    try:
        load_dotenv(args.env_file, override=False)
        config = load_config(values, args.config)
        if config.solver == "random":
            solver = RandomBaseline(seed=config.seed, probability=config.selection_probability)
        else:
            provider = OpenAIVisionProvider(
                config.model,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
            solver = Level1VLMSolver(provider)
        with BenchmarkClient(
            config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        ) as client:
            runner = BenchmarkRunner(
                client, solver, config, progress=lambda message: print(message, file=sys.stderr)
            )
            if args.command == "benchmark":
                output, summary = runner.run()
                print(json.dumps({"output_dir": str(output), "summary": summary}, indent=2))
                return 1 if summary["error_count"] else 0
            row = runner.evaluate(args.challenge_id, submit=args.submit and not config.dry_run)
            print(row.model_dump_json(indent=2))
            return 1 if row.error else 0
    except (SolverError, ValueError, OSError) as exc:
        print(
            str(exc)
            if isinstance(exc, (SolverError, ValueError))
            else "Unable to write or read local run files",
            file=sys.stderr,
        )
        return 1
    finally:
        if provider is not None:
            provider.close()


if __name__ == "__main__":
    raise SystemExit(main())
