# Provenance — Realtime and sync archetypes

Sources for the runtime pack. Return to the [archetype provenance index](../ARCHETYPES.md).

## Synchronised namespace with delta transfer

| Claim | Source |
|---|---|
| Rsync transfers differences using rolling and strong checksums rather than retransmitting an entire file | https://rsync.samba.org/tech_report/ |
| Content-defined chunking preserves chunk boundaries under insertions | https://www.usenix.org/conference/atc16/technical-sessions/presentation/xia |
| Multipart completion identifies parts and the service validates checksums; multipart ETags are not necessarily object MD5 digests | https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html · https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html |
| Compression must precede encryption because encrypted data is not compressible in general | https://www.rfc-editor.org/rfc/rfc3749.html#section-2.2 |
| Global cross-user deduplication leaks equality and conflicts with semantic security unless a convergent-encryption tradeoff is accepted | https://www.usenix.org/legacy/event/fast02/quinlan/quinlan.pdf |

## Stateful connection fabric

| Claim | Source |
|---|---|
| WebSocket provides bidirectional communication after an HTTP opening handshake | https://www.rfc-editor.org/rfc/rfc6455.html#section-1.2 |
| Accepted messages require durable delivery/deduplication while presence and connection routing may be ephemeral | [HEURISTICS.md — Async and streaming](../HEURISTICS.md#async-and-streaming) · [HEURISTICS.md — Transactions](../HEURISTICS.md#transactions) |
| 500M DAU × 20 messages/day ÷ 86,400 ≈ 115,741 messages/s | derived; DAU and messages/day are explicit design-envelope inputs, not current service measurements. |
| 1M connections ≈ 10 GB RAM | derived from an explicit 10 KB/connection sizing assumption; allocator, protocol, and application state must be measured. |
| ~5 s ping, ~30 s timeout, and “a few thousand” concurrent connections | Design-envelope tuning inputs, not protocol requirements or universal thresholds; RFC 6455 prescribes no heartbeat interval. |

## Convergent replicated document

| Claim | Source |
|---|---|
| CRDT replicas can update without coordination and converge after receiving the same updates | https://inria.hal.science/inria-00609399/document |
| Operational transformation and CRDTs carry different correctness and metadata/garbage-collection obligations | https://arxiv.org/abs/1810.02137 |
| Structural invariants such as uniqueness and referential constraints do not automatically follow from convergence | https://inria.hal.science/hal-01158370/document |
| 150 ms cross-region latency | Illustrative envelope input, not a universal network constant; measure the selected regions and use that result in the latency budget. |

## Offline-first client sync

| Claim | Source |
|---|---|
| Persist work so it survives process death and device reboot; execution remains subject to OS constraints | https://developer.android.com/develop/background-work/background-tasks/persistent |
| A sync protocol needs explicit change tokens/cursors and tombstones to communicate deletions | https://www.rfc-editor.org/rfc/rfc6578.html#section-3.6 · https://www.rfc-editor.org/rfc/rfc6578.html#section-3.7 |
| Mutation identifiers compose the idempotency rule already sourced in HEURISTICS.md | [HEURISTICS.md — Transactions](../HEURISTICS.md#transactions) |
| Device-clock last-write-wins can lose concurrent updates because clocks are not a causal order | https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/ |
