# Invocation evaluation

Run `python3 scripts/eval-invocation.py --runs 3 --output-dir /tmp/system-design-invocation-NEW` before changing the skill description. Choose a new output directory for each run; existing directories are rejected to preserve prior evidence. Fixtures in [invocation-cases.json](invocation-cases.json) define expected discovery. Change an incorrect fixture in a separate commit with its reason.

## What passes

A trial observes invocation when Claude requests the target `Skill` tool, then stops the process to avoid a full design run. This proves routing intent, not that the tool completed or produced a correct design. A non-invocation trial requires a terminal `success` result with `is_error: false` and a zero exit status. Assistant text alone, an empty or malformed stream, a missing result, a timeout, and terminal or process errors cannot count as successful non-invocation.

A case passes only when every planned trial is valid and a strict majority agrees with the fixture. Any invalid trial blocks the suite, even when the other trials agree. There are no automatic retries. Preserve a failed run and start a new evaluation explicitly after diagnosing it. `expectedMode` is displayed but not graded: this evaluator does not establish generation quality, candidate selection, audit correctness, or report delivery.

The plugin host uses an empty Git repository, this repository's plugin, and project-only settings. The user host deliberately uses the caller's setup. Record the host when comparing results. Model aliases and provider behavior can change; repeated trials are samples, not a reliability guarantee.

## Evidence and cost

With `--output-dir`, each trial retains `stdout.jsonl`, `stderr.txt`, and `trial.json`. `summary.json` joins trial outcomes to fixture labels and includes run options, timestamps, exit/termination details, known estimated cost, and the unknown-cost count. `metadata.json` records the repository revision and working-tree status, fixture/skill/evaluator SHA-256 hashes, and CLI version. The model reported in an initialization event is retained when present. A dirty revision alone cannot reconstruct source bytes; retain the corresponding checkout/diff separately if needed.

The runner records no environment variables or credentials itself. Streams are raw CLI output and can contain prompts, local paths, host messages, or sensitive material emitted by tools. Keep evidence local, review before sharing, and do not commit it by default. Without `--output-dir`, evidence is temporary and removed when the batch ends. Supplying an output directory is required when results need an audit trail.

A trial stopped at invocation usually has no terminal cost receipt. Its `cost_usd` is `null`, not zero. Missing, non-finite, negative, or non-numeric totals also remain unknown. The printed total is the sum of known client estimates and is incomplete when any trial has unknown cost. Even a recorded zero is not authoritative billing; crash receipts can contain zeroed estimates. See the official [agent-loop termination contract](https://code.claude.com/docs/en/agent-sdk/agent-loop) and [cost accounting limitations](https://code.claude.com/docs/en/agent-sdk/cost-tracking).

## Offline verification

Run `python3 scripts/test-eval-invocation.py`. These tests place a fake `claude` executable on PATH and exercise the real evaluator subprocess boundary. They cover terminal failures, incomplete streams, invalid-trial aggregation, bounded process cleanup, stderr saturation, evidence retention, unknown cost, and CLI argument validation without live model calls or production-only test hooks.
