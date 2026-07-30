# Contrastive examples

Return to [SKILL.md](SKILL.md). Use these contrasts only when a first-draft recommendation or interface is still generic; copy the specificity, not the scenario.

## Scale vs skew

**BAD:** “Shard the 12,000 writes/s evenly across 12 partitions.”

**GOOD:** “The busiest tenant owns 38% of writes, so hash by `(tenant_id, entity_id)` into 48 virtual partitions and cap one tenant at 1,500 writes/s; otherwise its 4,560 writes/s hotspot saturates a 2,000 writes/s partition while the cluster looks 38% utilized.”

## Replication vs backup

**BAD:** “Three replicas provide disaster recovery.”

**GOOD:** “Three synchronous copies preserve the last acknowledged data through two node losses but also copy an operator’s delete. Keep daily snapshots plus 15-minute log archives in a separate account; restore 2 TB at a measured 450 MB/s in 75 minutes, meeting RPO 15 minutes and RTO 2 hours.”

## Quorum overlap vs freshness

**BAD:** “With N=3, W=2, R=2, every read is current.”

**GOOD:** “W=2 and R=2 overlap, but an overlapping replica can return an older version. Require version comparison across both read responses and read repair; if the API needs linearizable reads after failover, route through the current fenced leader instead.”

## Queue vs log

**BAD:** “Put order events on a queue so any service can replay them.”

**GOOD:** “Use a work queue for email jobs: one worker owns each delivery and completed jobs disappear. Publish `OrderCommitted` to a retained log for billing and analytics: each consumer keeps its own offset and can replay seven days without stealing work from another consumer.”

## Idempotent request vs idempotent external effect

**BAD:** “The request has an idempotency key, so charging is exactly once.”

**GOOD:** “Persist `(account_id, idempotency_key) → charge_operation_id` with the order before calling the provider, pass that same key at the provider boundary, and reconcile `UNKNOWN` timeouts by provider operation ID; retain the mapping for 48 hours, longer than the 24-hour client retry window.”

## Failover vs ownership transfer

**BAD:** “After a 10-second timeout, the replica promotes itself.”

**GOOD:** “The coordinator grants epoch 43 to the replacement only after the old lease expires; every write carries epoch 43 and storage rejects epoch 42. A timeout supplies suspicion, while the storage-validated fencing token transfers ownership and prevents stale-writer corruption.”

## Cache freshness vs correctness

**BAD:** “A 60-second TTL keeps account balances correct enough.”

**GOOD:** “The ledger remains authoritative and enforces `available_balance >= 0`; the cache may serve a balance up to 60 seconds stale for display only. Withdrawal authorization bypasses it, and ledger sequence 918 invalidates any cached value with a lower sequence.”

## Architecture candidate vs database substitution

**BAD:** “Candidate A uses PostgreSQL; Candidate B uses DynamoDB.”

**GOOD:** “Candidate A keeps one regional ordering authority and synchronously commits inventory plus an outbox, accepting cross-region write latency. Candidate B assigns inventory ownership by region and reconciles transfers asynchronously, reducing local write latency but adding a fenced ownership-transfer protocol. Database products are implementation choices inside each candidate.”
