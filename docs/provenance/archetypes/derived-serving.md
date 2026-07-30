# Provenance — Derived serving archetypes

Sources for the runtime pack. Return to the [archetype provenance index](../ARCHETYPES.md).

## Materialized fan-out and derived views

| Claim | Source |
|---|---|
| Fan-out-on-write materializes home timelines; high-fan-out users are read and merged separately | https://www.infoq.com/presentations/Twitter-Timeline-Scalability/ (original presentation by Twitter's platform engineering lead) |
| A derived view needs a reconstruction source and cursor | [HEURISTICS.md — Async and streaming](../HEURISTICS.md#async-and-streaming) |
| “Five cache layers” is an illustrative decomposition, not a universal threshold | Runtime composition of feed IDs, content, graph, actions, and counters; no external correctness claim. |
| Fan-out under ~1k followers | Design-envelope anti-gate, not a measured universal crossover; the boundary must be recomputed from write fan-out, read assembly cost, and inactive-reader waste. |

## Ranked retrieval index

| Claim | Source |
|---|---|
| Prefix completion supports weighted, ranked suggestions | https://www.elastic.co/guide/en/elasticsearch/reference/current/search-suggesters.html#completion-suggester |
| Prefix-range partitions can be skewed, so a–z is not a balanced shard map | Design consequence of observed query-prefix frequency; the runtime requires measuring the selected corpus rather than asserting a universal distribution. |
| Sub-100 ms per keystroke | Product-envelope deadline, not a universal measured threshold. |
| 10M DAU and two requests per second during an assumed 100-second daily search session imply ≈23,148 QPS, rounded to 24k; 48k assumes a 2× peak | derived from explicit envelope assumptions, not a published service measurement. |
| “A few million documents” | Design-envelope anti-gate, not a universal index limit; datastore and query-plan measurements decide it. |

## Online decision under a deadline

| Claim | Source |
|---|---|
| Training and serving should use the same feature definitions to prevent training-serving skew | https://research.google/pubs/hidden-technical-debt-in-machine-learning-systems/ §3.2 |
| Two-stage retrieval bounds a candidate set before expensive ranking | https://research.google/pubs/deep-neural-networks-for-youtube-recommendations/ |
| The maximum of parallel dependency latencies determines fan-in completion | [HEURISTICS.md — The envelope](../HEURISTICS.md#the-envelope) |
| 100 ms − 30 ms retrieval − 40 ms scorer = 30 ms remaining | derived; all three figures are an illustrative product budget, not measured universal thresholds. |
| Ten feature reads each with a 50 ms p99 can have fan-in p99 above 50 ms | derived from order statistics; without an independence model no single combined percentile is claimed. |

## Global edge and hierarchical cache

| Claim | Source |
|---|---|
| Freshness lifetimes, validators, and stale-while-revalidate | https://www.rfc-editor.org/rfc/rfc9111.html · https://www.rfc-editor.org/rfc/rfc5861.html |
| Tiered parent caches collapse miss fan-in toward the origin | https://developers.cloudflare.com/cache/how-to/tiered-cache/ |
| A 95% hit ratio means the origin sees 5%; 90% doubles it; a full purge multiplies by 20 | derived |

## Spatial index over moving state

| Claim | Source |
|---|---|
| Hierarchical square cells can be mapped along a space-filling curve for locality | https://s2geometry.io/devguide/s2cell_hierarchy.html |
| H3 uses a hierarchical hexagonal grid and indexes neighbours | https://h3geo.org/docs/core-library/overview/ |
| A lease has a stated expiry; correctness-sensitive assignment requires fenced ownership rather than location freshness | [HEURISTICS.md — Replication and consistency](../HEURISTICS.md#replication-and-consistency) · [HEURISTICS.md — State survival and recovery](../HEURISTICS.md#state-survival-and-recovery) |
| “A few million rows” | Design-envelope anti-gate, not a universal spatial-index limit; density and measured query fan-out determine the boundary. |

## High-volume ingest and rollup

| Claim | Source |
|---|---|
| 1–2 bytes per sample compressed; reducing series beats reducing scrape frequency | https://prometheus.io/docs/prometheus/latest/storage/ |
| A series is metric name plus label set, so cardinality is the product of label cardinalities | https://prometheus.io/docs/concepts/data_model/ |
| Unsampled trace collection cost 16.3% average request latency; sampling at or below 1-in-16 fell inside the 2.5% measurement error | https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/ §4.1 |
| Sample on the correlation identity so a whole flow survives or none of it does | same, §4.4 · https://opentelemetry.io/docs/specs/otel/trace/sdk/ |
| Regional ingest with global query; partial results preferred over stale alerting | https://research.google/pubs/monarch-googles-planet-scale-in-memory-time-series-database/ |
| 200×50×10×5 = 500,000 series; ÷15 s = 33,333/s; ×1–2 B ×86,400 = 2.88–5.76 GB/day | derived |

**Rejected.** "1-in-16 sampling costs 2.12% latency." True as a table value, but the paper's stated
experimental error is 2.5%, so it is indistinguishable from zero and must not be quoted as a measurement.
