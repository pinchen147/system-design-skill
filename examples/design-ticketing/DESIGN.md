---
date: 2026-07-31
mode: greenfield
status: draft
---

# Design a high-demand ticket on-sale

## Context

A ticketing platform for one 60,000-seat venue on-sale across 6 price tiers. Two million fans arrive in the first 60 seconds against a seat writer measured at 300 seat-state transitions per second, holds last 10 minutes, and payment authorization and its webhook are slow, duplicated, and out of order. Zero double-sales, no overbooking, and no fan charged without a seat. Platform-wide the system is tiny — 40 million tickets a year is 2.54 transitions per second — so the whole problem is a burst around an immovable writer with money crossing a third-party boundary.

Constraints: the 300 transitions/s seat writer is a measurement, not a target, and no candidate may assume it moves; the 600 s hold duration is fixed by the promoter contract; single region, multi-AZ, so no cross-region consensus sits on a CP path; one team that can operate Postgres, Redis, a CDN, and one payment integration — not a fleet.

## Requirements

| id | Functional requirement | Priority |
|---|---|---|
| fr-1 | Queue and admit: a fan arrives, receives a draw position, and is admitted to purchase or told no | core |
| fr-2 | Select and hold: an admitted fan holds seats for up to 600 s | core |
| fr-3 | Pay and finalize: authorize, assign seats in one atomic transaction, capture, issue entitlement | core |
| fr-4 | Release: explicit release and expiry-driven reaping back to AVAILABLE | core |
| fr-5 | Reconcile: every payment reaches a terminal state and every captured dollar has a seat behind it | core |
| fr-6 | Non-authoritative live availability: seat map plus per-tier counters | core |
| fr-7 | Fan picks a specific seat rather than accepting best-available | stretch |

| Axis | Target | Rationale |
|---|---|---|
| correctness | no seat is SOLD to two orders; SOLD + HELD + BLOCKED + AVAILABLE = 60,000 per event at all times | user-stated invariant; the seat table *is* the count, so there is no separate counter to drift |
| correctness | no fan is charged without a seat (P0), and no seat is SOLD without money | user-stated P0; 33 candidate incidents per on-sale at a 0.1% rate makes the machinery earned |
| throughput | 300 seat-state transitions/s sustained — a measured ceiling, not a target | every decision is sized against it rather than trying to raise it |
| elasticity | absorb 33,333 arrivals/s for 60 s and 50,000 sustained read QPS while the writer stays at 300/s | arrivals exceed writer capacity 111:1; the burst is the whole problem |
| latency | the admission decision is a local signature check with zero network calls; 94% of arrivals get a terminal answer by t≈60 s | a limiter that calls out to decide has become the overload it was built to prevent |
| durability | zero committed transactions lost on one-AZ loss; RPO ≤ 60 s and RTO ≤ 30 min for whole-region loss | acknowledgement is WAL fsync plus synchronous standby apply, so no earlier acknowledgement exists to lose |
| auditability | admission order is re-derivable from a persisted seed months after the on-sale | a disputed on-sale must be reproducible; a seed is cheaper than a replayable command journal |
| availability | purchase chain is 99.740% serial; the published number is failover seconds inside the on-sale window, not annual nines | 0.9999 × 0.9995 × 0.9990 × 0.9990 — a 99.99% purchase-flow claim would be arithmetically false |

Top three characteristics: **reliability**, **elasticity**, **simplicity** (assumed, extracted from the domain). Three invariants including a P0 make correctness under partial failure the product. A 118:1 peak-to-average write ratio and a 26,000:1 arrival burst against a 2.54 transitions/s steady state is elasticity, which is a different property from scalability and the one bursty domains need. One team that cannot operate a fleet makes simplicity load-bearing. Deliberately *not* in the top three: raw performance, because the writer is fixed at 300/s and no performance work may move it, and scalability, because there is nothing to scale.

Out of scope: dynamic and surge pricing · secondary market, resale, and fan-to-fan transfer · venue seat-map authoring and CAD · gate scanning hardware and offline turnstile validation (the entitlement token format is in scope, the scanner is not) · scalper and bot detection models (the enforcement hooks are in scope: per-account limits, device attestation slot, admission-token binding) · refunds, exchanges, and post-event customer service · multi-currency, tax, and promoter settlement · the pre-sale and verified-fan qualification funnel that runs days earlier.

Accepted conflicts:

- The fixed 600 s hold and a fast sell-out pull in opposite directions — the hold owns 61.4% of the 2,149 s t99 tail and is not negotiable → attack *how many holds reach expiry*, not the duration. An explicit release path turns a 600 s lock into a ~45 s one for the fans who take it, moving t99 to 1,551 s at 60% adoption.
- A live seat map and a P0-safe payment pull in opposite directions — an authorization can land on a hold that has already expired → reserve a 68 s payment window inside every hold and refuse to start a checkout below it. 11.3% of every hold is spent buying the elimination of that entire failure class.
- Fans picking their own seats conflicts with a fixed 300/s budget — contention at 20% concentration on one seating block costs ~14 aborted writes/s, and an aborted conditional UPDATE still spends a lock acquisition → degrade to server-assigned best-available during the rush; seat choice re-enables when AVAILABLE exceeds 25% of inventory.
- Registered demand for this event is 33:1 against inventory, which crosses the stated 20:1 trigger for the deferred-draw candidate → recorded as a documented, pre-built switch and escalated to the product owner. Deleting the live seat map is a product decision with contractual consequences, not an agent's call.

## Core entities and invariants

- **Seat** — the invariant carrier. No seat is SOLD to two orders: the conditional UPDATE's affected-row count *is* the outcome, never a SELECT followed by an UPDATE. SOLD + HELD + BLOCKED + AVAILABLE = 60,000 at all times. The table is the count; per-tier counters are a derived projection that may lag and may never be believed.
- **Hold** — a time-boxed exclusive claim. Expiry is a query against a durable `expires_at`, never a cache TTL. A hold carrying a live payment lock is untouchable by the reaper even past its expiry. A reaper and a finalizer racing on one hold are arbitrated by the conditional UPDATE; the loser sees zero rows and stops.
- **Order** — the bounded multi-step purchase execution. State moves forward only, enforced by a CHECK on a rank column. The client idempotency record is committed in the same transaction as the effect it dedups. The per-account limit is enforced inside the finalization transaction, across all six tiers.
- **Payment** — the money side, whose authority lives at a third party that offers neither ordering nor exactly-once. Capture is reachable only from a committed SOLD transition, and every other path voids the authorization. Assignment is reachable only from an AUTHORIZED payment. Every payment reaches a terminal state including `UNKNOWN`, which is a first-class state with a named owner and a 5-minute SLA rather than a retry. The provider idempotency key is attempt-invariant, so a retry after a timeout reaches the same authorization instead of creating a second one.
- **Ledger entry** — written in the same transaction that captures; money and its record are never two writes. Never updated; a correction is a reversal entry. The nightly audit `sum(credits) = count(SOLD) × price` must balance or settlement is blocked.
- **Queue admission** — admission order is reproducible from a persisted, published seed months later. One position per account, so refreshing the page does not buy a second entry. No money and no seat depends on this store: it is auditable, not authoritative.
- **Entitlement** — identity is 128 bits of randomness and deliberately *not* time-sortable, because an entitlement is a capability and a sortable id is an enumeration attack. The displayed barcode is a rotating derivation, so a screenshot is not a ticket. The entitlement exists whether or not its delivery email does.

## Data and consistency model

**Seat.** One row per seat per event, keyed `(event_id, seat_id)` where `seat_id` is section/row/number — 60,000 rows and about 3.6 MB per event including indexes. Beside it, and explicitly not authoritative, the allocator holds a per-tier pre-sorted candidate queue of AVAILABLE seat ids (60,000 × 8 B = 480 KB) computed once at event load and rebuilt from the table on restart. Identity is stable forever: never reissued, never renumbered, because a resold seat number is a dispute nobody can settle. Ordering authority is the row itself, via a conditional UPDATE whose affected-row count is the outcome — the allocator is a rate shaper and contention eliminator, not the authority, and if the allocator is wrong the database rejects the write. Conflict resolution is avoidance rather than resolution: every seat write for one event routes through one allocator which dequeues each seat to exactly one order, so there is no conflict left. Where a race still occurs — a reaper and a finalizer touching one hold — the arbiter is the affected-row count. Last-write-wins is forbidden here; it would silently lose a sale. The durability point is local WAL fsync plus synchronous apply acknowledgement from a same-region standby; the fan sees "the seat is yours" only after that, because acknowledging earlier creates a loss window the P0 invariant cannot absorb. Seats are never deleted: rows move to a partitioned archive after settlement, which at 0.94 TB over seven years is query hygiene rather than space.

**Hold.** A row carrying the seat ids it moved to HELD, written in the same transaction as those seat updates, so a hold never exists without its seats. Two timestamps matter: `expires_at`, which the reaper scans, and `payment_locked_until`, which forbids the reaper from touching it. Identity is a server-minted time-sortable `hold_id`; the client's idempotency key maps to it, so a duplicate submit returns the same hold rather than consuming a second one out of a fixed budget. Expiry is a reaper query, never a cache TTL — a TTL in Redis expiring a hold whose seats live in Postgres is the dual-write problem with a P0 attached. The reaper/finalizer race resolves by `UPDATE hold SET state='CONVERTING' WHERE hold_id=$1 AND state='ACTIVE' AND expires_at > now()`: the loser sees zero rows and stops. No compensation, no saga, no ambiguity. RELEASED and EXPIRED holds are dispute evidence for 30 days.

**Order.** A mutable order row beside an append-only `order_event` table written in the same transaction — a row diff is not an event contract. A client-generated idempotency key, stable across retries, maps to a server-minted `order_id`; the dedup record is committed in the same transaction as the effect, because stored apart it is the dual-write problem again. The state machine `DRAFT → AUTHORIZING → AUTHORIZED → ASSIGNING → ASSIGNED → CAPTURING → COMPLETED`, with `FAILED`, `VOIDED`, and `UNKNOWN` as terminal or quarantine states, is enforced by a monotonic rank rather than by code, so there is one writer at a time and no conflict to resolve. The durability point is the finalization commit — the same commit that moves seats to SOLD, mints entitlements, writes both ledger legs, and writes the outbox row.

**Payment.** A mutable payment row plus an append-only `payment_event` table holding the raw provider payload, the provider event id, both timestamps, and the signature verification result — written in the same transaction as the state advance. The provider idempotency key is deterministic and attempt-invariant: a hash over order id, amount, currency, and payment-method token, so a retry after a timeout reaches the same provider-side authorization. Ordering is monotonic by local rank — `INITIATED(0) → AUTHORIZED(1) → CAPTURED(2)`, with `UNKNOWN(1.5)` and `VOIDED`/`FAILED(3)` — and the provider is not consulted for order because the provider does not offer one. A webhook may only advance state: `UPDATE payment SET state=$new WHERE payment_id=$1 AND state_rank < $new_rank`. A CAPTURED webhook arriving before its AUTHORIZED applies the capture, and the later authorization matches zero rows and is discarded with a log line. Duplicates die on a unique `(provider, provider_event_id)`. This is the single ordering rule the whole payment path rests on, and it needs no ordering guarantee from anyone. For the fan the durability point is the finalization commit — money moves after the seat is committed, never before. `payment_event` is retained 7 years and exempt from erasure; card fields are redacted at write and the card number never enters the system.

**Ledger entry.** Append-only, double-entry, immutable rows in the same store and the same transaction as the capture, keyed `(order_id, leg, sequence)`. Money and its record are never two writes, which is what makes the nightly audit meaningful rather than decorative. A correction is a reversal entry, never a mutation, so the history of a dispute survives the resolution of it. Never deleted; rolled to cold storage after 7 years.

**Queue admission.** A sorted set keyed by event, member account, score draw position — 2,000,000 × ~100 B = 200 MB. The draw seed and the ordered position list are snapshotted to durable object storage immediately after the draw closes, so the in-memory structure is a fast index over a durable artifact rather than a store of record. Ordering authority is a seeded shuffle over everyone who arrived inside the 60 s window, executed once by one process from one published seed — not FIFO by arrival millisecond, which rewards fast networks, proximity to a POP, and bots, none of which are the product. The durability point is the object-storage snapshot, not the in-memory write: losing the in-memory store costs a rebuild, and losing the snapshot too costs a re-draw with a newly published seed.

**Availability view.** A bitmap over the four seat states — 2 bits × 60,000 = 14.6 KiB raw, ~3.7 KiB compressed — plus six 4-byte tier counters, regenerated once per second by a projector tailing the seat transition log and published at a version-stamped immutable URL with a 1 s TTL pointer object naming the current version. Ordering is borrowed entirely; it is never the source of truth. A fan acting on a stale bitmap loses the race at the conditional UPDATE and is told so, which is why 1 s of staleness — at most 300 transitions, 0.50% of the venue — is acceptable. Versioned immutable URLs make invalidation unnecessary: a new encoding is a new version prefix and a purge is never used.

**Entitlement.** One row per sold seat, minted inside the finalization transaction, with delivery to email or wallet a downstream asynchronous concern. Identity is a 128-bit unguessable random token, deliberately not time-sortable — this is the one place where the monotonic-identity convention is wrong, so the system runs two identity schemes on purpose.

Five consequences worth stating plainly:

- Consistency is chosen per invariant, not per system: **CP** for seats, holds, orders, payments, and the ledger — under partition the purchase path refuses work; **AP** for browse, availability, and the queue — under partition they serve stale, bounded at 1 s for the bitmap and 30 s for the drain front.
- Exactly-once is not on offer anywhere. Every effect is at-least-once delivery plus an idempotent apply whose dedup record is committed **in the same transaction as the effect**: client idempotency keys for holds and orders, an attempt-invariant hash for the provider, a unique `(provider, provider_event_id)` for webhooks, an `outbox_id` for the broker.
- The authoritative/derived split is the spine. Authoritative: the core database and the object-storage draw seed. Derived and rebuildable: the queue store, the allocator's per-tier candidate queues, the availability bitmap, the read replicas, and the log broker. Nothing derived may be believed by the purchase path.
- Two identity schemes on purpose. Orders and holds use time-sortable ids because operations wants them ordered; entitlements use 128 bits of randomness because a sortable capability is an enumeration attack.
- Compatibility is directional and stated per surface. Public HTTP API: **both** directions, because shipped browser and app clients cannot be rolled back. Tables: **backward**, since replicas lag the primary and effectively deploy first. Outbox topic: **forward**, writers first. Availability bitmap: none needed, because the version is in the URL path. Signed tokens: **both**, with a version claim and dual-key verification during rotation. Field removal is two releases and the tag stays reserved forever; checks run in CI, not a runbook.

## Database schemas

### Seat — core database · authoritative inventory, the invariant carrier

- `event_id: ID` — partition key, and primary key part 1; references `Event.id`
- `seat_id: ID (section/row/number)` — primary key part 2
- `tier_id: ID` — references `Tier.id`
- `state: BLOCKED | AVAILABLE | HELD | SOLD`
- `hold_id: ID, nullable` — conditional-update guard; references `Hold.hold_id`
- `order_id: ID, nullable` — references `Order.order_id`
- `state_version: bigint` — monotonic cursor
- `updated_at: timestamp`
- **Indexes:** `(event_id, seat_id)` primary, so every write targets exactly one row · `(event_id, tier_id, state)` partial on AVAILABLE for best-available dequeue and the per-tier budget floor · `(event_id, hold_id)` where not null for batched reaping · `(event_id, state_version)` as the projector's tail cursor
- **Notes:** 60,000 rows at ~60 B plus indexes = 3.6 MB. This table *is* the count — the no-overbooking invariant has no separate counter that could drift. Every write is a conditional `UPDATE ... WHERE state = $expected`; SELECT-then-UPDATE is forbidden because it is exactly the double-sale generator. `state_version` is the version that appears in the bitmap's immutable URL. Never deleted; 7-year retention.

### Hold — core database · authoritative reservation

- `hold_id: UUIDv7 (time-sortable, allocator-minted)` — primary key
- `event_id: ID` — references `Seat.event_id`
- `account_id: ID` — references `Account.id`
- `seat_ids: ID[]`
- `idempotency_key: ID (client-supplied)` — dedup key
- `state: ACTIVE | CONVERTING | RELEASED | EXPIRED`
- `created_at: timestamp`, `expires_at: timestamp` — reaper scan key
- `payment_locked_until: timestamp, nullable`
- **Indexes:** `(event_id, expires_at)` partial on ACTIVE with no payment lock — the reaper's bounded batch scan · `(event_id, idempotency_key)` unique, so a double-clicked Buy button produces one hold · `(account_id, event_id)` for the cross-tier limit aggregate
- **Notes:** expiry is a reaper query, never a cache TTL — a TTL in a separate store expiring a hold whose seats live here is the dual-write problem with a P0 attached. `payment_locked_until` reserves the 68 s window; the reaper may not touch a locked hold even past `expires_at`, and the lock is durable so it survives a failover. RELEASED and EXPIRED rows are dispute evidence for 30 days.

### Order — core database · authoritative purchase state

- `order_id: UUIDv7` — primary key
- `idempotency_key: ID (client-generated, stable across retries)` — dedup key
- `account_id: ID` → `Account.id` · `event_id: ID` → `Seat.event_id` · `hold_id: ID` → `Hold.hold_id`
- `state: DRAFT | AUTHORIZING | AUTHORIZED | ASSIGNING | ASSIGNED | CAPTURING | COMPLETED | FAILED | VOIDED | UNKNOWN`
- `state_rank: integer` — monotonic guard; a CHECK forbids any decrease
- `seat_count: integer` · `total_amount: minor units` · `currency: ISO 4217` · `created_at`, `updated_at`
- **Indexes:** `(idempotency_key)` unique — the dedup record is committed in the same transaction as the effect · `(state_rank, updated_at)` partial on non-terminal states, the reconciler's sweep of orders stuck longer than the 68 s payment window · `(account_id, event_id)` for the per-account limit evaluated inside the finalization transaction
- **Notes:** sits beside an append-only `order_event` table written in the same transaction. The per-account limit lives here as a database constraint rather than in a counter cache: a limiter that can be lost cannot enforce an invariant. Orders retained 7 years; the idempotency record 90 days.

### Payment — core database · authoritative money state

- `payment_id: UUIDv7` — primary key
- `order_id: ID` — unique, one payment per order; references `Order.order_id`
- `provider_idempotency_key: sha256(order_id, amount, currency, payment_method_token)` — attempt-invariant external key
- `provider_authorization_id: ID, nullable`
- `state: INITIATED | AUTHORIZED | UNKNOWN | CAPTURED | VOIDED | FAILED`
- `state_rank: numeric (0, 1, 1.5, 2, 3)` — monotonic guard
- `amount`, `currency`, `payment_method_token` (a provider token, never a PAN), `unknown_since: timestamp, nullable`
- **Indexes:** `(order_id)` unique · `(provider_idempotency_key)` unique, so a retry after a timeout addresses the same authorization instead of creating a second one · `(state, unknown_since)` partial on UNKNOWN — the reconciler's work queue, alarmed above 50 open · `(state, updated_at)` partial on CAPTURED for the orphan-capture sweep
- **Notes:** a webhook may only advance state, so a CAPTURED arriving before its AUTHORIZED applies and the late AUTHORIZED matches zero rows. The receiver therefore requires no ordering guarantee from the provider, which is correct, because there is not one. `UNKNOWN` is terminal-until-resolved with a named owner and a 5-minute SLA, not a retry. `provider_authorization_id` is the external effect's receipt and is written in the same transaction that records step completion, so a retry finds the receipt instead of repeating the call.

### PaymentEvent — core database · authoritative append-only financial record

- `payment_event_id: UUIDv7` — primary key
- `provider: text` — unique with `provider_event_id` · `provider_event_id: ID` — dedup key
- `payment_id: ID` — references `Payment.payment_id`
- `event_type: authorized | captured | voided | failed`
- `raw_payload: JSON, card fields redacted at write` · `signature_verified: boolean`
- `provider_created_at (provider clock)` · `received_at (our clock)`
- **Indexes:** `(provider, provider_event_id)` unique — a duplicate insert conflicts and the receiver acknowledges 200 immediately · `(payment_id, provider_created_at)` for the ordered evidence trail · `(received_at)` for the receiver's own lag and burst monitoring against 84,783 deliveries per on-sale
- **Notes:** written by verify signature → store raw → acknowledge, in under 1 s; processing happens asynchronously off a queue, because a slow acknowledgement makes the provider's retry schedule amplify the delivery count. Out-of-order arrival is expected and safe: this table records what arrived, and `Payment.state_rank` decides what it means. Retained 7 years and exempt from erasure. The provider is treated as an untrusted parser — the signature is verified before the payload is parsed.

### LedgerEntry — core database · authoritative append-only double-entry ledger

- `order_id: ID` — primary key part 1; references `Order.order_id`
- `leg: debit | credit` — primary key part 2 · `sequence: integer` — primary key part 3
- `event_id: ID` → `Seat.event_id` · `account_code` · `amount: minor units` · `currency: ISO 4217`
- `reversal_of: sequence, nullable` · `created_at: timestamp`
- **Indexes:** `(order_id, leg, sequence)` primary and immutable once written · `(event_id, created_at)` for the nightly audit that `sum(credits) = count(SOLD) × price` · `(reversal_of)` so corrections are traceable
- **Notes:** written in the same transaction that captures — money and its record are never two writes. Never updated and never deleted; a correction is a reversal entry. The payment provider's dashboard cannot answer whether every captured dollar has a seat behind it — only this table joined to `Seat` can, which is why the ledger is earned by the P0 invariant rather than by transaction volume. A failed nightly balance blocks settlement rather than raising a ticket nobody reads.

### QueueAdmission — queue store over an object-storage snapshot · derived and rebuildable, never authoritative

- `event_id: ID` — sorted-set key
- `account_id: ID` — member, one position per account; references `Account.id`
- `position: integer` — score, assigned once, from one seed, by one process
- `seed_id: ID` — references the published draw seed in object storage
- `admission_token: signed (event_id, account_id, position, expiry, v)` · `outcome: QUEUED | NOT_SELECTED`
- **Indexes:** score order for the `now_serving` range and the shared drain-front publish · `(event_id, account_id)` so refreshing the page does not buy a second entry · `(event_id, seed_id)` in the snapshot, the ordered position list that makes the draw re-derivable
- **Notes:** 2,000,000 members at ~100 B is 200 MB — one instance holds it, but never one instance: append-only file every second plus a replica. Rebuilt from the seed and the ordered snapshot; losing both costs a re-draw with a newly published seed, a product and PR event with zero financial exposure. No money and no seat depends on this store. Deleted 7 days after the event; the seed and ordered list retained 1 year.

## System interfaces

### Join the draw

- **Style / transport:** REST command resource · `POST /v1/events/{eventId}/queue {accountId, deviceAttestation}`
- **Trust boundary:** untrusted browser or app → edge worker → waiting-room service; the position and its expiry are server-assigned and no rule keys on a device clock
- **Deadline / retry:** 2 s to return a position and a signed token · retry 429 and 5xx with the same account; the position is unchanged because it derives from the persisted seed
- **Backpressure:** 429 with `Retry-After`, cacheable at the edge; client retries capped at 20% of active with a floor of 3, honoured with jitter
- **Consistency / idempotency:** one position per account, assigned once from one published seed · `(eventId, accountId)`
- **Compatibility:** additive fields only within v1; ignore unknown fields
- **Failure result:** `QUEUED` with a position; `NOT_SELECTED` as a signed terminal payload rendered client-side with no further request ever; `RATE_LIMITED`; `UNKNOWN` on timeout is resolved by resubmitting the same account, which is idempotent

### Read the drain front

- **Style / transport:** cacheable REST read · `GET /e/{eventId}/front`
- **Trust boundary:** public, unauthenticated, identical for every viewer — the personalisation happens on the device
- **Deadline / retry:** 300 ms at the edge; the object carries `server_time` so a client can render a countdown without being trusted for one · safe to retry at any time, polled on a jittered interval
- **Backpressure:** 1 s TTL with request collapsing at each POP and a tiered parent cache; origin fill is 50 req/s at 50 POPs, and a client whose front object is older than 30 s degrades to a "checking" state rather than a wrong estimate
- **Consistency / idempotency:** eventual, bounded at 1 s of staleness · pure read, with the cache key an explicit allowlist of `(eventId)` and nothing else, so no request attribute can leak one fan's response to another
- **Compatibility:** additive fields only; `drain_rate` is published as a trailing 60 s measured average, never a forecast
- **Failure result:** `200` with `{now_serving, drain_rate, seat_version, server_time}`; a stale object is served rather than an error, because this flow fails open while the purchase path behind it fails closed

### Hold seats

- **Style / transport:** REST command resource · `POST /v1/events/{eventId}/holds {admissionToken, tierId, quantity, idempotencyKey}`
- **Trust boundary:** signed admission token verified at the edge with zero network calls → admission controller → allocator; the per-account limit is a database constraint, never a client check
- **Deadline / retry:** 3 s to a durable hold, of which the allocator's transaction is budgeted at 500 ms · retry 429 and 5xx with the same idempotency key, which returns the same hold rather than consuming a second one out of a fixed 300/s budget
- **Backpressure:** the seat-token lease pool is denominated in AVAILABLE seats, not requests, and refills each second from the allocator's residual budget; above it, 429 with `Retry-After`
- **Consistency / idempotency:** linearizable within the event — the affected-row count must equal the requested quantity or the whole transaction rolls back · client idempotency key, committed in the same transaction as the hold
- **Compatibility:** additive fields only within v1; ignore unknown fields
- **Failure result:** `HELD` with a hold id, the seat ids, and `expires_at`; `SOLD_OUT` or `NO_LEASE` before anything is written; `UNKNOWN` on timeout after the commit may have occurred — resubmit the same idempotency key, which returns the existing hold

### Submit checkout

- **Style / transport:** REST command resource · `POST /v1/orders {holdId, paymentMethodToken, idempotencyKey}`
- **Trust boundary:** authenticated account → payment adapter → external payment provider; the card number never crosses into this system, only a provider token
- **Deadline / retry:** 68 s end to end, which is why a checkout is refused outright when the hold has less than 68 s left; the provider call itself is bounded at 12 s · retry the same idempotency key freely, but a provider timeout is never retried as an authorization — it becomes `UNKNOWN` and the reconciler queries it
- **Backpressure:** the adapter's 570-deep connection pool sheds at the adapter, never at the database, so a slow provider queues as unadmitted fans rather than unbounded in-flight orders
- **Consistency / idempotency:** one transaction covers seats, order, entitlements, both ledger legs, and the outbox row · client idempotency key for the order, an attempt-invariant hash for the provider
- **Compatibility:** additive fields only within v1; ignore unknown fields
- **Failure result:** `COMPLETED` with entitlements; `DECLINED` or `FAILED` with the authorization voided and seats released; `UNKNOWN` when the provider call times out — the seats stay HELD under a durable payment lock and the reconciler resolves it within 5 minutes

### Receive payment webhook

- **Style / transport:** inbound event callback · `POST /v1/webhooks/payments` (provider-signed)
- **Trust boundary:** untrusted third party → webhook receiver; the signature is verified before the payload is parsed, and card fields are redacted at write
- **Deadline / retry:** verify, store raw, and acknowledge in under 1 s — a slower acknowledgement makes the provider's retry schedule amplify 84,783 deliveries per on-sale · the provider owns the retry; this receiver never retries inbound delivery and never asks for ordering
- **Backpressure:** processing happens asynchronously off a queue depth-capped at 10,000 with age-based shedding; the receiver stays stateless and always acknowledges fast
- **Consistency / idempotency:** state advances by rank only — a capture arriving before its authorization applies, and the late authorization is a no-op · unique `(provider, provider_event_id)`
- **Compatibility:** forward-compatible — unknown event types and unknown fields are stored raw and ignored by the processor
- **Failure result:** `200` on accept and on duplicate; `401` on a failed signature; `UNKNOWN` never appears here, because an unrecognised event is stored rather than judged

## Estimates

Given as measurement: 60,000 seats across 6 tiers · 2,000,000 arrivals in 60 s · 50,000 read QPS · 300 transitions/s measured · 600 s hold · auth p50 2 s / p99 8 s · webhook p99 45 s, duplicated and out of order · 40,000,000 tickets/yr.

Assumed, each falsifiable: mean order 2.0 seats · 70% hold-to-purchase conversion, modelled 50–90% · 90 s hold-to-submit for a converting fan · abandoners release at the 600 s expiry (45 s explicit release modelled separately) · 8% card declines · tier sizes 5/10/20/15/30/20% · 8 tickets per account per event · $80 face at a 15% take · 50 CDN POPs and a 4× brotli ratio · single region, multi-AZ, one team.

| Metric | Value | Derivation |
|---|---|---|
| arrival rate at the door | 33,333 fans/s for 60 s | 2,000,000 ÷ 60 s — one-shot, not sustained |
| seat writer | 300 transitions/s | measured ceiling; every path AVAILABLE→HELD→SOLD costs exactly 2 transitions, every abandoned attempt costs 2 and yields nothing |
| platform steady state | 2.54 transitions/s | 40,000,000 × 2 ÷ 31,536,000 — six times below the ~17 write-TPS gate at which one ACID database has capacity to spare |
| arrivals : writer | 111:1 | 33,333 ÷ 300 |
| peak : platform average (write) | 118:1 | 300 ÷ 2.54 — an elasticity requirement, not a scalability one |
| sold-out-venue-equivalents | 667/yr ≈ 1.8/day | 40,000,000 ÷ 60,000 — the burst machinery runs twice a day and idles the rest of the time |
| absolute sell-out floor | 400 s = 6 min 40 s | 60,000 × 2 ÷ 300 — no waiting room, CDN, or front-end work beats this, and it should be on the product page |
| budget floor at 70% conversion | 571 s | 60,000 ÷ 0.70 = 85,714 attempts × 2 ÷ 300; 444 s at 90%, 800 s at 50% |
| conversion as the only budget lever | 70% → 90% removes 22.2% of all writer work | 1 − (2/0.9) ÷ (2/0.7); 127 s off the floor with zero infrastructure change |
| steady-state budget split | 150 new holds/s, 150 resolutions/s | 300 ÷ 2 — every hold has one resolution, so in equilibrium the budget halves; at 70% that is 105 sales/s and 45 re-availabilities/s |
| order admission rate | 75 orders/s | 150 ÷ 2.0 seats — the number the entire front end exists to produce |
| door reduction | 444:1 | 33,333 ÷ 75, performed at the edge with no state and no network call |
| reaping share of the budget | 5% / 15% / 25% at 90/70/50% conversion | (60,000/c − 60,000) ÷ (60,000/c × 2) — at 50% conversion half of every transition the writer performs is wasted |
| peak concurrent held seats | 31,860 (53% of the venue) at 70% | greedy residual admission simulated at 1 s steps; Little's law alone (150/s × 243 s) predicts 36,450 and over-commits, because the AVAILABLE pool is itself the token bucket |
| sell-out tail | t50 302 s, t95 1,482 s, t99 2,149 s at 70% | fluid simulation, priority finalize > reap > new-hold; the closed form n = ln(target)/ln(1−c) waves × 600 s + 90 s gives 2,385 s — two independent models within 10% |
| tail decomposition | 26.6% floor / 61.4% hold-expiry recycling / 12.1% writer scarcity | 571 s / 1,319 s / 259 s of the 2,149 s t99 — a 6× faster writer buys 230 s, an infinite one buys 259 s |
| explicit-release leverage | 60% adoption → t99 1,551 s; 90% → 1,090 s | abandoners releasing at 45 s instead of 600 s — 28% and 49% improvements with zero infrastructure change |
| payment window | 68 s, reserving 11.3% of every hold | auth p99 8 s + webhook p99 45 s + 15 s margin; 68 ÷ 600, leaving a 532 s usable select window |
| authorization rate | 57 auth/s sustained | 105 seats/s ÷ 2.0 = 52.5 orders/s ÷ 0.92 for an 8% decline rate |
| authorization concurrency | 457 in flight → pool sized 570 | 57.1/s × 8 s p99, the pathological all-at-p99 case; the mean-latency interpolation is deliberately not load-bearing |
| authorizations per on-sale | 32,609 | 30,000 orders ÷ 0.92 — the single external quota this design depends on |
| webhook deliveries | 84,783 per on-sale; 39/s mean, 118/s at 3× | 32,609 × 2 events × 1.3 duplicate factor over a ~2,149 s sell-out |
| seat bitmap | 14.6 KiB raw, ~3.7 KiB on the wire | 2 bits × 60,000 = 15,000 B; brotli 4× on clustered runs. Per-tier counters are 6 × 4 B = 24 B, which is what "is it sold out?" actually needs |
| read bandwidth from origin | 6.0 Gbps raw / 1.5 Gbps compressed | 50,000 × 15,000 B × 8 — either figure forecloses origin serving |
| CDN economics | origin fill 50 req/s, 99.90% hit; 5,000 QPS at a 90% hit | 50 POPs × 1 req/s at a 1 s TTL with request collapsing; a cold cache is 100× the warm fill, and origin is sized from the miss rate at its worst |
| read-load decomposition | 40,000 queue front + 2,500 availability (CDN) + 7,500 personalised (origin) | 50,000 QPS split across three populations; 7,500 ÷ 3 replicas ≈ 2,500 each, and the primary serves zero reads |
| queue-poll trap | 200,000–400,000 QPS — 4× to 8× the entire read budget | 2,000,000 ÷ a 10 s or 5 s interval; the interval that exactly consumes all 50,000 QPS is 40 s, unusable as UX |
| fans who can never be served | 1,970,000 (98.50%); 1,880,000 (94.0%) told at t≈60 s | 60,000 ÷ 2 = 30,000 winners; the admission ceiling is 60,000 ÷ (2 × worst-case 25% conversion) = 120,000 orders |
| queue store footprint | 200 MB | 2,000,000 × ~100 B in one sorted set |
| storage | 134.4 GB/yr; 0.94 TB single-copy at 7 years | 3,360 B/ticket (ticket 400 + order 600 + 3 transitions 360 + 4 payment events 1,200 + 2 ledger legs 800) × 40,000,000 |
| serial availability of the purchase flow | 99.740% = 1,365 min/yr | 0.9999 × 0.9995 × 0.9990 × 0.9990 — nines in sequence multiply |
| failover cost inside the on-sale window | 30 s = 9,000 transitions deferred; 60 s = 2.8% of the window | seconds × 300/s, and 60 ÷ 2,149 s. Sales are deferred, not lost, because demand exceeds supply 33:1 |
| revenue and P0 exposure | $720,000 per sold-out on-sale; ~33 charged-without-seat candidates | 60,000 × $80 × 15%; 32,609 auths × 0.1%, at 1.8 on-sales/day |
| cross-region replication lag | n/a | one venue in one timezone; the sanity pass forecloses cross-region consensus on a CP write path |
| cache footprint (working set) | n/a | the entire authoritative dataset for one event is 60,000 rows at ~60 B |
| fan-out per write | n/a | one seat transition affects exactly one shared view read by everybody; per-reader materialisation would be 2,000,000 copies of an identical 14.6 KiB object |

## Candidates

**A — Single ACID core behind an edge admission gate** `[service-based]`. Every invariant — double-sale, overbooking, money-to-seat, and the cross-tier account limit — lives inside one transactional authority reached through one serialising allocator, and the 111:1 burst is absorbed entirely at the edge by a signed token rather than by anything that can write. A fan makes **one** request for the whole wait, receives a seeded draw position and a signed token, and either renders `NOT_SELECTED` locally forever or polls **one shared cached object** and computes their own estimate. The allocator runs strict priority `finalize > reap > new-hold` inside 300 transitions/s with per-tier budget floors, and finalization is `authorize → assign-in-one-transaction → capture`. Pros: every invariant is a local constraint; the burst never reaches anything that can write; one team can operate it; the AVAILABLE pool is its own token bucket so occupancy self-limits at 53% with no guard to tune. Cons: one primary on the critical path, and a 30 s failover straddles the 68 s payment window of every in-flight checkout; the write path has nothing to scale; the tail is only movable by product levers; the allocator needs fenced leader election; seat *choice* is degraded to best-available during the peak.

**B — Per-tier partitioned allocator with in-memory seat authority** `[space-based]`. Seat authority is split six ways by price tier and moved into memory behind a replicated log, so the invariants that span tiers — the per-account limit and a multi-tier basket — stop being local constraints and become an escrow protocol across partitions. It adds six tier authorities, a replicated seat log, a basket coordinator, and an account-limit service. Pros: the seat write path is genuinely elastic; reads of seat state never touch a database; each tier's failure is isolated; the replicated log is a replayable record of every transition. Cons: two invariants cross partition boundaries and become a saga with no isolation; the 6× throughput claim is unmeasured; tier skew means five authorities idle while one saturates; the benefit is 10.7% of the tail; it creates a hold-stampede lockup A does not have and must then add back the guard simulation proved harmful; recovery time becomes the availability budget and must be published; six stateful authorities plus an escrow protocol is a different operational organisation from the one that exists.

**C — Deferred allocation with an auditable draw** `[pipeline]`. Demand capture is decoupled from allocation entirely: during the 60 s rush the system accepts **intents** as append-only writes with no seat state touched and no payment call made — a pure insert at 33,333/s with zero contention and no relationship to the 300/s writer. Then the window closes and a batch draws from a published seed, allocates at the 400 s absolute floor, authorizes winners only at a rate the design chooses, and answers every fan. Pros: the charged-without-a-seat window nearly disappears because the seat is committed before an authorization is attempted; no hold exists, so the 61.4% of the tail that hold-expiry owns simply is not there; the burst is an uncontended append; a seeded batch is replayable offline; the entire live read path collapses. Cons: time-to-answer is 10–30 minutes for the last fan; it deletes the live seat map, seat choice, and instant confirmation, which some artists and promoters contractually require; 2,000,000 fans must store a payment token before knowing whether they won; gaming shifts to bulk account creation, exporting a hard problem to an out-of-scope system; a declined winner's seat must be re-allocated, so the batch is a loop that converges in 2 rounds rather than one pass.

## Comparison and recommendation

**Recommended: A — Single ACID core behind an edge admission gate**, with two mechanisms adopted from C: the seeded, published, auditable draw for admission ordering, and a documented pre-built switch to C for any event whose registered demand exceeds a stated threshold. B is rejected outright.

No rating appears in this chain. Every link is an envelope number, an invariant, or a named failure mode.

1. **The platform is small.** 40,000,000 tickets/yr is 2.54 seat-state transitions/s, six times below the ~17 write-TPS threshold at which one ACID database still has capacity to spare. Rate contributes no argument for distributing anything.
2. **So the only thing that could justify distribution is an invariant spanning owners that cannot share a transaction — and there is none.** No-double-sale is per seat, no-overbooking is a count over one table, money-to-seat is one transaction, and the per-account limit spans all six tiers, which makes it an argument *against* splitting by tier rather than for it.
3. **The real problem is a burst, not a volume.** Arrivals exceed writer capacity 111:1 and the peak-to-average write ratio is 118:1. That is elasticity, and it is bought at the door: 33,333 arrivals/s become 75 admissions/s, a 444:1 reduction performed by a signed-token check at the edge with zero network calls.
4. **B's premise fails on measurement.** 300/s is a *measurement* of the writer; six partitions delivering 1,800/s is an unmeasured 6× claim. Even granting it in full, t99 at 70% conversion moves only from 2,149 s to 1,919 s, because 61.4% of the tail is hold-expiry recycling and only 12.1% is writer scarcity. B spends its entire complexity budget on 12% of the problem.
5. **And B creates a failure mode A does not have.** At 300/s greedy residual admission peaks at 31,860 held seats and self-regulates; at 1,800/s it reaches all 60,000 within ~33 s, so the map reads sold out for ten minutes with nothing sold. B must then add back the held-inventory guard that simulation showed made t95 *worse* — 1,482 s → 2,099 s at a 60% guard, 3,310 s at 35%.
6. **The P0 invariant is satisfied structurally, and only inside one transactional authority.** `authorize → assign-in-one-ACID-transaction → capture` means money moves after the seat is committed, so the charged-without-a-seat window is the gap between commit and capture, which the reconciler owns and bounds at 5 minutes. B places seats in six authorities and money outside all of them, turning finalization into a saga with a non-compensable money step and no isolation.
7. **The read load is a cache problem, not a serving problem, and no candidate differs.** 50,000 QPS at 14.6 KiB is 6.0 Gbps and forecloses origin serving, but 42,500 of it is identical for every viewer, so a 1 s TTL puts origin fill at 50 req/s. The only personalised read is 7,500 QPS across three replicas with the primary serving zero.
8. **C is correct and it is not an agent's decision to take.** It satisfies the P0 invariant more strongly than A and reaches the 400 s absolute floor, but it deletes the live seat map, seat choice, and instant confirmation — a product decision with contractual consequences for artists and promoters. It is recorded as a documented, pre-built switch: the same allocator driven from a batch source, triggered when registered demand exceeds 20× inventory. This event's 33:1 crosses that trigger, and escalating it is the single highest-value action this design surfaces.
9. **What breaks first in A, named up front:** the primary failover, because a 30 s failover defers 9,000 transitions and straddles the 68 s payment window of every in-flight checkout — precisely the orders with money in the air. The durable payment lock and the reconciler bound it; they do not eliminate it.
10. **The measurement that would overturn this:** profile *why* the seat writer is 300/s. If it is lock contention on hot seat rows, server-assigned best-available may raise it for free and the ceiling was never a ceiling. If it is CPU or fsync, it is real. The design is sized at 300/s so that it is correct either way, which is what makes the profile a day-one task rather than a prerequisite.

See `design.json` for the full ratings matrix and per-candidate flows. Every candidate carries a 1-star cell except A — B's is simplicity and C's is performance — and A's absence of one is a flag on the rating rather than a compliment to the design, which is why A's honest floor is named explicitly: its fault tolerance is a 3, and its dependence on a single primary during a 68 s payment window is the thing most likely to produce the P0 the whole design exists to prevent.

Every authoritative database, log, and object store records its acknowledgement point, independent failure domain, RPO, RTO, and recovery procedure. Every derived cache, replica, projection, and broker records its reconstruction source and cursor. Every edge records a deadline or maximum age, exactly one retry owner, and a finite concurrency, retention, in-flight, or backlog bound; these contracts are visible in the component inspector.

## Critical deep dives

1. **Allocate a 300/s budget that cannot be increased.** Three classes of work compete for one fixed budget, and at 50% conversion 49.7% of all writer work is wasted. Strict priority `finalize > reap > new-hold` with new holds taking the residual and no fixed shares; **no inventory guard**, because the AVAILABLE pool is itself the token bucket and occupancy self-limits at 46/53/67/80% for 90/70/50/30% conversion — an explicit guard at 60% or 35% moved t95 from 1,482 s to 2,099 s and 3,310 s, so the guard was deleted because the numbers said so. Server-assigned best-available within tier during the peak gives exactly one transition per seat and zero aborted conditional updates. Offer exactly the requested quantity: offering 4 for an order of 2 at 75 orders/s wastes 150 transitions/s, half the entire budget. Per-tier floors of `300 × share × 0.5` redistributed each second, because the 5% tier would otherwise exhaust in 20 s while five tiers starve. Artist releases are scheduled, since 2,000 seats is 6.7 s of the whole budget. Rejected: fixed shares, an inventory guard, optimistic per-seat CAS with fan-chosen seats, and raising the writer. **Failure mode:** reaper starvation under a finalization wave — expired holds accumulate, AVAILABLE goes to zero, and admissions stop while thousands of seats are notionally free. Detected by `reap_backlog_seconds` paged at 30 s; mitigated by promoting the reaper above finalization at 60 s, an explicit alarmed priority inversion rather than an emergent one. **The conclusion about the tail:** the correct response to a 2,149 s t99 is not a faster writer — it is raising conversion (−22.2% of all work) and shortening abandonment latency (t99 1,551 s at 60% explicit release, 1,090 s at 90%). Both are product changes, and they beat six partitions by a factor of three.

2. **Make charged-without-a-seat structurally impossible.** Five mechanisms, each closing one named hole. (a) `authorize → assign in one transaction → capture`, never capture first; a failed assignment voids the authorization so no charge ever settles. The accepted exposure is stated: a voided authorization can show as a pending charge for a few business days, which is a support-messaging problem, not a P0 — the difference between "we owe you a refund" and "your bank will release the hold". (b) A 68 s payment window reserved inside every hold, with checkout refused below it and a **durable** payment lock the reaper may not touch; without it, the exposed race is every checkout begun in the last 53 s of a hold. (c) `UNKNOWN` as a third terminal-until-resolved state with the reconciler as its named owner and a 5-minute SLA — an ambiguous authorization is *queried*, never repeated, which is safe because the provider key is attempt-invariant; past the SLA the order is force-voided with the provider reference attached. (d) A webhook receiver that verifies, stores raw, and acknowledges in under 1 s, killing duplicates with a unique index and out-of-order arrival with the monotonic rank rule — it requires no ordering guarantee from the provider at all, which is correct, because there is not one. (e) Two continuous sweeps in both directions plus a nightly ledger audit that blocks settlement on a mismatch. Rejected: capture-first, a distributed transaction spanning the provider, retrying an ambiguous authorization, trusting webhook ordering, and selling on provider unavailability — the last is refused because demand exceeds supply 33:1 so a refused sale is immediately re-sold, reasoning that would be *wrong* for a slow-selling event and is therefore a configuration value, not a code path. **Failure mode:** primary failover inside the 68 s payment window, bounded by two published numbers — no seat in an in-flight payment is resold for at least 68 s after a failover, and no authorization goes unresolved for more than 5 minutes.

3. **Turn 33,333 arrivals/s into 75 admissions/s without a per-fan read.** One request per fan for the entire wait, returning a position, a seed id, and a signed token. A seeded published draw rather than FIFO by arrival millisecond, which rewards fast networks, proximity to a POP, and bots. Reject 94% in the first minute with a signed terminal payload rendered client-side and deliberately **not** retryable, because a retryable rejection to 1.88M clients is an outage — and deferring that answer to sell-out would convert it into a 1,880,000-request herd at the moment the system is most loaded. The remaining ~120,000 poll **one shared cached object** carrying `{now_serving, drain_rate, seat_version, server_time}` at a 1 s TTL and compute their own estimate locally: ~40,000 QPS served entirely by the CDN at 50 req/s origin fill. Admission is decided at the edge by a local signature check with zero network calls. The admission unit is a seat-token lease denominated in AVAILABLE inventory — the one quota no gateway or mesh can express, and the only custom component in the admission path; everything else is bought configuration. Rejected: a per-fan position endpoint (4–8× the read budget), SSE or WebSockets to 2M fans (20 GB of connection state, ~20 gateway hosts, and a reconnect-storm surface at the worst possible moment), a 40 s poll interval, and FIFO by arrival. **Failure modes:** a `drain_rate` published too high, mitigated by publishing a trailing 60 s measured average and rendering a range rather than a point; and, stated deliberately, **recovery is not automatic** — after an incident `now_serving` does not accelerate to catch up, because it is bounded by the residual of a fixed 300/s budget, so the system returns to health by *not* accelerating and the queue simply takes longer.

## Operations and rollout

- Watch `reap_backlog_seconds` (paged at 30 s, reaper promoted above finalization at 60 s), open `UNKNOWN` count (alarmed above 50), outbox depth (alarmed at 10,000), replica lag (alarmed above 1 s), CDN hit ratio against the 90% provisioning case rather than the 99.90% steady state, webhook acknowledgement p99 against the 1 s deadline, and the ratio of explicit releases to expiries — the last is the tail's single largest lever.
- Shed first: browse and seat-map refresh. Shed last: finalization of an in-flight payment. Money, auth, and abuse paths **fail closed**; browse, availability, and the drain front **fail open**.
- Rehearse a primary failover inside a synthetic 68 s payment window before the first on-sale. On allocator restart, every order in a non-terminal state older than 68 s is enqueued to the reconciler automatically.
- The bitmap is versioned in its URL, so a purge is never used; a new encoding is a new version prefix. Provision origin for the 90% hit case (5,000 QPS), never the warm fill.
- Stage the on-sale itself: publish the draw seed before the window opens, run the draw, snapshot the seed and ordered position list to object storage before declaring the draw closed, then open admission. The draw is not closed until the snapshot lands.
- Erasure is explicit: pseudonymise `account_id` across `order`, `hold`, and the queue store while leaving `ledger_entry` and `payment_event` intact under the financial-record exemption, then delete the mapping table.

## Risks and what breaks first

- 57 auth/s sustained and a 570-deep concurrency ceiling are **contractual terms** with the payment provider, not engineering tasks — the single external quota the design depends on, and it cannot launch unconfirmed (before launch).
- Nobody has profiled *why* the seat writer is 300/s. Lock contention on hot seat rows may be free to fix; CPU or fsync is permanent (day one).
- This event's registered demand is 33:1 against inventory, crossing the 20:1 trigger for the deferred-draw switch — an unescalated trigger is the difference between a product decision and an incident (before this on-sale).
- The allocator is a single active instance per event; fenced leader election must be proven under a real partition, because a split-brain allocator that the database *does* stop still burns budget on aborted writes (at launch).
- Conversion is the highest-leverage input in the design and it is assumed at 70%. At 50% the writer wastes 49.7% of every transition and t99 reaches 3,881 s, so the first real on-sale is also the measurement that resizes the envelope (first live on-sale).
- Explicit release is a product change, not an infrastructure one, and it owns 28–49% of the tail. If the client work is deprioritised, the capacity argument silently reverts to the 2,149 s baseline (first product cycle).
- Losing both the queue store and its object-storage snapshot forces a public re-draw with a newly published seed — no money at risk, but a promoter-facing event (any on-sale).

## Measurements that could overturn the decision

- If the seat writer's 300/s turns out to be lock contention on hot seat rows, server-assigned best-available may raise it for free and the ceiling was never a ceiling — the budget arithmetic changes, though the invariant argument against B does not.
- If measured hold-to-purchase conversion lands near 50% rather than 70%, half of every transition is wasted and t99 reaches 3,881 s; the deferred-draw switch stops being an escalation and starts being the default for this venue.
- If six tier authorities are actually measured — against a shared WAL device, connection pool, and network — and deliver close to 1,800/s *and* the tail is shown to be writer-bound rather than hold-bound, B's premise is restored and it deserves a second look.
- If explicit-release adoption exceeds 60% in production, the tail falls to 1,551 s without any infrastructure change, which removes the strongest remaining argument for either alternative candidate.
- If a promoter contract drops the live-seat-map requirement for high-demand events, C is strictly better on the P0 invariant and reaches the 400 s floor, and the recommendation inverts.

## Next steps

1. Confirm 57 authorizations/s sustained and a 570-deep concurrency ceiling in writing with the payment provider.
2. Profile the seat writer to determine whether 300/s is lock contention, business-logic CPU, or fsync — the design is sized to be correct either way, so this is a day-one task and not a prerequisite.
3. Escalate the deferred-draw switch to the product owner: this event exceeds the 20×-inventory trigger, and the choice belongs to whoever owns the artist and promoter contracts.
4. Build the explicit release path first — an unload beacon, a visible Cancel control, and hold surrender when a fan starts a new selection — because it moves t99 from 2,149 s to 1,551 s at 60% adoption with no infrastructure change.
5. Instrument `reap_backlog_seconds` and the open-`UNKNOWN` count before the first on-sale; both are the paging signals for the two named failure modes.
6. Rehearse a primary failover inside a synthetic 68 s payment window and verify that the durable payment lock keeps every in-flight hold untouchable and that the reconciler resolves every ambiguous authorization within 5 minutes.

## Notes
