# Provenance — Authoritative state archetypes

Sources for the runtime pack. Return to the [archetype provenance index](../ARCHETYPES.md).

## Scarce resource reservation

| Claim | Source |
|---|---|
| 1.5M reservations/day ÷ 86,400 ≈ 17 average writes/s | derived illustrative envelope; peak burst remains an input to measure, not a published platform fact. |

## Money movement and ledger

| Claim | Source |
|---|---|
| The network authorizes on an unreachable issuer's behalf and the issuer must settle what was approved — the reason CP-everywhere was false | Visa Interlink Core Rules, stand-in processing |
| Balanced immutable double-entry postings | https://docs.tigerbeetle.com/coding/financial-accounting/ |
| Idempotency keys with a retention window | https://docs.stripe.com/api/idempotent_requests |

## Single-authority ordered state

| Claim | Source |
|---|---|
| 6 million orders per second on a single thread | https://martinfowler.com/articles/lmax.html |
| State derived entirely from a replayed input event stream | same |
| Consumers detect gaps by sequence number and request retransmission | https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf |
| Cancel and replace as first-class ordered commands | https://www.nasdaqtrader.com/content/technicalsupport/specifications/TradingProducts/Ouch5.0.pdf |
| Deterministic replay as a recovery and testing primitive | https://www.foundationdb.org/files/fdb-paper.pdf |
| 100,000 × 86,400 = 8.64e9; ÷ 6e6/s = 1,440 s = 24 min | derived |

## Replicated authoritative store

| Claim | Source |
|---|---|
| Consistent hashing with virtual nodes; sloppy quorums write to the first healthy preference-list members; hinted handoff and anti-entropy repair | https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf §4.2–4.7 |
| Memtable-to-SSTable write path and Bloom filters | https://cassandra.apache.org/doc/latest/cassandra/architecture/storage-engine.html |
| Repair must complete within the tombstone grace window or deleted data can reappear | https://cassandra.apache.org/doc/latest/cassandra/managing/operating/repair.html |
| Failure suspicion must not itself reassign ownership; shared-state operations require fencing at the resource | [HEURISTICS.md — Replication and consistency](../HEURISTICS.md#replication-and-consistency) · [HEURISTICS.md — State survival and recovery](../HEURISTICS.md#state-survival-and-recovery) |
| 40M live carts and 10 KB per cart | Design-envelope inputs, not measured platform facts; 40M × 10 KB ≈ 400 GB and ×3 replicas ≈ 1.2 TB are derived. |

## Monotonic identity and short codes

| Claim | Source |
|---|---|
| A 64-bit ID layout with 41 timestamp, 10 worker, and 12 sequence bits, plus clock-regression handling | https://github.com/twitter-archive/snowflake/tree/snowflake-2010 |
| 41 milliseconds-of-epoch bits provide approximately 69 years | derived from the sourced Snowflake layout: 2^41 ms ÷ 365.2425 days/year ≈ 69.7 years |
| Base-62 encoding of a unique integer remains unique; 62^7 = 3,521,614,606,208 | derived |
| 100M/day ÷ 86,400 = 1,157/s (rounded to 1,160/s); 10× read ratio = 11,600/s | derived; 100M/day and the 10:1 ratio are explicit design-envelope inputs, not measured platform facts. |
| 100M records/day × 1 KB × 3,650 days = 365 TB over 10 years | derived from the runtime's explicit envelope inputs. |
