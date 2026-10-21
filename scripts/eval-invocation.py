#!/usr/bin/env python3
"""Grade skill discovery against a real Claude Code host, not skill execution.

The plugin host loads this repository in an empty git repository. Each trial
stops at the target Skill request or waits for a successful terminal result.
Invalid trials block the gate; attempts are never retried automatically.
Use --output-dir NEW_DIRECTORY to retain streams and provenance.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs" / "evaluations" / "invocation-cases.json"
SKILL_NAME = "system-design"


@dataclass
class Observation:
    invoked: bool = False
    first_action: str = ""
    cost_usd: Optional[float] = None
    error: str = ""
    stop_reason: str = ""
    result_subtype: Optional[str] = None
    returncode: Optional[int] = None
    resolved_model: Optional[str] = None


def first_action(event: dict) -> Optional[str]:
    for block in event.get("message", {}).get("content", []):
        if block.get("type") == "tool_use":
            target = block.get("input", {}).get("skill")
            return f"{block['name']}({target})" if target else block["name"]
        if block.get("type") == "text" and block.get("text", "").strip():
            return "answered"
    return None


def is_this_skill(event: dict) -> bool:
    for block in event.get("message", {}).get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            # Plugin installs namespace the same skill name.
            if str(block.get("input", {}).get("skill", "")).split(":")[-1] == SKILL_NAME:
                return True
    return False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_case(prompt: str, args: argparse.Namespace, directory: Path) -> dict:
    command = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--no-session-persistence", "--permission-mode", "default",
               "--max-turns", str(args.max_turns)]
    if args.host == "plugin":
        command += ["--setting-sources", "project", "--plugin-dir", str(ROOT)]
    if args.model:
        command += ["--model", args.model]

    directory.mkdir()
    started_at, started = utc_now(), time.monotonic()
    observation = Observation()
    process = None
    timer = None
    timed_out = threading.Event()
    terminal = None
    protocol_error = ""
    with tempfile.TemporaryDirectory(prefix="system-design-eval-") as workdir:
        with (directory / "stdout.jsonl").open("w", encoding="utf-8") as stdout_log, \
                (directory / "stderr.txt").open("w", encoding="utf-8") as stderr_log:
            try:
                subprocess.run(["git", "init", "-q"], cwd=workdir, check=True,
                               stdout=subprocess.DEVNULL, stderr=stderr_log, timeout=args.timeout)
                # A file drains stderr without competing with the streamed stdout reader.
                process = subprocess.Popen(command, cwd=workdir, stdout=subprocess.PIPE,
                                           stderr=stderr_log, text=True, encoding="utf-8", errors="replace",
                                           start_new_session=os.name == "posix")

                def stop_process() -> None:
                    try:
                        if os.name == "posix":
                            os.killpg(process.pid, signal.SIGKILL)
                        elif process.poll() is None:
                            process.kill()
                    except ProcessLookupError:
                        pass

                def expire() -> None:
                    # Descendants can still hold stdout open after the parent exits.
                    timed_out.set()
                    stop_process()

                timer = threading.Timer(args.timeout, expire)
                timer.start()
                assert process.stdout is not None
                for line in process.stdout:
                    stdout_log.write(line)
                    stdout_log.flush()
                    try:
                        event = json.loads(line)
                        if not isinstance(event, dict):
                            raise ValueError("event must be an object")
                        if event.get("type") == "assistant":
                            observation.first_action = observation.first_action or (first_action(event) or "")
                            if is_this_skill(event):
                                observation.invoked = True
                                break
                        elif event.get("type") == "system" and event.get("subtype") == "init":
                            if isinstance(event.get("model"), str):
                                observation.resolved_model = event["model"]
                        elif event.get("type") == "result":
                            if terminal is not None:
                                protocol_error = "multiple terminal results"
                            terminal = event
                    except (ValueError, TypeError, AttributeError, KeyError) as exc:
                        protocol_error = f"invalid stream event: {exc}"
                if observation.invoked:
                    timer.cancel()
                    stop_process()
                process.wait()
            except (OSError, subprocess.SubprocessError) as exc:
                observation.error = f"host execution failed: {exc}"
                observation.stop_reason = "host_error"
            finally:
                if timer is not None:
                    timer.cancel()
                    timer.join()
                if process is not None:
                    stop_process()
                    process.wait()
                    observation.returncode = process.returncode
                    if process.stdout is not None:
                        # Preserve any bytes already emitted after the decisive Skill request.
                        stdout_log.write(process.stdout.read())
                        process.stdout.close()

    if terminal is not None:
        observation.result_subtype = terminal.get("subtype")
        cost = terminal.get("total_cost_usd")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            try:
                if math.isfinite(cost) and cost >= 0:
                    observation.cost_usd = float(cost)
            except OverflowError:
                pass
    if not observation.error:
        if protocol_error:
            observation.error, observation.stop_reason = protocol_error, "protocol_error"
        elif timed_out.is_set():
            observation.error = f"timed out after {args.timeout:g}s"
            observation.stop_reason = "timeout"
        elif observation.invoked:
            observation.stop_reason = "invocation_observed"
        elif terminal is None:
            observation.error, observation.stop_reason = "missing terminal result", "missing_result"
        elif terminal.get("subtype") != "success" or terminal.get("is_error") is not False:
            observation.error = f"unsuccessful terminal result: {terminal.get('subtype')}"
            observation.stop_reason = "terminal_error"
        elif observation.returncode != 0:
            observation.error = f"host exited with status {observation.returncode}"
            observation.stop_reason = "host_error"
        else:
            observation.stop_reason = "completed"
    record = {**asdict(observation), "started_at": started_at, "finished_at": utc_now(),
              "duration_seconds": time.monotonic() - started, "command": command,
              "stdout_path": str(Path(directory.name) / "stdout.jsonl"),
              "stderr_path": str(Path(directory.name) / "stderr.txt")}
    (directory / "trial.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer")
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", choices=("plugin", "user"), default="plugin")
    parser.add_argument("--runs", type=positive_int, default=1, help="trials per case")
    parser.add_argument("--label", action="append", help="fixture label; repeatable")
    parser.add_argument("--model", help="model alias passed to claude")
    parser.add_argument("--max-turns", type=positive_int, default=3)
    parser.add_argument("--timeout", type=positive_float, default=240.0)
    parser.add_argument("--jobs", type=positive_int, default=4)
    parser.add_argument("--output-dir", type=Path, help="new directory for streams and summary; never overwritten")
    return parser.parse_args()


def command_output(command: list[str]) -> Optional[str]:
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def metadata(args: argparse.Namespace) -> dict:
    return {"host": args.host, "requested_model": args.model, "runs": args.runs,
            "max_turns": args.max_turns, "timeout_seconds": args.timeout, "jobs": args.jobs,
            "cli_version": command_output(["claude", "--version"]),
            "revision": command_output(["git", "rev-parse", "HEAD"]),
            "working_tree_status": command_output(["git", "status", "--porcelain"]),
            "fixture_sha256": hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),
            "skill_sha256": hashlib.sha256((ROOT / "skills/system-design/SKILL.md").read_bytes()).hexdigest(),
            "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def evaluate(args: argparse.Namespace, cases: list[dict], output: Path) -> int:
    provenance = metadata(args)
    (output / "metadata.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    jobs = [(case, run) for case in cases for run in range(args.runs)]

    def execute(job: tuple[int, tuple[dict, int]]) -> dict:
        index, (case, run) = job
        record = run_case(case["prompt"], args, output / f"trial-{index + 1:04d}")
        record.update(label=case["label"], run=run + 1, expected_invocation=case["expectedInvocation"])
        return record

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        observations = list(pool.map(execute, enumerate(jobs)))
    failures = 0
    errors = sum(bool(run["error"]) for run in observations)
    total_cost = sum(run["cost_usd"] for run in observations if run["cost_usd"] is not None)
    unknown_cost = sum(run["cost_usd"] is None for run in observations)
    print(f"host={args.host} runs={args.runs} model={args.model or 'default'}\n")
    print(f"{'label':<25} {'expect':<7} {'invoked':<8} {'mode (not graded)':<18} first action")
    for index, case in enumerate(cases):
        runs = observations[index * args.runs:(index + 1) * args.runs]
        valid = [run for run in runs if not run["error"]]
        hits = sum(run["invoked"] for run in valid)
        expected = case["expectedInvocation"]
        agreeing = sum(run["invoked"] == expected for run in valid)
        passed = len(valid) == len(runs) and agreeing * 2 > len(runs)
        failures += not passed
        actions = ", ".join(sorted({run["error"] or run["first_action"] for run in runs}))
        mark = "ok  " if passed else "FAIL"
        print(f"{mark} {case['label']:<20} {str(expected).lower():<7} {hits}/{len(runs):<6} "
              f"{case['expectedMode']:<18} {actions}")
    summary = {"metadata": provenance, "trials": observations, "cases": len(cases),
               "failed_cases": failures, "invalid_trials": errors,
               "known_cost_usd": total_cost, "unknown_cost_trials": unknown_cost}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(cases) - failures}/{len(cases)} cases pass; {errors} run errors; "
          f"known estimated cost ${total_cost:.2f}; {unknown_cost} trials with unknown cost")
    if args.output_dir:
        print(f"Evidence: {output}")
    return 1 if failures or errors else 0


def main() -> None:
    args = parse_args()
    if not shutil.which("claude"):
        print("eval-invocation: the claude CLI is not on PATH", file=sys.stderr)
        raise SystemExit(2)
    cases = json.loads(FIXTURES.read_text())
    if args.label:
        missing = set(args.label) - {case["label"] for case in cases}
        if missing:
            print(f"eval-invocation: unknown labels {sorted(missing)}", file=sys.stderr)
            raise SystemExit(2)
        cases = [case for case in cases if case["label"] in args.label]
    try:
        if args.output_dir:
            output = args.output_dir.resolve()
            output.mkdir(parents=True, exist_ok=False)
            status = evaluate(args, cases, output)
        else:
            with tempfile.TemporaryDirectory(prefix="system-design-eval-results-") as directory:
                status = evaluate(args, cases, Path(directory))
    except OSError as exc:
        print(f"eval-invocation: {exc}", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(status)


if __name__ == "__main__":
    main()
