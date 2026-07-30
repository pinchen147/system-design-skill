# Provenance — Traffic and work archetypes

Sources for the runtime pack. Return to the [archetype provenance index](../ARCHETYPES.md).

## Admission control and quota

| Claim | Source |
|---|---|
| Bound a queue by request age rather than depth; drop by sojourn time | https://www.rfc-editor.org/rfc/rfc8289.html |
| Retry budget capped at 20% of active requests with a floor of 3 | https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/cluster/v3/circuit_breaker.proto |
| Admission quota is separate from scheduling and placement | https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/ |
| Retries multiply load exactly when capacity is lowest; recovery is not automatic | https://sre.google/sre-book/handling-overload/ |
| 10k req/s × 100 ms = 1,000 slots; 2,000/s backlog reaches 10,000 in 5 s; 3³ = 27 | derived |

## Durable workflow and retrying work DAG

| Claim | Source |
|---|---|
| History caps near 51,200 events / 50 MB, warning at 10,240 / 10 MB | https://docs.temporal.io/workflow-execution/limits |
| Visibility timeout default 30 s, maximum 12 h; at-least-once means duplicates | https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html |
| The same program may be started twice even at parallelism 1 — steps must be idempotent | https://kubernetes.io/docs/concepts/workloads/controllers/job/ |
| Overlap policy is a named choice: allow, forbid, replace; missed-start deadline | https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/ |
| Heartbeat interval derived from fleet size rather than a global default | https://developer.hashicorp.com/nomad/docs/configuration/server#heartbeat_grace |
| Master-paced polling prevents recovery storms | https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/ |
| 12 h ÷ 30 s = 1,440 redeliveries; 16,400 ÷ 20 s = 820 writes/s | derived |

**Rejected.** "A recurring trigger stops after 100 missed schedules." The limit was removed upstream and
is not in current documentation.

## Politeness-bounded fetch

| Claim | Source |
|---|---|
| Fetch and parse can retry and scale independently when a durable fetched artifact is handed off by reference; the seam is earned when refetch cost or parser lag threatens the deadline | https://learn.microsoft.com/en-us/azure/architecture/patterns/pipes-and-filters · https://learn.microsoft.com/en-us/azure/architecture/patterns/claim-check |

## Third-party channel delivery

| Claim | Source |
|---|---|
| At-least-once processing requires a stable deduplication/effect key at the party performing the effect | [HEURISTICS.md — Transactions](../HEURISTICS.md#transactions) · [HEURISTICS.md — Async and streaming](../HEURISTICS.md#async-and-streaming) |
| An ambiguous timeout does not prove that a remote side effect failed | https://docs.stripe.com/error-low-level#content-errors |
| Provider delivery status is asynchronous and reported by callbacks | https://www.twilio.com/docs/messaging/guides/track-outbound-message-status |
| Commercial email must include a functioning opt-out mechanism and honor an opt-out within 10 business days | https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title15-section7704&num=0&edition=prelim |
| Channel-isolated queues, retry ownership, deadlines, and bounded backlog compose already-sourced dependency rules | [HEURISTICS.md — Interfaces and dependency contracts](../HEURISTICS.md#interfaces-and-dependency-contracts) · [HEURISTICS.md — The envelope](../HEURISTICS.md#the-envelope) |
