# Realtime and sync archetypes

Selected from the router for [SKILL.md](../SKILL.md). Reusable mechanisms and decision ladders remain in [HEURISTICS.md](../HEURISTICS.md).

## Synchronised namespace with delta transfer
- **Shape**: cross-device sync, revisions, strong consistency of file state.
- **Match when** a mutable namespace is shared across devices and bandwidth makes whole-object transfer untenable. **Not when** the name is meant to be immutable — versioned artifacts want content addressing, and a mutable namespace fights that requirement.
- **Moves**: clients chunk files, compress, encrypt, and upload by checksum; **delta sync** sends changed chunks only; content-defined chunking preserves reuse after insertions; relational metadata and immutable version rows provide namespace truth; a per-namespace journal makes "changes since offset N" a range read; long polling notifies; offline clients surface both copies on conflict; cold storage holds stale blocks.
- **Staff gate**: define multipart integrity and finalization — the server verifies uploaded parts against the object store, and upload identity is a content fingerprint, never the store's own composite entity tag, which changes on copy. Specify block reference counting/GC, journal cursor semantics, rename/move atomicity, an index keyed by user for sharing, and offline conflict resolution. Compression happens before encryption. Global cross-user dedupe conflicts with true E2E encryption—choose explicitly rather than claiming both.
- **Anti-gate**: one device per user and no offline requirement — upload, download, and a version column are the design.
- **Cases**: cloud drives, large-file source control, backup clients, photo libraries, design-tool asset sync.

## Stateful connection fabric
- **Shape**: bidirectional real-time, offline delivery, multi-device, presence.
- **Match when** the connection itself is state the architecture must manage — routing, presence, resume. **Not when** updates are infrequent and one-way; polling or long polling stays correct and costs nothing to operate.
- **Moves**: WebSocket for both directions (HTTP for everything non-realtime); stateful chat servers + service discovery; expiring connection leases device→gateway; message-sync queue per device (inbox model; group send = bounded copies); wide-row store for history; message IDs time-sortable; heartbeat presence (~5 s ping, ~30 s timeout); content-free push for offline; per-device high-water mark for sync.
- **The dial**: connection routing and presence are ephemeral and may ride lossy pub/sub; accepted messages are not. Ordering follows causality, not wall clocks — logical clocks where order is contested.
- **Staff gate**: name the acknowledgement point, stale-lease recovery, reconnect/range-scan protocol, duplicate suppression, and gateway-deploy behavior. E2E encryption changes topology: servers cannot inspect content, push payloads are content-free, and a new device cannot silently backfill undecryptable history.
- **Numbers anchor**: 500M DAU × 20 msgs ≈ 115k msg/s avg; 1M connections ≈ 10 GB RAM but never one box.
- **Anti-gate**: below a few thousand concurrent connections with no offline requirement, long polling against the existing service is the design.
- **Cases**: chat and messaging, collaboration presence, trading and sports tickers, multiplayer lobbies, device command channels.

## Convergent replicated document
- **Shape**: concurrent edits converging to one document, with offline support. The difficulty lives in the data model, not the component graph — generate candidates on the conflict-resolution axis and hold topology fixed.
- **Match when** two writers may edit the same object with no coordination and both edits must survive. **Not when** one writer can be made authoritative cheaply — routing every write for an entity to one home leader dissolves the problem entirely.
- **Moves**: choose the conflict-resolution mechanism with the rule in [HEURISTICS.md](../HEURISTICS.md) — pessimistic locking rules out real-time collaboration, and differential sync survives only weak conflicts. Apply locally and propagate asynchronously; 150 ms cross-region is unhideable otherwise. Version history is a compacted operation log or periodic snapshot, never the live state.
- **Staff gate**: name the ordering authority and what the document does when it is unreachable. State the metadata cost and the garbage-collection/causal-stability story for whatever converges, the divergence window an offline client may accumulate before its edits stop being mergeable, and how the structural invariants no merge rule preserves — cycles, uniqueness, referential integrity — are validated. Presence and cursor traffic routinely exceed edit traffic: budget it separately, and never on the durable path.
- **Anti-gate**: a document with one editor at a time and a visible lock is a correct product decision, not a failure of ambition.
- **Cases**: collaborative documents and whiteboards, shared spreadsheets, design tools, note sync, code-review annotation.

## Offline-first client sync
- **Shape**: the on-device store is the read and write path, the network is an optimisation, and correctness is decided on devices you cannot schedule, observe, or roll back.
- **Match when** the product must work with no connectivity and the device holds authority between syncs. **Not when** the client is a thin view of a server that is always reachable — a cache with revalidation is simpler and has no merge semantics to get wrong.
- **Moves**: writes apply locally and append to a durable mutation outbox — the operation id is the idempotency key, so a crash mid-flight replays instead of dropping the edit; pull is a server-issued cursor delta, never a full-collection scan; deletes travel as tombstones or change-feed entries, because an absent row is indistinguishable from an unsynced one; blobs sync lazily off the metadata path behind a bounded on-disk LRU; every pass is resumable because the OS kills the process mid-step; one high-water mark per device, persisted with the data it describes.
- **Buy gate**: platform device-sync frameworks and managed offline-persistence layers already ship the outbox, the cursor, and a conflict path. A hand-rolled engine must beat one on a stated requirement — schema control, backend portability, end-to-end encryption — not on preference.
- **Staff gate**: never infer pending work by diffing `updatedAt` against `syncedAt` — that is an outbox with no durability, no retry count, and no dead letter. State cursor semantics, the divergence window, bytes and round trips per foreground session, the background-refresh budget, the disk eviction policy, and exactly what a user sees when two of their own devices disagree. Device-clock last-write-wins is non-deterministic loss, not a policy.
- **Anti-gate**: a read-mostly app with a spinner and a retry is a supported product, and it has no merge semantics to get wrong.
- **Cases**: mobile note and task apps, field-service and point-of-sale terminals, mail and calendar clients, offline mapping, local-first editors.
