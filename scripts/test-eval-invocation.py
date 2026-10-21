#!/usr/bin/env python3
"""Exercise evaluator exit status and evidence through a fake Claude executable."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "docs/evaluations/invocation-cases.json").read_text())
NEGATIVE = next(c["label"] for c in CASES if not c["expectedInvocation"])
POSITIVE = next(c["label"] for c in CASES if c["expectedInvocation"])
PRELUDE = '''import json, sys, time
if "--version" in sys.argv:
    print("fake-claude 1.0")
    sys.exit(0)
def emit(event):
    print(json.dumps(event), flush=True)
def answer():
    emit({"type":"assistant","message":{"content":[{"type":"text","text":"An answer"}]}})
def result(**changes):
    value = {"type":"result","subtype":"success","is_error":False,"total_cost_usd":0.125}
    value.update(changes)
    emit(value)
'''


class InvocationCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.binary = self.directory / "claude"

    def run_eval(self, body, *options, label=NEGATIVE):
        self.binary.write_text("#!" + sys.executable + "\n" + PRELUDE + body + "\n")
        self.binary.chmod(0o755)
        env = dict(os.environ, PATH=str(self.directory) + os.pathsep + os.environ["PATH"])
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/eval-invocation.py"), "--label", label,
             "--jobs", "1", "--timeout", "2", *options],
            env=env, capture_output=True, text=True, timeout=15,
        )

    def test_terminal_errors_cannot_pass_negative(self):
        for ending in ["result(subtype='error_max_turns', is_error=True)",
                       "result(is_error=True)", "result(); sys.exit(1)"]:
            with self.subTest(ending=ending):
                run = self.run_eval("answer()\n" + ending)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertIn("run errors", run.stdout)

    def test_missing_or_malformed_result_cannot_pass_negative(self):
        for body in ["pass", "answer()", "print('not JSON')", "emit([])",
                     "answer(); result(subtype='future_unknown')"]:
            with self.subTest(body=body):
                run = self.run_eval(body)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)

    def test_skill_after_terminal_result_cannot_override_failure(self):
        run = self.run_eval("result(subtype='error_max_turns', is_error=True)\nemit({'type':'assistant','message':{'content':[{'type':'tool_use','name':'Skill','input':{'skill':'system-design'}}]}})\ntime.sleep(3)",
                            label=POSITIVE)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)

    def test_invalid_trial_blocks_majority_without_retry(self):
        counter = self.directory / "count"
        body = f"from pathlib import Path\np = Path({str(counter)!r})\n"
        body += "n = int(p.read_text()) if p.exists() else 0\np.write_text(str(n+1))\n"
        body += "if n >= 2: sys.exit(1)\nanswer(); result()"
        run = self.run_eval(body, "--runs", "3")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(counter.read_text(), "3")

    def test_positive_stop_retains_evidence_and_unknown_cost(self):
        output = self.directory / "evidence"
        body = "emit({'type':'assistant','message':{'content':[{'type':'tool_use','name':'Skill','input':{'skill':'system-design-skill:system-design'}}]}})\ntime.sleep(10)"
        run = self.run_eval(body, "--output-dir", str(output), label=POSITIVE)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        summary = json.loads((output / "summary.json").read_text())
        trial = summary["trials"][0]
        self.assertTrue(trial["invoked"])
        self.assertEqual(trial["stop_reason"], "invocation_observed")
        self.assertIsNone(trial["cost_usd"])
        self.assertEqual(summary["unknown_cost_trials"], 1)
        self.assertEqual(summary["metadata"]["cli_version"], "fake-claude 1.0")
        self.assertEqual(len(summary["metadata"]["fixture_sha256"]), 64)
        self.assertEqual(len(summary["metadata"]["skill_sha256"]), 64)
        self.assertTrue(summary["metadata"]["revision"])
        self.assertIn('"name": "Skill"', (output / trial["stdout_path"]).read_text())
        self.assertTrue((output / trial["stderr_path"]).exists())

    def test_stderr_does_not_deadlock_and_success_cost_is_retained(self):
        output = self.directory / "evidence"
        run = self.run_eval("sys.stderr.write('x' * 1000000); sys.stderr.flush(); answer(); result()",
                            "--output-dir", str(output))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        summary = json.loads((output / "summary.json").read_text())
        self.assertEqual(summary["known_cost_usd"], 0.125)
        self.assertEqual(summary["unknown_cost_trials"], 0)
        self.assertEqual((output / summary["trials"][0]["stderr_path"]).stat().st_size, 1000000)

    def test_timeout_is_invalid_and_retained(self):
        output = self.directory / "evidence"
        run = self.run_eval("answer(); time.sleep(10)", "--timeout", "0.1", "--output-dir", str(output))
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        trial = json.loads((output / "summary.json").read_text())["trials"][0]
        self.assertEqual(trial["stop_reason"], "timeout")
        self.assertIsNone(trial["cost_usd"])

    @unittest.skipUnless(os.name == "posix", "process group cleanup is POSIX-specific")
    def test_timeout_closes_descendant_inherited_pipe(self):
        started = time.monotonic()
        run = self.run_eval("import subprocess\nsubprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])\nanswer()",
                            "--timeout", "0.5")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("timed out", run.stdout)
        self.assertLess(time.monotonic() - started, 3)

    def test_cost_missing_is_unknown_even_on_success(self):
        output = self.directory / "evidence"
        run = self.run_eval("answer(); result(total_cost_usd=None)", "--output-dir", str(output))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIsNone(json.loads((output / "summary.json").read_text())["trials"][0]["cost_usd"])

    def test_existing_output_directory_is_not_overwritten(self):
        output = self.directory / "evidence"
        output.mkdir()
        marker = output / "summary.json"
        marker.write_text("previous evidence")
        run = self.run_eval("answer(); result()", "--output-dir", str(output))
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertEqual(marker.read_text(), "previous evidence")

    def test_positive_numeric_options(self):
        for option, value in [("--runs", "0"), ("--jobs", "-1"), ("--max-turns", "0"),
                              ("--timeout", "0"), ("--timeout", "nan"), ("--timeout", "inf")]:
            with self.subTest(option=option, value=value):
                run = self.run_eval("raise RuntimeError('must not launch')", option, value)
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
