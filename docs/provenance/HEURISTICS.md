# Provenance — HEURISTICS.md

Checked 2026-07-31.

## Storage engine

| Claim | Source |
|---|---|
| A compaction backlog stalls writes and inflates read tails, so compaction throughput is capacity | https://github.com/facebook/rocksdb/wiki/Write-Stalls · https://github.com/facebook/rocksdb/wiki/Compaction |
| Under multi-version concurrency a B-tree retains old versions and dead index entries until vacuum; a long-running transaction pins them | https://www.postgresql.org/docs/current/btree.html · https://www.postgresql.org/docs/current/routine-vacuuming.html |
| Bounding two of read, update, and memory degrades the third | https://stratos.seas.harvard.edu/files/stratos/files/rum.pdf |

**Rejected.** "B-tree — each key lives in one place." False under multi-version concurrency. It was the
original text and is the reason this section was rewritten.

## Schema and encoding evolution

| Claim | Source |
|---|---|
| Explicit field identity; readers ignore unknown fields; round-tripping preserves them | https://protobuf.dev/programming-guides/proto3/#updating |
| Never renumber or reuse a retired tag; reserve it | https://protobuf.dev/programming-guides/proto3/#deleting |
| Reader/writer schema resolution and the direction of compatibility | https://avro.apache.org/docs/1.12.0/specification/#schema-resolution |
| Compatibility direction follows deploy order; checks belong in the build | https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html |

## Replication and consistency

| Claim | Source |
|---|---|
| W + R > N overlaps a **strict** quorum; a sloppy quorum uses the first N *healthy* nodes and voids the overlap | https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf §4.5, §4.6 |
| Overlap is not latest-value and never linearizability | https://jepsen.io/consistency/models |
| Session guarantees hold only where the session token travels | https://jepsen.io/consistency/models/monotonic-reads · https://jepsen.io/consistency/models/read-your-writes |
| A node outage should not trigger rebalancing of partition assignment | https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf §4.8.1 |
| Membership change is explicit, never inferred from failure detection | https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html |
| Fencing tokens: a lease holder's operations carry a monotonic sequencer the resource validates | https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/ §2.4 |
| Anti-entropy repair must complete inside the tombstone-collection window or deletes resurrect | https://cassandra.apache.org/doc/latest/cassandra/managing/operating/repair.html |
| Failure detectors are unreliable in an asynchronous system | https://dl.acm.org/doi/pdf/10.1145/226643.226647 |

## State survival and recovery

| Claim | Source |
|---|---|
| Local WAL commit and synchronous replication expose distinct durability/availability acknowledgement choices; asynchronous failover can lose recent committed transactions | https://www.postgresql.org/docs/current/wal-async-commit.html · https://www.postgresql.org/docs/current/warm-standby.html#SYNCHRONOUS-REPLICATION |
| A base backup plus a continuous sequence of archived WAL supports point-in-time recovery | https://www.postgresql.org/docs/current/continuous-archiving.html |
| Continuous replication can propagate corruption or destruction; recovery therefore also needs versioned or point-in-time backups | https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html |
| RPO and RTO are scoped recovery objectives; backup cadence follows RPO and measured restore time must fit RTO | https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/disaster-recovery-dr-objectives.html · https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_backing_up_data_identified_backups_data.html |
| Periodic isolated restores should validate integrity, measure achieved RPO/RTO, and exercise the real recovery procedure | https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_backing_up_data_periodic_recovery_testing_data.html · https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_planning_for_recovery_dr_tested.html |
| Consensus-backed ownership transfer plus fencing prevents an old owner from continuing writes after a new owner is active | https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/ §2.4 |
| Data checksums detect on-disk corruption and can be systematically verified | https://www.postgresql.org/docs/current/checksums.html · https://www.postgresql.org/docs/current/app-pgchecksums.html |

## Transactions

| Claim | Source |
|---|---|
| Read committed permits lost updates on read-modify-write; snapshot admits write skew | https://www.postgresql.org/docs/current/transaction-iso.html |
| Two-phase commit blocks because the coordinator is unreplicated; replicating the decision removes the stall | https://research.google/pubs/spanner-googles-globally-distributed-database-2/ |
| Optimistic conflict resolution with retry as the alternative to a blocking coordinator | https://www.foundationdb.org/files/fdb-paper.pdf |
| Sagas give up isolation — no effort is made to notify transactions that saw intermediate results | https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf |
| Idempotency: the dedup record commits with the effect; a stated retention window | https://docs.stripe.com/api/idempotent_requests |
| An effect at a third party dedupes on that party's mechanism | https://docs.stripe.com/api/idempotent_requests |
| Transaction scope follows invariant ownership — the uniquely identified entity is the scope of serializability | https://www.cidrdb.org/cidr2007/papers/cidr07p15.pdf |

**Rejected.** "~17 write TPS → sagas and two-phase commit are unjustified complexity" as a *causal*
rule. The figure survives as a calibration anchor; the inference does not. Throughput does not
determine transaction locality — ownership, atomic invariants, and datastore capability do.

## Async and streaming

| Claim | Source |
|---|---|
| A pipeline stage can scale and retry independently when a durable handoff separates it; large or externalised payloads travel by reference while the artifact lives in durable storage | https://learn.microsoft.com/en-us/azure/architecture/patterns/pipes-and-filters · https://learn.microsoft.com/en-us/azure/architecture/patterns/claim-check |
| Spool bytes = arrival bytes per unit time × tolerated backlog time | Derived from the arrival-rate form of Little's Law; see The envelope. |
| Change data capture feeds a private replica; a published event needs an outbox written in the same transaction | https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html |
| Event time versus processing time; the skew is unbounded | https://research.google/pubs/the-dataflow-model-a-practical-approach-to-balancing-correctness-latency-and-cost-in-massive-scale-unbounded-out-of-order-data-processing/ |
| A watermark is a heuristic completeness claim; late data needs a stated policy | same |
| State retention follows window plus lateness bound | https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/fault-tolerance/state/ |
| Checkpoint and output commit must be atomic together or replay double-counts | https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/fault-tolerance/checkpointing/ |
| Transaction boundaries do not automatically extend to external sinks | https://kafka.apache.org/documentation/#semantics |

## Interfaces and dependency contracts

| Claim | Source |
|---|---|
| HTTP methods have defined safety/idempotency semantics; `202 Accepted` does not mean processing completed | https://www.rfc-editor.org/rfc/rfc9110.html#name-methods · https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted |
| Long-running work is represented as an operation resource with state and eventual result or error | https://google.aip.dev/151 |
| GraphQL lets a request select fields over a typed schema; gRPC defines typed unary and streaming RPCs | https://spec.graphql.org/October2021/#sec-Language.Operations · https://grpc.io/docs/what-is-grpc/core-concepts/ |
| SSE is a one-way server-to-client event stream; WebSocket provides two-way communication after its opening handshake | https://html.spec.whatwg.org/multipage/server-sent-events.html · https://www.rfc-editor.org/rfc/rfc6455.html#section-1.2 |
| Cursor pagination uses an opaque page token tied to request arguments | https://google.aip.dev/158 |
| Backwards-incompatible API changes require versioning; deprecation needs a migration period | https://google.aip.dev/180 · https://google.aip.dev/185 |
| gRPC retries distinguish transparent retry from configured retry policy and can be throttled; deadlines bound how long a call may run | https://grpc.io/docs/guides/retry/ · https://grpc.io/docs/guides/deadlines/ |
| An idempotency key records the first request outcome and rejects parameter mismatch; ambiguous connection failures are retried with the same key | https://docs.stripe.com/api/idempotent_requests · https://docs.stripe.com/error-low-level#content-errors |
| Layered retries amplify attempts; retryable operations need exponential backoff and jitter, while non-idempotent operations require explicit safety | https://docs.cloud.google.com/storage/docs/retry-strategy |
| Unbounded queues turn overload into growing latency and make recovery harder; admission and queue age must be bounded | https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs/ |

## The envelope

| Claim | Source |
|---|---|
| Availability in sequence multiplies; in parallel is 1 − (1 − a)^n | https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html |
| Concurrency = arrival rate × service time | https://web.mit.edu/~sgraves/www/papers/Little's%20Law-Published.pdf |
| Retries multiply offered load exactly when capacity is lowest | https://sre.google/sre-book/handling-overload/ · https://sre.google/sre-book/addressing-cascading-failures/ |

## Style ratings matrix

| Claim | Source |
|---|---|
| Aim for three structurally distinct candidates, but draw only those that remain viable after the envelope and invariants | Product decision confirmed by user preference after the 2026-07-31 blind control test; the viability gate retains the test's proportionality correction. |
| A rating is never evidence; the recommendation chain rests on a number, an invariant, or a named failure mode | Internal: a candidate that scores itself and then cites the score is arguing in a circle. Observed across four red-team designs, three of which selected the same middle candidate carrying identical self-assigned scores. |
