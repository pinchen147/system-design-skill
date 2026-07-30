# Requirement Frontier

The requirement-closing protocol [SKILL.md](SKILL.md) runs at **Close the requirement frontier**, and the sanity pass it runs at **Run and challenge the envelope**. Used identically in repository and greenfield work. The goal is production clarity, not ceremony.

## Protocol

Start with evidence. In repository mode, pre-fill answers from ADRs, schemas, APIs, telemetry, config, code, and recent history. In greenfield mode, pre-fill everything stated by the prompt. Never ask the user a fact the workspace already answers.

Treat unresolved decisions as a dependency tree. The **frontier** is every question whose prerequisites are settled. Each round:

1. Ask the whole frontier at once, numbered and grouped, with at most eight questions.
2. Give each question one recommended default and a one-line reason, so “use your recommendations” is a complete answer.
3. Wait, incorporate the answers, and recompute the frontier.
4. Stop after at most three rounds; fill remaining gaps with visible assumptions.

If no one is answering—an agent-driven, scheduled, or subagent run, or a user who has already delegated the choices—do not post questions into an empty room. Answer the frontier yourself from the recommended defaults and continue; the run proceeds without the user's judgement, and every answer taken this way is tagged `assumed`, never `user`.

Facts are the agent's job. Decisions with material product, correctness, cost, or operating consequences belong to the user.

Typical sequence:

- Round 1: scope, actors, core flows, entities, invariants, and workload.
- Round 2: measurable targets, failure/consistency choices, team/cost constraints, and the top three characteristics.
- Round 3: unresolved domain failure modes, build/buy boundaries, rollout constraints, and deep-dive steering.

## Question bank

Choose only questions that can change the architecture.

### Scope, domain, and workload

| Question | Why it matters | Recommended default |
|---|---|---|
| Which two or three flows are core, and what is explicitly excluded? | Scope determines which architecture is being designed | The smallest complete product loop |
| Who are the actors and client types? | Trust boundaries and protocols start here | Derive from the repo/product |
| What are the core entities? | Ownership and partition boundaries follow the domain model | Entities touched by the core flows |
| Which invariants must never break? | Correctness drives topology more reliably than component fashion | Money, inventory, identity, ordering, and acknowledged durability first |
| DAU, peak concurrency, actions per user, and growth horizon? | Downstream capacity math derives from these | Domain-typical values, visibly labelled assumed |
| Read:write ratio and payload/object-size distribution? | Average payload alone hides storage and bandwidth cliffs | Include p50/p99 or hard limits where relevant |
| Is traffic steady, bursty, skewed, or fan-out dominated? | Peak shape and hot keys often matter more than average QPS | Model the known worst distribution |

### Targets and operating choices

| Question | Why it matters | Recommended default |
|---|---|---|
| What is the p99 target for each critical operation? | Tail latency amplifies across fan-out and remote calls | <500 ms interactive; <100 ms type-ahead |
| Under a partition, which operations refuse work and which serve stale? | CP/AP is a per-invariant decision, not a product slogan | CP for money/inventory/identity; AP for content/discovery |
| For each authoritative write, after which failures may an acknowledged result still be lost: process, node, promotion, zone, region, corruption, or operator error? | The loss contract determines whether acknowledgement may occur at memory, local WAL, or durable replicated/quorum storage | No acknowledged loss on ordinary promotion; make broader disaster loss explicit |
| What are the time-based RPO and RTO for each relevant failure scope? | They determine replication, backup cadence, restore capacity, and failover automation | Define separate targets for regional loss, corruption, and operator error |
| After node, region, operator, or corruption loss, which snapshot/backup and log source is authoritative for recovery? | A replica alone does not recover replicated deletion or corruption | Independent verified snapshot plus retained ordered logs for PITR |
| What ordering and read-your-writes guarantees are actually visible to users? | Scoped guarantees are cheaper and more achievable than global strength | Session or entity-scoped guarantees |
| Retention, deletion, privacy, abuse, and compliance obligations? | These can change storage, keys, logs, and trust boundaries | Minimise retention and make deletion explicit |
| Availability target and failure blast radius? | Nines and isolation have direct cost | 99.9% unless money, safety, or an existing SLO says otherwise |
| Which three architecture characteristics matter most? | The top three decide which trade-offs are acceptable; a design that tries to support everything sinks on launch | Derive from [HEURISTICS.md](HEURISTICS.md) |
| What team, budget, hosting, and rollout constraints are binding? | Operability and migration are architecture inputs | Smallest design the current team can safely run |

### Failure modes and deep dives

| Question | Why it matters | Recommended default |
|---|---|---|
| Which component or invariant breaks first at the envelope boundary? | Deep dives should follow pressure, not novelty | The highest correctness/cost/operability risk |
| For each load-bearing dependency, what is its deadline, which single layer owns retries, and what bounded backlog/admission rule applies? | Unowned retries and unbounded queues turn dependency failure into overload | Deadline inside the caller budget; one retry owner; capped jittered retries and bounded admission |
| What completion and failure states are externally visible, including a timeout after an effect may have committed? | Callers need a durable way to distinguish lifecycle from observation uncertainty | Operation ID with pending, succeeded, failed, and reconciling; surface `UNKNOWN` observation and reconcile before a new effect |
| What conventional baseline applies, and why might this system deviate? | Clever deviations must still cover canonical failures | Use the baseline until evidence disproves it |
| Which commodity parts should be bought? | Rebuilding undifferentiated infrastructure adds risk | Buy CDN/blob/push/payments/device-sync unless they are the differentiator |
| Which settled decisions or migration constraints cannot move? | Existing contracts and ADRs are real constraints | Preserve recorded decisions unless new evidence invalidates them |
| What measurement would reverse the recommendation? | Load-bearing assumptions need a falsification plan | Instrument the least-certain envelope input |

## Completion criterion

Do not draw candidates until the following are explicit or visibly assumed:

| Section | Must contain |
|---|---|
| Functional scope | Core flows, stretch features, and excluded scope |
| Domain | Core entities, ownership, and invariants |
| Interfaces | Boundary, transport, consistency, idempotency |
| Non-functional targets | Numerical targets with units and percentiles |
| Workload | Average/peak, concurrency, size distributions, burst/skew/fan-out, growth — in the units that gate this system, `n/a` with a reason where one does not apply |
| Priorities | Top three characteristics, in any order |
| Constraints | Team, cost, hosting, privacy/security, rollout/migration |

## Sanity pass

Run after the envelope and before candidates:

- **Speed of light:** a cross-region round trip is roughly 150 ms; cross-region consensus cannot satisfy a sub-100 ms p99.
- **CAP:** “strongly consistent and always available under partition” is contradictory. Choose per invariant.
- **Delivery:** exactly-once is not a network property. Use at-least-once, idempotent effects, and deduplication.
- **Acknowledgement:** a client-visible acknowledgement before the authoritative durable effect creates a named loss window.
- **Nines versus team:** each extra nine multiplies redundancy and operating cost.
- **Burst versus average:** ticket on-sales, auctions, and retries need admission control and elasticity, not merely more steady-state capacity.
- **Overload:** retries multiply offered load exactly when capacity is lowest, and an unbounded queue converts latency into failure rather than absorbing it. Name the admission limit, what is shed first, and how the system returns to health after offered load drops — recovery is not automatic.
- **Skew and fan-out:** unbounded followers, groups, tenants, spatial cells, or hot objects break average-based designs.
- **Latency fan-out:** the slowest of N downstream calls determines the user-visible tail.
- **Security and privacy:** encryption, deletion, tenancy, and abuse controls can alter topology; they are not a final checklist.
- **Untrusted edge:** a client sits outside the trust boundary. A device clock is user-settable, so a rule keyed on a client timestamp loses writes unpredictably rather than merely lossily, and a quota, entitlement, or limit enforced only on the client is UX, not enforcement. Each needs a server-assigned ordering or a server-side check, or a stated accepted exposure.
- **Version skew:** readers and writers deploy at different times, and shipped clients cannot be rolled back — the previous release keeps writing for months. Every wire, stored, and on-device schema change must be readable by the release before it, and a retired field name or number is never reused.

Record every accepted conflict under `requirements.conflicts`. It is a design input, not a footnote.
