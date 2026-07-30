# Derived serving archetypes

Selected from the router for [SKILL.md](../SKILL.md). Reusable mechanisms and decision ladders remain in [HEURISTICS.md](../HEURISTICS.md).

## Materialized fan-out and derived views
- **Shape**: read-heavy timeline assembly under fan-out.
- **Match when** one write must appear in many readers' precomputed views. **Not when** the audience per write is small or the view is cheap to assemble on read — precomputation is then pure waste plus an invalidation problem.
- **The dial**: fan-out on write (fast reads, celebrity hotkeys, wasted work for inactives) vs fan-out on read (slow reads, no waste) vs **hybrid** — push for normals, pull for celebrities. Follower-count distribution is itself a load parameter.
- **Moves**: feed cache holds IDs only, capped per user; five cache layers (feed / content / graph / action / counters); expensive mutations through job queues; precompute lists; partition vote/like queues by entity key. Federation (per-user repositories + relay firehose + index servers) is the decentralised variant.
- **Staff gate**: quantify the celebrity boundary and inactive-user waste rather than saying "hybrid" by habit. Replicate celebrity/hot-object caches across shards, bound read-time merge fan-out, and model tail amplification: one slow shard can dominate an otherwise fast feed. Every derived view states what rebuilds it and from which position.
- **Anti-gate**: fan-out under ~1k followers inside one datastore is a query with an index, not a pipeline.
- **Cases**: social timelines, activity feeds, notification inboxes, follower counters, search-visible denormalisations.

## Ranked retrieval index
- **Shape**: sub-100 ms per keystroke, prefix retrieval, ranked by frequency, rebuilt rather than updated.
- **Match when** reads dominate overwhelmingly and the index may lag its source. **Not when** results must reflect the last write — a freshness-critical lookup belongs on the authoritative store with an index, not a rebuilt one.
- **Moves**: trie with top-k cached at every node (O(1) via prefix-length cap + per-node cache); periodic rebuild from sampled analytics logs, snapshot into trie DB + cache; filter layer for unsafe suggestions; shard by prefix range via a shard-map manager (a–z is skewed); browser-side caching of suggestions.
- **The dial**: index freshness against rebuild cost — the rebuild cadence *is* the staleness guarantee.
- **Staff gate**: state the rebuild cadence, what serves during a rebuild, and how a bad index is rolled back. Name the skew in the shard key and the hot-prefix path. Say what a query returns when a shard is missing — partial results with a marker, or an error.
- **Numbers anchor**: 10M DAU ≈ 24k QPS, peak 48k.
- **Anti-gate**: below a few million documents with no per-keystroke budget, the datastore's own text index is the design.
- **Cases**: search autocomplete, product type-ahead, entity pickers, log and code search.

## Online decision under a deadline
- **Shape**: a model or rule set returns a scored decision inside a hard latency budget, and the budget is the product requirement — a late answer is a wrong answer.
- **Match when** every request needs a ranked, scored, or classified answer computed from features that change: fraud, recommendation, ad ranking, relevance, risk. **Not when** the decision can be precomputed per subject and looked up — a nightly batch into a key-value store is cheaper, more debuggable, and has no serving tail at all.
- **Minimum state**: the feature values a decision reads with their freshness, the model or rule version that produced it, and a decision log that allows replay and audit.
- **Moves**: caching and the latency fan-out rule are ladders in [HEURISTICS.md](../HEURISTICS.md). This shape pins: retrieve a bounded candidate set cheaply, then score only that set — never score the corpus. Features are read from a store written by the same pipeline that trained on them, or training and serving disagree silently. Every decision records its model version and inputs. The deadline is enforced by returning a partial result, so a slow feature degrades the answer rather than failing it.
- **The dial**: decision quality against the latency budget. Candidate-set size and model size both buy quality and spend the budget, and the tail rather than the mean is what the budget must cover.
- **Buy gate**: managed feature stores, vector indexes, and ranking services ship retrieval, versioning, and drift monitoring. Building must beat that on a stated requirement — a feature freshness they cannot serve, a corpus they price badly — not on the appeal of owning the model path.
- **Staff gate**: name the fallback decision when the model is unavailable and who is accountable for it, because the fallback runs during every incident. State the training-versus-serving skew check, the feature freshness each decision assumes, and how a bad model version rolls back inside one deploy. An adversary adapts: say what the decision does when its inputs are chosen by the party it judges.
- **Numbers anchor**: a 100 ms budget spent on 30 ms retrieval and a 40 ms p99 scorer leaves 30 ms for everything else, and the slowest of N parallel feature reads sets the tail — ten reads at p99 50 ms produce a fan-in p99 well above 50 ms.
- **Anti-gate**: a few thousand decisions a day over stable inputs — a rule table and a nightly batch beat a serving path with a model registry and a feature store.
- **Breaks first**: the fallback. It was written once, never exercised, and it is what serves during the incident that took the model down.
- **Cases**: fraud and risk scoring, recommendation and feed ranking, ad selection and pacing, search relevance, real-time content moderation.

## Global edge and hierarchical cache
- **Shape**: one origin serves a world; the edge absorbs the reads and the origin sees only misses.
- **Match when** the same bytes are requested by many clients far apart and staleness is tolerable for a stated window. **Not when** every response is personalised or authorised per request — that is compute at the edge, not caching, and a cache key wide enough to stay correct has a hit ratio of zero.
- **Minimum state**: a cache key, a freshness lifetime, and a validator per object; at the origin, the authority to invalidate.
- **Moves**: the caching ladder is in [HEURISTICS.md](../HEURISTICS.md); this shape pins where it resolves. The cache key is an explicit allowlist of the request attributes that change the response, never the whole request. Tiered parent caches collapse miss fan-in so the origin sees one request per object rather than one per edge. Serve stale while revalidating, and stale on origin error, both bounded. Invalidation is a purge by key or a change in the key itself — versioned immutable URLs make invalidation unnecessary.
- **The dial**: freshness against origin load. Lifetime is the one knob that moves both, and a purge path exists because some content cannot wait out its lifetime.
- **Staff gate**: state the hit ratio the origin's capacity assumes and what happens when it drops, because a cold or purged cache *is* an origin overload event — name the request collapsing and the admission behaviour that survives it. Say who may purge, how fast a purge reaches every edge, and what serves in the meantime. Enumerate the cache key attributes and prove authorised content cannot be served to the wrong client.
- **Numbers anchor**: at a 95% hit ratio the origin sees 5% of traffic; falling to 90% doubles origin load and a full purge multiplies it by 20. Origin capacity is sized by the miss rate at its worst, never by the steady-state hit ratio.
- **Anti-gate**: one region, traffic inside a single datacentre's capacity — a cache in front of the datastore is the design. A global edge tier adds a purge protocol and a debugging surface.
- **Breaks first**: the cache key. A missing attribute serves one client's response to another; a superfluous one drops the hit ratio to zero, and the origin discovers it at peak.
- **Cases**: content delivery networks, static asset and image delivery, edge API response caching, package mirror networks, streaming manifest and segment delivery.

## Spatial index over moving state
- **Shape**: "who or what is near me" at high QPS over a moving population.
- **Match when** entities move and staleness makes a result wrong rather than merely old. **Not when** the entities are static — a business listing wants a read-replicated index with the other filters in the same query, and importing leases, freshness TTLs, and heartbeats there adds machinery for movement that never happens.
- **Moves**: hierarchical spatial index—square cells with space-filling-curve locality or hexagonal cells with equidistant neighbours; cell ID as shard key; cover-the-radius then query a bounded shard set; timezone-driven hot cells spread over hosts; same-entity updates through one partition; map matching for noisy GPS; write-optimised store plus recency buffer.
- **Staff gate**: define freshness TTLs and lease expiry so vanished devices cannot remain matchable. Separate the AP location ocean from the tiny CP claim/assignment island, and persist the assignment workflow so retries cannot double-match. Size the candidate set and re-query radius from density, not a fixed global number.
- **Anti-gate**: a static dataset under a few million rows is a bounding-box query with a spatial index, not a partitioned ocean.
- **Cases**: ride dispatch, courier and delivery matching, presence and proximity, fleet tracking, geofenced alerts.

## High-volume ingest and rollup
- **Shape**: cost is bounded by a budget the architecture enforces at admission, not by whatever producers happen to emit.
- **Match when** the write rate is orders of magnitude above the read rate, most events are never read individually, and the value lives in aggregates over time — metrics, traces, logs, click and impression streams. **Not when** every event is money or must be counted exactly: metering and billing events cannot be sampled or dropped, and a pipeline built to shed under pressure will shed revenue.
- **Minimum state**: per series, its identity and its ordered samples; per ingest tenant, an active-series count and a rate budget. Raw events are not state — they are a retention tier.
- **Moves**: partitioning, LSM ingest, and log-versus-queue brokers are ladders in [HEURISTICS.md](../HEURISTICS.md). What this shape adds is two admission gates: cardinality — a new series identity is an authorised allocation, not a free side effect of a label value — and rate, a per-tenant budget enforced before the durable path. Sample on a hash of the correlation identity so a whole flow survives or none of it does, never per step, which yields fragments that answer nothing. Separate event time from arrival time, publish a watermark, and make late data a stated policy rather than a silent loss. Roll up on write into immutable time-partitioned parts; keep the raw tier short and the aggregate tier long.
- **The dial**: fidelity against cost, set by what the data is actually used for. Alerting needs recency and completeness across a few series; debugging needs depth on rare events — those pull the dial in opposite directions and cannot share one retention policy.
- **Buy gate**: managed metrics, log, and trace backends already ship ingestion, cardinality limits, downsampling, and query. Building one must beat that on a stated requirement — a residency boundary, a cardinality its pricing punishes, an ingest rate it will not accept — not on the belief that storing numbers is easy.
- **Staff gate**: state the cardinality budget as a number, what happens when a tenant exceeds it (reject, drop the label, or degrade), and who owns the mapping from series to owner. Say what a query returns when a partition is missing — partial results with a freshness marker, or an error. The pipeline must not share a failure zone with the systems it observes, and an incident is exactly when every producer emits more: reserve capacity for the alerting flow ahead of the exploration flow.
- **Numbers anchor**: one metric name across 200 hosts × 50 endpoints × 10 statuses × 5 zones is 500,000 series, not one metric; at a 15 s interval that is 33k samples/s and, at the 1–2 bytes per sample a compressed store achieves, 2.9–5.8 GB/day from a single careless label. Unsampled trace collection cost 16.3% average request latency in a production search cluster, while every sampling frequency at or below 1-in-16 fell inside the 2.5% measurement error — sampling is not a cost optimisation, it is what makes the instrumentation affordable at all.
- **Anti-gate**: a few thousand series and a few thousand events/s — one time-series store, full retention, no sampling, no rollup. Cardinality control, tiering, and a rollup pipeline are machinery for a problem the envelope does not have yet.
- **Breaks first**: cardinality, and it breaks the read side before the write side. Ingestion keeps accepting while dashboards and alerts time out, because one deploy added a label with an unbounded value.
- **Cases**: metrics platforms, distributed tracing backends, log aggregation, ad impression and click pipelines, product analytics streams.
