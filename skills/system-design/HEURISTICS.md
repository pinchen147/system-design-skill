# Heuristics

The decision rules, numbers, and named principles [SKILL.md](SKILL.md) cites, from **Size the ask** through **Decide and deep-dive**. Cite principles by name in every recommendation — "the invariant lives in one store → local ACID transactions, not sagas (fix granularity, not transactions)" — so the reasoning is checkable.

This file owns the reusable mechanisms and every decision ladder. [ARCHETYPES.md](ARCHETYPES.md) names them and adds only what a shape changes; neither file restates the other.

## Contents

- [The laws](#the-laws) · [Characteristics](#characteristics-extract-then-pick-three) · [The envelope](#the-envelope) — formulas, latency and availability numbers, calibration anchors
- Decision rules: [Data model](#data-model) · [Storage engine](#storage-engine) · [Schema and encoding evolution](#schema-and-encoding-evolution) · [Caching](#caching)
- [Replication and consistency](#replication-and-consistency) · [State survival and recovery](#state-survival-and-recovery) · [Partitioning](#partitioning) · [Transactions](#transactions) — the ladders live here, not in the archetypes
- [Async and streaming](#async-and-streaming) · [Interfaces and dependency contracts](#interfaces-and-dependency-contracts) · [Scaling substrate](#scaling-substrate)
- [Style ratings matrix](#style-ratings-matrix) — priors for generating candidates, never evidence for one
- [Anti-overengineering gates](#anti-overengineering-gates) — cite when a candidate outruns its envelope

## The laws

- **Everything in architecture is a trade-off** — if a choice looks free, the trade-off has not been found yet.
- **Why beats how** — a topology diagram shows how; only recorded rationale preserves why. Hence the reasoning chains and the ADR on decision.
- **Least worst, not best** — never shoot for the best architecture; shoot for the least-worst set of trade-offs for the stated top-3 characteristics.
- **Earn every alternative** — first thoughts need challenge, not ceremonial tabs. Fully draw the simplest viable candidate, then add only alternatives that survive the envelope and differ on a load-bearing axis. A closed alternative is evidence for the recommendation, not a slot to refill; three is the ceiling.
- **The network is not reliable, latency is not zero, bandwidth is not infinite, topology changes, transport costs money.** Every distributed candidate pays these; say where.
- **Deep modules** — each service should hide a lot of behaviour behind a simple interface; a service whose API is as complex as its implementation is a shallow module wearing a network hop.

## Characteristics: extract, then pick three

Translate domain concerns before asking anyone to pick "-ilities":

| Domain concern | Implied characteristics |
|---|---|
| Mergers & acquisitions | Interoperability, scalability, adaptability, extensibility |
| Time to market | Agility = testability + deployability (one ingredient is not the cake) |
| User satisfaction | Performance, availability, fault tolerance, security |
| Competitive advantage | Agility, scalability, availability |
| Time and budget | Simplicity, feasibility |

Rules: implicit characteristics (availability, security) rarely appear in requirements but always matter; "thousands, one day millions" means scalability; bursty domains (ticket on-sale, auction close) mean **elasticity**, a different property from scalability. Have the user pick the **top three, in any order** — a design that tries to support everything sinks on launch.

## The envelope

Formulas: QPS = DAU × actions/day ÷ 86,400 · peak = 2–5× average (timezone-skewed products at the high end) · read QPS = write QPS × read:write · storage/day = items/day × %-with-payload × size · totals × 365 × retention years · replication ×3 · concurrency = QPS × service time · availability in sequence multiplies (three hops at 99.9% cannot exceed 99.7%), in parallel is 1 − (1 − a)^n — decompose the nines target across the primary flow's serial dependencies before committing to it.

**Unit economics** (compute whenever money crosses a boundary): revenue/event = conversion-rate × basket × take-rate · events/day = reach × exposures-per-reach × conversion-rate · payback days = build cost ÷ (revenue/event × events/day). When revenue per event is cents, the design budget is set by the provability of the event, not by its rate.

Discipline: round aggressively (99,987/9.1 → 100,000/10) · label every unit · write assumptions down and tag them `user` or `assumed` · verify the arithmetic with `python3 -c` before it enters a document.

**Powers of two**: 2^10 ≈ thousand (KB) · 2^20 ≈ million (MB) · 2^30 ≈ billion (GB) · 2^40 ≈ trillion (TB) · 2^50 (PB).

**Latency numbers**: memory reference 100 ns · compress 1 KB 10 µs · read 1 MB from memory 250 µs · same-DC round trip 500 µs · disk seek 10 ms · read 1 MB from disk 30 ms · cross-continent round trip ~150 ms. Conclusions: memory fast, disk slow; compress before the network; cross-region hops are felt by humans.

**Availability nines**: 99% = 3.65 days down/yr · 99.9% = 8.8 h · 99.99% = 52.6 min · 99.999% = 5.26 min. Each nine multiplies redundancy cost.

**Calibration anchors** (worked examples to sanity-check against): 150M DAU × 2 posts ≈ 3,500 QPS, peak 7,000 · URL shortener 100M/day = 1,160 write/s, 11,600 read/s · chat at 500M DAU × 20 msgs ≈ 115k msg/s avg, 3–5× peak · global booking platform ≈ **17 write TPS** against ~1k read QPS · workplace chat at 10M DAU ≈ 12k write / 120k read QPS · autocomplete 10M DAU ≈ 24k QPS, peak 48k · 1M WebSocket connections × 10 KB ≈ 10 GB RAM — one box, but never one box (single point of failure).

## Decision rules

### Data model
- Connectedness picks the model: key-value → document → relational → graph as item-to-item links increase.
- Self-contained trees loaded whole → document (locality, schema-on-read). Recurring many-to-many → relational (cheap joins; app-side join emulation just moves the complexity into your code). Traversals are the workload → graph.
- Non-relational justification menu: super-low latency, unstructured data, serialize-only access, massive volume. Otherwise default to a relational store.

### Storage engine
- Sustained ingest → LSM (random writes become sequential), but only while compaction keeps up: a compaction backlog stalls writes and inflates read tails, so budget compaction throughput as capacity. Range scans and a predictable p99 → B-tree, whose cost under multi-version concurrency is index bloat and vacuum lag rather than compaction — a long-running transaction pins garbage. Both amplify writes; bound two of read/update/memory and the third degrades.
- Analytics never runs on the transactional store — separate warehouse, column layout, ETL or CDC feed.

### Schema and encoding evolution
- Every stored record and every message outlives the code that wrote it. Encode with explicit field identity — tag numbers, or names with declared defaults — never positional; readers ignore unknown fields, and anything that round-trips a record preserves them.
- Compatibility direction follows deploy order: readers first → backward-compatible changes, writers first → forward-compatible, independent deploys or shipped clients → both. State which, per topic and per table.
- Always safe: add an optional field with a default, add an enum value the reader can fall back from. Never: renumber or reuse a retired tag, tighten a type, make an existing field required. Removing a field is two releases — stop writing it, ship, then stop reading it — and its number stays reserved. Compatibility checks belong in CI, not a runbook.
- State whether old records are migrated in bulk, upgraded on read, or kept readable forever. Silence here means forever, and the oldest bytes still in the store belong in a test.

### Caching
- Placement: beside the DB when queries are the bottleneck; at the API when computation is. Policies: TTL everywhere; write-through for freshness; write-behind only for lossy, latency-critical writes; cache-aside as the default read pattern. Cache is never the system of record.
- Cache the small hot set: feed IDs not feed bodies; users rarely scroll deep, so a capped list keeps hit rates high.

### Replication and consistency
- Single-leader is the default; multi-leader only for multi-region write latency or offline clients (conflicts arrive with it); leaderless for write availability with tunable quorums. W + R > N overlaps the read and write sets of one **strict** quorum — a sloppy quorum buys availability and voids that overlap, so name which you took. Overlap is not freshness and never linearizability; concurrent writes still need version semantics.
- Session guarantees — read-your-writes, monotonic reads, consistent prefix — are far cheaper than linearizability but hold only where the session token travels. Say what a second device, a downstream service, a cache tier, or a failover sees. Reserve linearizable, consensus-backed operations for locks, leader election, uniqueness, money.
- Failure detection yields suspicion, not truth: route around a suspected member, never reassign its ownership — ownership moves by explicit, quorum-agreed reconfiguration, and every lease-holder's write carries a monotonic fencing token the resource itself checks. Hinted handoff and read repair are best-effort; convergence needs a scheduled anti-entropy pass that completes inside the tombstone-collection window, or deletes resurrect.
- CP vs AP is chosen **per subsystem**: browse AP, checkout CP. And even without a partition, choose latency vs consistency explicitly.
- **Conflict resolution — pick by the coordination available, not by sophistication.** Avoidance is cheapest: route every write for one entity to one home leader and there is no conflict to resolve. Otherwise: a single ordering authority reachable on the write path → server-ordered last-write-wins registers per (entity, property), hybridised by field class — a sequence CRDT for text, a fractional index for sibling order, server-side validation for structural operations (cycles, uniqueness). No authority on the write path — peer-to-peer, unbounded offline, edge merge → CRDT, budgeting 4–10× metadata and a garbage-collection/causal-stability story. A central server *and* intention preservation across many operation types → operational transformation, budgeting O(k²) transform pairs. Last-write-wins over whole entities silently loses writes — say so, and name the mechanism that detects it. This is the single ladder; [ARCHETYPES.md](ARCHETYPES.md) does not restate it.

### State survival and recovery
- **Choose the acknowledgement point from the promised loss window.** Memory acknowledgement is admission, not durability: process loss may erase it. Local-WAL acknowledgement survives a process crash but not loss of that node. Replicated/quorum acknowledgement waits for independently failing durable copies and is the choice when an acknowledged write must survive promotion. Name whether each copy has received, durably logged, or applied the write. Immediate visibility additionally requires a read path that targets a known-applied copy or intersects the applied write set and selects its newest version; acknowledgement alone does not provide read-after-write consistency.
- **Choose replication by the promotion promise.** Synchronous acknowledgement adds replica delay and can block when the required replicas are unavailable; asynchronous acknowledgement avoids waiting for replicas but exposes a measurable lag-dependent acknowledged-loss window on failover. Before promoting, compare replay positions against the loss contract for that failure scope; after promotion, prevent split brain through consensus-backed ownership transfer and a new epoch/fencing token that every write target validates.
- **Choose recovery material, not just replicas.** Replicas serve traffic and shorten failover, but replicate deletion and corruption; backups are independent, retained recovery points. Recover mutable state from a verified snapshot plus ordered WAL/log replay. Retain logs and catalog recovery points to support point-in-time recovery (PITR), including a target immediately before a destructive event.
- **Turn RPO/RTO into a restore budget per failure scope.** Keep the acknowledged-write promise separate: ordinary promotion may allow no acknowledged loss while regional loss, corruption, or operator error has a time-based RPO. RPO sets the oldest acceptable recovery point and therefore replication/log/backup retention and cadence; RTO sets the longest acceptable outage and therefore automation and provisioned restore capacity. Minimum bulk restore time = bytes to restore ÷ sustained end-to-end restore throughput, then add provisioning, log replay, validation, and cutover. If that sum exceeds RTO, reduce bytes/replay or pre-provision more parallel restore capacity.
- **Prove recoverability.** Checksum blocks and manifests, verify backups on creation, and scrub stored data periodically so latent corruption is found before the only good copy expires. Run timed restore drills into an isolated environment, replay through the target point, verify application invariants and sampled reads, record achieved RPO/RTO and throughput, then fix the bottleneck. A backup that has not passed this path is an assertion, not a recovery plan.

### Partitioning
- Hash for even spread, key-range for range scans, compound (hash(prefix), range-suffix) for per-entity time series. Never `mod N` on an elastic cluster — consistent hashing exists for this.
- Celebrity keys: hashing does not help when one key is hot — hybrid fan-out (push for normals, pull for celebrities), salted keys, or dedicated shards.
- Secondary indexes: local per-partition (scatter-gather reads) vs global term-partitioned (fan-out async writes) — pick by whether reads or writes dominate the filtered access.

### Transactions
- Keep an invariant inside one transactional authority. Isolation is chosen per invariant, not per system: read committed permits lost updates on read-modify-write and snapshot adds write skew, so name the invariant, then pick an atomic single-statement update, a locking read, a materialised lock row, or serializable with a retry loop.
- Cross-partition atomicity needs an atomic-commit protocol, and classic two-phase commit blocks only because its coordinator is unreplicated — replicate the commit decision, or resolve conflicts optimistically and retry, and the stall goes with it. Cross-service "transactions" are sagas: a durable step log, compensations that are themselves idempotent and driven to completion, and no isolation — others read intermediate state, and nobody is told when it is undone — so non-compensable effects (money out, mail sent) go last. Both are granularity smells first: don't do transactions across services — fix the service boundaries instead.
- Exactly-once = at-least-once delivery + idempotent apply: a client-generated key, and a dedup record committed in the same transaction as the effect — stored apart, it is the dual-write problem again. Correctness checks live at the endpoints: state the key's retention window, and remember an effect landing at a third party is idempotent only through that party's own mechanism, not yours. Payments: append-only event log beside mutable state, same transaction; double-entry ledger; webhook receivers verify-store-ack and process async.

### Async and streaming
- Queues absorb spikes and decouple producer scaling from consumer scaling; the fee is asynchrony (job IDs, status polling). Partition queues by entity key for per-key FIFO and less lock contention.
- When an expensive or non-repeatable acquisition stage feeds an independently failing or scaling stage, persist a short-lived input artifact and durably enqueue its pointer before acknowledging acquisition. Size the spool from arrival bytes × tolerated backlog age. Skip this seam only when refetch is demonstrably cheaper than retention and replay.
- Log broker (replayable, offset-based) when consumers replay, fan out, or arrive later; queue broker (per-message ack) for independent tasks. Backpressure is a design decision, not a surprise: block, drop, or spill — choose.
- Never dual-write two stores from app code. For a private replica, tail the system-of-record's change log; for an event other teams consume, write an outbox row in the same transaction as the effect — a row diff is not an event contract, and its schema is your table's rather than your consumers'. Declare every store as source-of-truth or derived-from-what.
- Every aggregate over a stream has two clocks — event time, when it happened, and processing time, when you saw it — and the skew between them is unbounded. Aggregate on event time, or a replay returns a different answer than the live run did.
- A watermark is a heuristic claim that event time has passed *t*: too fast drops late data, too slow lets one straggler hold every result. State the lateness bound and where events past it go.
- Window plus lateness bound sets state retention — name that TTL or the store grows forever. Late data means an emitted result must change: choose per consumer between overwrite, correction, and discard, and monitor watermark lag separately from consumer lag. The checkpoint and the output commit are atomic together or replay double-counts.

### Interfaces and dependency contracts
- **Model the boundary before choosing transport.** Stable nouns with CRUD and cache semantics → resource API; an action with domain intent, side effects, or no natural resource → command. Public resource-oriented HTTP → REST; low-latency typed service calls or streaming → RPC; client-selected traversal across an aggregated graph → GraphQL. The style does not supply authorization, idempotency, or transaction boundaries: state those separately.
- **Choose completion semantics.** If work reliably completes inside the caller's deadline, return the result synchronously. Otherwise create an operation resource with a stable ID, authoritative lifecycle state (`PENDING | RECONCILING | SUCCEEDED | FAILED | CANCELLED`), result/error, and cancellation semantics; `202` means accepted, not completed. `UNKNOWN` is only a caller observation after an ambiguous timeout, never authoritative state. Expose progress by polling for broad compatibility, webhook for sparse server-to-server completion, SSE for one-way browser event streams, or WebSocket only when both sides need a long-lived bidirectional channel.
- **Bound collections and evolution.** Use opaque cursor pagination for live or growing collections; define stable ordering and cursor expiry, and reserve offset/page numbers for snapshot-like data where random page jumps matter. Prefer additive changes; version only intentional incompatibility, publish a deprecation date and migration path, measure remaining old-version use, and keep the old contract until the announced window closes.
- **Assign the dependency budget and retry owner.** Every call gets a deadline inside its caller's remaining budget. Retry only transient failures and explicit throttling, with capped exponential backoff, jitter, and a retry budget; do not retry validation, authorization, or permanent domain rejection. Exactly one layer owns retries. Bound concurrency and backlog; on saturation block/admit, shed, or spill explicitly and propagate pressure rather than creating an unbounded queue.
- **Scope idempotency to the effect.** Request deduplication scopes the same key to the caller and operation, verifies equivalent parameters, and returns the recorded outcome for a declared retention window. That local record does not make a payment, email, or other external effect idempotent; use the dependency's effect key or reconcile against its durable identifier.
- **Represent ambiguity.** A timeout or disconnect after dispatch leaves the caller's observation `UNKNOWN`: the external effect may have committed even while the authoritative operation remains pending. Do not blindly issue a new command. Retry with the same idempotency key when supported; otherwise move the operation to `RECONCILING`, query by a stable business identifier, surface pending/unknown externally, and conclude success or failure only when reconciliation supplies evidence.
- Client bytes are a budget: pass minimal data; pre-signed URLs send blobs straight to storage so app servers carry metadata only.

### Scaling substrate
The default evolution order, so candidates do not skip steps: single box → split web/data tiers → load balancer + stateless web tier (session state externalised; sticky sessions are the anti-pattern) → DB replication → cache + CDN → multi-DC with geoDNS → queues to decouple → shard the data tier. Redundancy at every tier; monitor and automate from the start.

## Style ratings matrix

Per-style ratings, 1–5 (cost: 5 = cheapest). These rows are **priors, not scores**: start from the row for the candidate's style, then move every cell this design's components, envelope, or failure modes justify moving, and say why in its `tradeoffs`. Architecture 0 is rated the same way. The top-3 characteristics decide which columns dominate.

| Style | Partition | Quanta | Deploy | Elast | Evolv | FaultTol | Modul | Cost | Perf | Reliab | Scal | Simpl | Test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Layered monolith | Technical | 1 | 1 | 1 | 1 | 1 | 1 | 5 | 2 | 3 | 1 | 5 | 2 |
| Modular monolith | Domain | 1 | 2 | 1 | 3 | 1 | 4 | 5 | 3 | 3 | 1 | 4 | 3 |
| Pipeline | Technical | 1 | 2 | 1 | 3 | 1 | 3 | 5 | 2 | 3 | 1 | 5 | 3 |
| Microkernel | Dom+Tech | 1 | 3 | 1 | 3 | 1 | 3 | 5 | 3 | 3 | 1 | 4 | 3 |
| Service-based | Domain | 1..n | 4 | 2 | 3 | 4 | 4 | 4 | 3 | 4 | 3 | 3 | 4 |
| Event-driven | Technical | 1..n | 3 | 5 | 5 | 5 | 4 | 3 | 5 | 3 | 5 | 1 | 2 |
| Space-based | Dom+Tech | 1..n | 3 | 5 | 3 | 3 | 3 | 2 | 5 | 4 | 5 | 1 | 1 |
| Microservices | Domain | 1..n | 5 | 5 | 5 | 4 | 5 | 1 | 2 | 4 | 5 | 1 | 4 |

Selection rules: one characteristic set for the whole system → a monolith family (layered for small/simple, **modular monolith** for domain-first). Differing characteristics per part → distributed; **quantum analysis** (independently deployable + own data + async seams) tells you where the split earns itself. Service-based is the pragmatic distributed default — ACID inside coarse services, no saga tax. Event-driven for reactive scale and extensibility; broker topology for decoupling, mediator for workflow control. Space-based for extreme bursty concurrency (>10k concurrent, ticketing-shaped). Microservices only with differing per-workflow characteristics AND mature automation — its 1-star cells are cost and simplicity, and they are honest.

Candidate-generation stance: fully draw the simplest production-viable candidate first. Add a measured-scale-boundary or dominant-risk alternative only when it survives the envelope and changes a load-bearing structural, data, or async axis. Keep a closed option as a one-line rejection, never refill its slot, and stop after three. Rate every drawn candidate honestly — one with no 1-star cell has not been examined, and one whose every cell equals its style row has been looked up, not rated.

## Anti-overengineering gates

Numbers kill complexity; cite these when a candidate reaches for more than the envelope justifies:

1. ~17 write TPS → one ACID database with capacity to spare (global booking platforms run at this rate). Rate removes the scaling excuse only: sagas and two-phase commit are earned by an invariant that spans owners you cannot put in one transaction, never by throughput.
2. ~100 avg TPS → a single well-built service on a few boxes; do not shard yet.
3. Read:write 100:1 → spend on CDN, cache, and read replicas — not write scaling.
4. Blob bytes dwarf metadata bytes → two storage problems, two stores (90 TB of audio beside 3 GB of metadata).
5. Delivered-then-deleted messages → storage sized by the undelivered backlog, not raw volume (10 TB/day ingested, but only the undelivered fraction × its wait persists: ~1 TB steady state against a 300 TB 30-day ceiling).
6. Most functions fire less than once a minute → scale-to-zero beats warm fleets.
7. Start monolith; earn distribution with measured evidence.
8. Design for the next order of magnitude, not 100× — and say which order of magnitude that is.
9. Revenue at risk over a quarter (revenue/event × events/day × 90) below one engineer-week of build cost → instrument, ship, and measure the real loss rate before building machinery to prevent it. Correctness machinery is priced like scale machinery: 3k clicks/day × 3% conversion × $35 basket × 8% take ≈ $250/day, so a whole day of lost attribution costs less than the queue that would have saved it.
