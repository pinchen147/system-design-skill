# Provenance — Investigation runtime

Sources for [RUNTIME.md](../../skills/system-design/RUNTIME.md). The runtime is a product decision grounded in [the harness research](../research/2026-10-21-harness-lessons.md).

## Start and resume

| Claim | Source |
|---|---|
| The installed host supplies reasoning; bundled Python tools manage records without model calls or installation | Local implementation contract. Python 3.9 compatibility checked by CLI tests; not a claim about untested Python/platform combinations. |
| Byte freshness covers dirty files and invalidates dependent completed judgments | Content-identity design, exercised by `scripts/test-design-session.py`. Current bytes identify the source, not claim truth. |

## Commands

| Claim | Source |
|---|---|
| Narrow commands with declared effects and recoverable errors | [REA tool design](https://github.com/morluto/rea/blob/705058f3e2df82503f1c601fc464aea7cbb626b8/docs/tool-design.md); command behavior is defined by local CLI tests. |
| Rendering is delegated to the existing renderer; structural validation is not semantic proof | Repository invariant and [MUSE outcome-policy separation](https://arxiv.org/html/2606.03005v1). |

## Record contracts

| Claim | Source |
|---|---|
| Explicit evidence identity, scope, limitations, and unresolved coverage | [REA reconstruction coverage](https://github.com/morluto/rea/blob/705058f3e2df82503f1c601fc464aea7cbb626b8/docs/reconstruction-coverage.md). Local fields and closed statuses are product contracts, not REA schema compatibility. |
| A nonempty evidence reference is necessary but not sufficient to support a completed claim | Logical distinction between reference integrity and evidence sufficiency; semantic judgment remains with the host. |

## State and checkpoints

| Claim | Source |
|---|---|
| Same-directory atomic replace, synchronized writes, and cooperating-writer locks preserve local state under the tested failure paths | Python standard-library `os.replace`, `os.fsync`, `fcntl.flock`, and `msvcrt.locking` contracts; real CLI tests exercise POSIX concurrency and retained snapshots. Windows branch is untested. |
| Digest comparison detects stale callers; noncooperating edits can still race the final replacement | Explicit implementation limit. Neither locking nor hashing claims protection against arbitrary filesystem failures or independent Git merges. |
| Canonical tracked JSON and preimage snapshots | User-selected product policy; no SQLite store, daemon, MCP dependency, or provider SDK. |

## Recover from observed failures

| Claim | Source |
|---|---|
| Diagnose the actual failure, preserve evidence, repair supported operations, and resume the task | [REA connection/recovery guide](https://github.com/morluto/rea/blob/a2d8b94dd50dab8d966239dd63ab84718aa8b4b4/.agents/skills/reverse-engineer-anything/references/connection-and-recovery.md). |
| Restore only an explicitly selected verified checkpoint; downgrade recovered successful judgments | Local conservative recovery policy, tested against corrupted current state and stale sources. Recovery restores records, not their truth. |
