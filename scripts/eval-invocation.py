#!/usr/bin/env python3
"""Run the invocation fixtures against a real Claude Code host and grade discovery.

Each fixture prompt goes to a headless `claude -p` session in an empty git
repository. The run stops at the first Skill tool call or after a few turns, so
a case costs one or two model calls rather than a full design run.

The default host loads only this repository as a plugin, with no user or local
settings, so another installed skill or a session hook cannot decide the
result. `--host user` runs on your own configuration instead, which is what
users with other skills installed actually get.

Only invocation is graded. `expectedMode` is printed but not checked: telling a
direct answer from a full run needs the whole run to finish.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs" / "evaluations" / "invocation-cases.json"
SKILL_NAME = "system-design"


@dataclass
class Observation:
    invoked: bool
    first_action: str
    cost_usd: float
    error: str = ""


def first_action(event: dict) -> str | None:
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
            # A plugin namespaces the name (`system-design-skill:system-design`);
            # a user-level install does not.
            if str(block.get("input", {}).get("skill", "")).split(":")[-1] == SKILL_NAME:
                return True
    return False


def run_case(prompt: str, args: argparse.Namespace) -> Observation:
    command = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--no-session-persistence",
        "--permission-mode", "default",
        "--max-turns", str(args.max_turns),
    ]
    if args.host == "plugin":
        command += ["--setting-sources", "project", "--plugin-dir", str(ROOT)]
    if args.model:
        command += ["--model", args.model]

    workdir = Path(tempfile.mkdtemp(prefix="system-design-eval-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        process = subprocess.Popen(
            command, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        # A run that stalls must not block the batch, and must not pass a
        # negative case by never reaching a decision.
        timed_out = threading.Event()

        def expire() -> None:
            timed_out.set()
            process.kill()

        timer = threading.Timer(args.timeout, expire)
        timer.start()
        invoked, action, cost = False, "", 0.0
        assert process.stdout is not None
        for line in process.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "assistant":
                action = action or (first_action(event) or "")
                if is_this_skill(event):
                    invoked = True
                    break
            elif event.get("type") == "result":
                cost = float(event.get("total_cost_usd") or 0.0)
        if process.poll() is None:
            process.kill()
        _, stderr = process.communicate()
        timer.cancel()
        if timed_out.is_set() and not invoked:
            return Observation(False, action, cost, f"timed out after {args.timeout:.0f}s")
        if not action and process.returncode not in (0, -9):
            return Observation(False, "", cost, stderr.strip().splitlines()[-1] if stderr.strip() else "no output")
        return Observation(invoked, action, cost)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", choices=("plugin", "user"), default="plugin",
                        help="plugin: this repo only, no user settings (default); user: your own setup")
    parser.add_argument("--runs", type=int, default=1, help="runs per case; invocation is sampled, not fixed")
    parser.add_argument("--label", action="append", help="run only these fixture labels (repeatable)")
    parser.add_argument("--model", help="model alias passed to claude --model")
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=240.0, help="seconds per run")
    parser.add_argument("--jobs", type=int, default=4, help="concurrent runs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not shutil.which("claude"):
        print("eval-invocation: the claude CLI is not on PATH", file=sys.stderr)
        raise SystemExit(2)
    cases = json.loads(FIXTURES.read_text())
    if args.label:
        cases = [case for case in cases if case["label"] in args.label]
        missing = set(args.label) - {case["label"] for case in cases}
        if missing:
            print(f"eval-invocation: unknown labels {sorted(missing)}", file=sys.stderr)
            raise SystemExit(2)

    jobs = [(case, run) for case in cases for run in range(args.runs)]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        observations = list(pool.map(lambda job: run_case(job[0]["prompt"], args), jobs))

    failures, errors, total_cost = 0, 0, 0.0
    print(f"host={args.host} runs={args.runs} model={args.model or 'default'}\n")
    print(f"{'label':<25} {'expect':<7} {'invoked':<8} {'mode (not graded)':<18} first action")
    for index, case in enumerate(cases):
        runs = observations[index * args.runs:(index + 1) * args.runs]
        total_cost += sum(run.cost_usd for run in runs)
        broken = [run for run in runs if run.error]
        errors += len(broken)
        hits = sum(run.invoked for run in runs)
        graded = len(runs) - len(broken)
        expected = case["expectedInvocation"]
        # Pass on a strict majority of graded runs in the expected direction.
        agreeing = hits if expected else graded - hits
        passed = graded > 0 and agreeing * 2 > graded
        failures += not passed
        actions = ", ".join(sorted({run.error or run.first_action for run in runs}))
        mark = "ok  " if passed else "FAIL"
        print(f"{mark} {case['label']:<20} {str(expected).lower():<7} {hits}/{len(runs):<6} "
              f"{case['expectedMode']:<18} {actions}")

    print(f"\n{len(cases) - failures}/{len(cases)} cases pass; {errors} run errors; "
          f"cost ${total_cost:.2f} (runs stopped at the Skill call report $0)")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
