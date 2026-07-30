---
date: 2026-07-31
mode: greenfield
status: draft
---

# Design WhatsApp

## Context

A real-time messaging service: 1:1 and small-group text plus media, delivered in under half a second while both parties are online, queued reliably for 30 days when they are not, synchronised across a user's devices, with presence. Mobile networks are assumed unreliable. Constraints: mobile-first clients; messages deleted from servers after delivery; group size capped at 100 to bound fan-out.

## Requirements

| id | Functional requirement | Priority |
|---|---|---|
| fr-1 | 1:1 text messaging with sent/delivered/read status | core |
| fr-2 | Group chat up to 100 participants | core |
| fr-3 | Offline delivery queue, 30-day retention | core |
| fr-4 | Media attachments via direct-to-storage upload | core |
| fr-5 | Presence (online / last-seen) with heartbeats | core |
| fr-6 | Multi-device sync via per-device high-water mark | stretch |

| Axis | Target | Rationale |
|---|---|---|
| latency | p99 < 500 ms send-to-deliver (online) | user-stated |
| durability | no acknowledged loss on process, node, zone, or ordinary promotion; regional disaster RPO <5 min | delivery guarantee is the product, scoped by failure domain |
| scalability | 500M DAU, 50M concurrent connections | user-stated |
| availability | 99.99% message path | chat is the primary channel |
| consistency | per-conversation ordering; cross-conversation eventual | causality within a chat is what users notice |

Top three characteristics: **scalability**, **fault tolerance**, **performance** (user-stated) — 500M DAU stated, and an acknowledged message may never be lost.

Out of scope: voice/video calls · end-to-end encryption key management · stories/status feeds.

Accepted conflicts: exactly-once delivery requested → at-least-once transport + client-side dedup by message id.

## Core entities and invariants

- **Conversation** — ordering and partitioning boundary. Membership is checked before accepting a send; one logical order exists per conversation.
- **Message** — immutable user-authored event. A client message id is unique per sender device; acknowledgement happens only after durable acceptance.
- **Device inbox** — durable backlog and resume cursor. Cursors only move forward; reconnect cannot skip an accepted message.
- **Connection lease** — short-lived device-to-gateway mapping. Expired leases are never routed; at most one active lease exists per device session.

## Data and consistency model

**Conversation.** Not a stored aggregate — a partition key. Membership and group metadata are rows in the authoritative User/group DB; the conversation's content uses one durable acceptance partition in flight and a keyed row range in the message store at rest. `conversationId` is minted once, stays stable for the life of the chat, and is the partition key everywhere the conversation appears. Ordering authority is the candidate's acceptance partition: its committed sequence *is* the conversation's one logical order, and nothing outside it may assign sequence. Membership has a single writer, so concurrent edits serialize in the User/group DB and the send path rejects a non-member before anything is accepted; that commit is the durability point, and a conversation holds no other losable state. The record outlives its messages — retiring it deletes membership, never the partition, because dropping the partition would leave a late arrival with nothing to be ordered against.

**Message.** An immutable event: a record in the conversation's durable acceptance partition in flight, a row keyed `(conversationId, acceptedSequence)` in the wide-row store at rest. Media never travels inside it — the body carries a reference to an object in storage. Identity is a server-assigned `messageId`, while the sender's `clientMessageId`, scoped to the sending device, is the deduplication key that makes a retried send idempotent. The committed sequence in the acceptance partition is the ordering authority; wall clocks are not consulted and there is no global sequencer. The message itself needs no conflict resolution because it is append-only and never mutates — delivery state moves separately as a receipt resolved by max-state transition (sent < delivered < read), so a reordered or duplicated receipt cannot move it backwards. The acceptance-partition commit is the durability point *and* the sender's acknowledgement, leaving no acknowledged-loss window for process, node, zone, or ordinary promotion failures; regional disaster retains the explicit <5-minute RPO. Delivered messages are deleted from servers after delivery; undelivered ones are parked in the authoritative message store on a 30-day clock rather than held in the acceptance partition, since transient authority must transfer to the store before that partition's retention window closes.

**Device inbox.** A derived per-device backlog materialized from accepted messages plus authoritative resume progress in the message store; the backlog is rebuildable and never the authority for message content. Cursor identity is `(deviceId, conversationId)`, and each cursor is the highest `acceptedSequence` that device has acknowledged in that conversation — there is deliberately no cross-conversation cursor. Ordering is borrowed: the inbox imposes none of its own, draining each conversation's committed sequence in order and interleaving across conversations arbitrarily. Conflicts resolve by monotonic max — a cursor only moves forward, so a stale reconnect carrying a lower cursor is discarded rather than applied, at the cost of redelivery that client-side dedup already absorbs. Each per-conversation cursor advance must be durable before the matching backlog entry may be dropped; that write ordering is what makes a reconnect unable to skip an accepted message. An entry drops once every one of the user's device cursors has passed it, or at the 30-day ceiling, whichever comes first.

**Connection lease.** An expiring entry in the in-memory connection registry mapping a device to the gateway currently holding its socket — derived, roughly 5 GB fleet-wide, and deliberately never persisted. Identity is `deviceId` plus device session id, so exactly one lease is active per session and a reconnect supersedes rather than duplicates. The presence service is the authority, renewing leases from gateway heartbeats; recency is the order that matters, because the newest heartbeat is by definition the live connection. Last writer wins on that recency, an expired lease is treated as absent, and a routing miss is not an error — it falls through to the device inbox, which is the durable path. There is no durability point, by choice: losing the entire registry costs a wave of redelivery, not a lost message, which is exactly why presence is allowed to be fast and lossy. Leases expire on heartbeat timeout — 30-second heartbeat, 60-second reap — and a gateway drain expires its own explicitly instead of waiting.

Four consequences worth stating plainly:

- Ordering is per conversation, never global — cross-conversation order is not a product promise, and no candidate buys one.
- Every consumer on the delivery path is at-least-once, so every write is idempotent by `clientMessageId` within its conversation. Deduplication is the price paid for refusing to claim exactly-once delivery.
- The split between authoritative and derived is the spine: A's queue and B's log are transient authority until authoritative message-store commit and consumer acknowledgement; device inboxes and the connection registry remain rebuildable views.
- Rejected alternative C — Cell-based isolation: write-behind acknowledges from the in-memory grid before durable persistence, so an ordinary cell crash can lose acknowledged messages inside the zero-loss failure scope.

## Database schemas

### Message — wide-row message store · authoritative history

- `conversationId: ID` — partition key; references `Conversation.id`
- `acceptedSequence: integer` — sort key
- `messageId: ID` — unique identity
- `clientMessageId: ID` — deduplication key
- `senderId: ID` — references `User.id`
- `body: text | media reference`
- `createdAt: timestamp`
- **Indexes:** `(conversationId, acceptedSequence DESC)` for ordered conversation history; `messageId` for direct lookup
- **Note:** immutable after acceptance; delivery receipts are stored separately

### Conversation — user and group database · authoritative metadata

- `id: ID` — primary key
- `type: direct | group`
- `memberIds: ID[]` — references `User.id`
- `createdAt: timestamp`
- **Index:** `memberId` for conversations visible to a user
- **Note:** membership is checked before a message is accepted

### DeviceInbox — message store · derived and rebuildable

- `deviceId: ID` — partition key; references `Device.id`
- `conversationId: ID` — sort-key prefix
- `acceptedSequence: integer` — sort key
- `messageId: ID` — deduplication key; references `Message.messageId`
- `expiresAt: timestamp`
- **Index:** `(deviceId, conversationId, acceptedSequence)` for reconnect scans after each cursor
- **Note:** entries expire after delivery or the 30-day offline retention ceiling

### DeviceResumeCursor — message store · authoritative delivery progress

- `deviceId: ID` — partition key; references `Device.id`
- `conversationId: ID` — sort key; references `Conversation.id`
- `acceptedSequence: integer` — monotonic cursor
- `updatedAt: timestamp`
- **Index:** `(deviceId, conversationId)` for one resume position per conversation
- **Note:** advance by max only; commit before deleting matching inbox entries

## System interfaces

### Connect or resume

- **Style / transport:** bidirectional session command · `WSS CONNECT {deviceId, perConversationCursors}`
- **Trust boundary:** authenticated device → connection gateway
- **Deadline / retry:** 5 s to authenticate and return accepted per-conversation cursors · reconnect with the same device session id and last accepted cursors
- **Backpressure:** gateway closes overloaded sessions with 1013; device reconnects with exponential backoff and jitter
- **Consistency / idempotency:** session read-your-writes · device session id
- **Compatibility:** additive command fields within protocol v1; ignore unknown fields
- **Failure result:** `CONNECTED` with accepted cursors; `REJECTED` with auth or cursor error; `UNKNOWN` on timeout after session installation—reconnect with the same session id

### Send message

- **Style / transport:** bidirectional command · `WSS SEND {conversationId, clientMessageId, body}`
- **Trust boundary:** sender device → connection gateway
- **Deadline / retry:** 3 s to durable acceptance · retry with the same `clientMessageId` after reconnect
- **Backpressure:** server overload closes with 1013; client reconnects with jitter
- **Consistency / idempotency:** ordered per conversation · `clientMessageId` scoped to sender device
- **Compatibility:** additive fields only within v1; ignore unknown fields
- **Failure result:** `ACCEPTED` with `messageId`; `REJECTED` before commit; `UNKNOWN` if the gateway deadline expires after the durable acceptance-partition commit may have occurred

### Update receipt

- **Style / transport:** bidirectional event command · `WSS RECEIPT {messageId, delivered|read}`
- **Trust boundary:** recipient device → connection gateway
- **Deadline / retry:** 2 s to accept the receipt update · retry any timeout; duplicate or older states are no-ops
- **Backpressure:** coalesce pending receipts to the highest state per message and pause sends while the socket is unwritable
- **Consistency / idempotency:** monotonic per recipient device · max-state transition
- **Compatibility:** new receipt states require a negotiated protocol version; unknown optional fields are ignored
- **Failure result:** `APPLIED`, `NO_OP`, or `REJECTED`; `UNKNOWN` on timeout is resolved by retrying the same monotonic transition

### Request media upload

- **Style / transport:** REST command resource · `POST /v1/media/uploads`
- **Trust boundary:** authenticated sender device → media API; upload then crosses to object storage
- **Deadline / retry:** 2 s to return an upload URL · retry 429 and 5xx with the same upload request id; do not retry other 4xx responses
- **Backpressure:** 429 with `Retry-After`; client limits concurrent upload requests to two
- **Consistency / idempotency:** eventual attachment availability · upload request id
- **Compatibility:** versioned `/v1` path; response fields are additive and unknown fields are ignored
- **Failure result:** `CREATED` with `uploadId` and a URL valid for 15 min; `RATE_LIMITED` or `REJECTED`; `UNKNOWN` on timeout after creation—retry the same upload request id

## Estimates

Assumptions: 500M DAU (user) · 20 msgs/user/day (assumed) · 1 KB/message (assumed) · peak ×4 (assumed) · 10% media at ~200 KB (assumed) · 5% of messages await an offline recipient, ~2-day mean wait (assumed).

| Metric | Value | Derivation |
|---|---|---|
| messages/day | 10B | 500M × 20 |
| write QPS | 116k avg / 463k peak | 10B ÷ 86,400; × 4 |
| connection memory | ~500 GB fleet-wide | 50M × ~10 KB |
| message storage/day | 10 TB raw; ~1 TB active | 10B × 1 KB = 10 TB/day; active = 5% undelivered × 2-day mean wait ≈ 1 TB; 30-day retention ceiling = 300 TB |
| media ingest/day | 200 TB | 10B × 10% × 200 KB |
| routing lookups | 463k/s peak | one per message → in-memory registry |

## Candidates

**A — Service-based with async delivery spine** `[service-based]`. Coarse stateless services behind persistent-connection gateways; an independently replicated managed queue is the durable transient authority from sender acknowledgement until the message-store commit and consumer acknowledgement, with a seven-day failure backlog while the message store owns 30-day offline retention. Delivery workers materialize per-device inbox entries; reconnecting gateways page the store after each per-conversation cursor, pause on socket backpressure, and durably advance cursors before deleting entries. Pros: no acknowledged-loss window inside the stated failure domain; stateless scaling; simple ops. Cons: queue choke point at 463k/s; fan-out concentrates in workers; retained queue capacity is expensive.

**B — Event-driven backbone (log-first)** `[event-driven]`. The replayable log is transient authority for in-flight messages until the persist consumer commits each message and its per-device inbox entries to the authoritative 30-day store; fan-out and push remain independent consumers. Reconnecting gateways use the same contracted cursor-based store drain as A. Pros: acceptance durability and ordering are log properties; peak absorbs into consumer lag; seven-day replay covers recovery and backfill while the store protects longer-lived history. Cons: highest ops skill floor; latency budget spans two consume hops; harder to test.

**Rejected C — Cell-based isolation** `[space-based]`. Closed before drawing: its write-behind acknowledgement from the in-memory grid can lose acknowledged messages on an ordinary cell crash, violating the zero-loss process/node/zone/promotion contract.

## Comparison and recommendation

**Recommended: B — Event-driven backbone.**

1. Both candidates close the acknowledged-loss window: A acknowledges its replicated durable queue and B its replicated log quorum; each remains transient authority until message-store commit and consumer acknowledgement.
2. At 463k routing lookups/s across 50M live connections, B's independently replayable persistence, fan-out, and push consumers scale and evolve without touching the acknowledgement path.
3. Peak = 4× average: B gives each concern independent lag, replay, and scaling controls rather than A's shared delivery-worker bottleneck.
4. Per-conversation ordering falls out of partition-by-conversation — the consistency target met by construction.
5. Honest costs: B's operational skill floor and testability (2/5) are accepted for replayable consumers and evolvability; C is already closed by the hard invariant.

See `design.json` for the full ratings matrix and per-candidate flows.

Every authoritative queue, log, database, and blob store records its acknowledgement point, independent failure domain, RPO, RTO, and recovery procedure. Every derived cache/view records its reconstruction source and cursor. Every edge records a deadline or maximum age, one retry owner, and a finite concurrency, retention, in-flight, or backlog bound; these contracts are visible in the component inspector.

## Critical deep dives

1. **Acknowledgement is the durability point.** At 463k peak sends/s with zero acknowledged loss inside the ordinary-failure scope, acknowledge only after the partitioned log commits. Gateway memory and an acknowledgement before history persistence both leave a named crash window.
2. **Socket routing is an expiring lease, not durable truth.** At 50M connections, heartbeat-renewed device-to-gateway leases plus inbox replay recover from stale routes and gateway deploys.
3. **Ordering and duplicate suppression are scoped.** Partition by conversation for causal order; deduplicate by sender-device client message id. Wall clocks and a global sequencer are both worse fits.

## Operations and rollout

- Watch produce-to-deliver p99, consumer lag, stale-lease rate, reconnect drain duration, duplicate suppression, and per-conversation hot partitions.
- Drain gateways before deploy; expire their leases; reconnect devices resume from durable cursors.
- Reconcile log offsets against the materialized message store and alert before retention makes replay impossible.
- Stage with one region and shadow consumers, then add regional gateways and asynchronous forwarding after the durability path is proven.

## Risks and what breaks first

- Presence fan-out (status × friends) can exceed message volume — needs its own budget and viewport-scoped subscriptions (at launch scale).
- Delivery-topic-per-gateway rebalance storms during deploys (at 100+ gateways).
- Log retention vs 30-day offline queue: parked messages move to the store, not the log (day one).

## Measurements that could overturn the decision

- If reconnect requires merging enough partitions to breach the 500 ms p99, choose the per-device inbox candidate.
- If fan-out write amplification stays cheap under real group/device distributions, the simpler service-based candidate wins.
- If consumer rebalances or gateway delivery topics cannot stay inside the latency budget, replace the log-spine hot path with a durable inbox and keep the log as a side stream.

## Next steps

1. Prototype the gateway: produce path, own-partition consume, heartbeat reaping.
2. Measure produce→deliver p99 on a loaded 3-broker log against the 500 ms budget.
3. Define the message id: snowflake vs per-conversation sequence.

## Notes
