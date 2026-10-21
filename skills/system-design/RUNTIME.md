# Investigation runtime

The local runtime for [SKILL.md](SKILL.md) preserves investigation state in `design.json`. The coding host reads sources, reasons, and proposes records; the CLI validates and stores them. It calls no model, executes no repository commands, and installs nothing. Python 3.9 or later is sufficient.

## Start and resume

Use the installed skill directory, not an assumed working directory:

```bash
python3 <skill-dir>/scripts/design_session.py status \
  --design docs/design/example/design.json --root .
```

Read the response's `sha256`, then initialize that existing design explicitly:

```bash
python3 <skill-dir>/scripts/design_session.py init \
  --design docs/design/example/design.json --root . \
  --expected-sha256 <sha256-from-status>
```

Legacy designs remain readable without initialization. Initialization preserves existing design fields and adds `investigation`; it does not rewrite the design version or manufacture evidence. Supply the same repository root on subsequent commands, including after moving the checkout. The runtime owns the investigation records; edit ordinary design content with normal file tools, then reread status before any runtime mutation.

At the start of a later session, read status and run `resume` with its SHA. Resume checks the bytes of recorded local sources. It marks changed evidence stale and unavailable sources unknown; affected passed checks become unknown, resolved unknowns reopen, and answered questions become partial. It retains previous answer text and checkpoint history. Restoring old source bytes does not automatically restore old approvals: capture new evidence and reconsider the claim.

## Commands

Every command requires `--design`. `--root` defaults to the current directory and resolves root-relative source paths. Every mutation requires `--expected-sha256`, including init, checkpoint, resume, and recover. Record commands additionally require `--record <file>` or `--record -` for JSON on stdin.

| Command | Effect |
|---|---|
| `status` | Return inspected records with pending freshness invalidations applied in memory; no writes. The SHA identifies canonical bytes. `freshnessChangesPending` means resume must persist invalidation. |
| `init` | Add a new session and empty record collections to an existing design. Refuses to reset an initialized design. |
| `record-evidence` | Capture source byte hashes and append immutable evidence under a new ID. |
| `record-question` | Insert or replace one question by ID. |
| `record-unknown` | Insert or replace one unresolved question or its resolution by ID. |
| `record-check` | Insert or replace one explicit check result by ID. |
| `checkpoint` | Preserve the exact current bytes under their digest without changing the design. |
| `resume` | Persist source freshness observations and invalidate dependent successful records. |
| `validate` | Check investigation structure, references, and local freshness without writing. It does not prove the claims or replace report checks. |
| `recover` | Restore a specifically selected, hash-verified checkpoint, preserving current bytes first. Requires `--checkpoint-sha256`. Downgrades every recovered pass, resolution, and answered question for reconsideration. |

Generate the report with the existing `render_report.py`; this runtime does not duplicate rendering or HTML substitution. Browser inspection and semantic review remain separate checks performed by the host.

## Record contracts

IDs are stable strings containing letters, digits, dots, underscores, or hyphens, beginning with a letter or digit. Each collection has unique IDs; references always identify evidence. Unsupported fields, duplicate JSON keys, and non-finite numbers fail validation.

Evidence input:

```json
{
  "id": "ev-order-commit",
  "claim": "The handler writes the order before returning success",
  "type": "observed",
  "scope": "src/orders.py handler source at capture",
  "limitations": ["Static source inspection does not prove a successful runtime commit"],
  "sources": [{"path": "src/orders.py"}],
  "references": []
}
```

The CLI adds each source's `sha256` and evidence `freshness` (`current`, `stale`, or `unknown`). Paths must stay inside the declared root; parent traversal, absolute paths, and source symlinks are rejected. Dirty working-tree bytes are hashed directly. Evidence types are `observed`, `derived`, and `inferred`; the host must accurately classify the claim. Hash identity does not prove claim truth. `limitations` and `scope` are required. Evidence requires a local source or an external reference. External-only references remain unknown in freshness because this CLI does not fetch them; preserve a local dated source snapshot when reproducible external evidence matters. An evidence ID cannot be reused with replacement content.

Other input records:

```json
{"id":"q-durability","question":"When is an order durable?","status":"answered","evidenceRefs":["ev-order-commit"],"answer":"The handler acknowledges after its write; runtime guarantees need a separate check."}
```

```json
{"id":"u-restore","question":"Can the backup meet the recovery target?","status":"open","evidenceRefs":[],"resolution":""}
```

```json
{"id":"check-ack","check":"Inspect the handler's acknowledgement ordering","status":"pass","evidenceRefs":["ev-order-commit"],"detail":"Source ordering matches the stated boundary; runtime durability was not tested."}
```

Question status is `open | partial | answered`; unknown status is `open | resolved`; check status is `pass | fail | unknown`. Missing input status defaults to open, open, and unknown respectively. Missing `evidenceRefs` defaults to an empty array; answer/resolution/detail defaults to an empty string. Stored records carry every field explicitly.

A pass, resolution, or answered question requires references to currently fresh evidence and nonempty result text. This is a structural prerequisite, not a machine judgment that the evidence is sufficient. The host must still check scope, authority, and contradictions. Missing references are errors, not evidence to invent. All design-replacing mutations refresh existing evidence before publishing their records; checkpoint preserves bytes without changing freshness.

## State and checkpoints

`investigation` contains `session: {id, revision}` and `evidence`, `unknowns`, `questions`, and `checks` arrays. These are canonical tracked JSON alongside the design. Each successful state mutation advances the revision; init starts at zero. Checkpoint alone changes no revision. Recovery advances the restored checkpoint’s revision, which can be lower than the damaged document’s revision. A revision is session bookkeeping, not a globally monotonic concurrency token; the raw-file SHA detects ordinary design edits as well as runtime edits.

Before replacing the design, the runtime preserves exact previous bytes in the sibling `<design-stem>.history/<sha256>.json`. Track these snapshots with the design when retaining investigation history. Existing snapshots must match their names; they are never overwritten by a command. A corrupt current document can also be retained there as exact recovery evidence, despite its `.json` extension.

Writes use a same-directory temporary file, file synchronization, and atomic replacement. A sibling `.<design-name>.lock` coordinates CLI writers through an operating-system lock, released when the owner exits. The empty lock file contains no durable state; leave it in place and exclude it from commits. Do not delete it to resolve contention. POSIX uses `flock`; Windows uses byte-range locking. The Windows path requires validation on Windows before claiming platform coverage.

The SHA check and lock protect cooperating CLI writers. Ordinary editors do not acquire that lock. A second SHA check catches edits made during preparation, but an editor racing the final replace remains outside the cooperative protocol; do not edit the design concurrently with a runtime mutation. These filesystem guarantees do not imply immunity to disk failure or every network filesystem's behavior.

## Recover from observed failures

Normal commands return one JSON object on stdout, with `ok` and exit code zero on success, or exit code two and `error: {code, message, nextAction, neededArgs}`. `--help` is plain CLI help. A successful mutation returns the new SHA, session revision, and prior checkpoint path. After a timeout or lost reply, read status before retrying: the original command may already have committed.

| Error | Next action |
|---|---|
| `conflict` | Read status, reconcile the intended edit against the current records, and use the new SHA. Never just substitute the SHA and replay a stale replacement record. |
| `busy` | Let the owner finish, then reread status. Process death releases the lock; no stale PID deletion is needed. |
| `invalid_json` | Preserve the damaged file. Read `observedSha256` and `historyDirectory` from the status error; inspect candidate checkpoints before explicit recovery. |
| `invalid_record`, `dangling_reference`, `insufficient_evidence` | Correct the named record or collect missing evidence. An unavailable check remains unknown. |
| `stale_evidence` | Run resume, capture new evidence as needed, and re-evaluate affected claims. |
| `immutable_evidence` | Reuse the existing reference or create a new evidence ID. |
| `checkpoint_corrupt` | Preserve the corrupt snapshot and locate an independently verified copy. Never overwrite history to make a check pass. |
| `io_error` | Inspect the named path and permissions; read status before retrying because publication may already have completed. |

Explicit recovery:

```bash
python3 <skill-dir>/scripts/design_session.py recover \
  --design docs/design/example/design.json --root . \
  --expected-sha256 <current-raw-sha256> \
  --checkpoint-sha256 <verified-history-sha256>
```

The runtime never chooses an older success automatically. Recovery preserves the damaged preimage, verifies the selected snapshot, refreshes local sources, and downgrades recovered successful records. Inspect the result and re-establish the necessary evidence before declaring the investigation complete.
