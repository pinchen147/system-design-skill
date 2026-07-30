# Demo: design a greenfield system

Install once:

```bash
npx skills@latest add pinchen147/system-design-skill
```

Then describe the product:

```text
/system-design Design a ticketing platform for high-demand on-sales. A venue has 60,000 seats
across 6 price tiers, 2 million fans arrive in the first 60 seconds, and the seat writer is
measured at 300 state transitions per second. Holds last 10 minutes. Nobody may be charged
without receiving a seat.
```

## What happens

With no repository to inspect, the skill takes everything the prompt already states and asks only for decisions that can change the architecture:

- which operations refuse work under a partition, and which serve stale;
- the acknowledgement point — when a fan is told a seat is theirs;
- what happens to a hold when payment outlives it;
- overbooking as a product rule rather than an accident;
- the fairness contract for an oversubscribed on-sale.

It derives the load before drawing anything, and separates rates the prompt invites you to conflate:

- 33,333 arrivals per second against a writer measured at 300 transitions per second — a 111:1 reduction the admission tier has to produce;
- an absolute floor of 400 seconds to move 60,000 seats through that writer, which nothing in front of it can beat;
- a 68-second payment window inside the 10-minute hold, from provider authorization p99 plus webhook p99 plus margin;
- 2.54 seat transitions per second platform-wide at 40M tickets a year — six times below the write rate that would justify distributing anything.

That last number does most of the work. The rate says one transactional writer is ample, so distribution has to be earned by an invariant spanning owners you cannot put in one transaction — and here there is none. Sagas and two-phase commit are rejected on the invariant, with the number as corroboration.

Three complete candidates make different structural bets:

1. one transactional core behind an edge admission gate;
2. per-tier write authorities;
3. deferred allocation with an auditable draw.

The report keeps every candidate fully drawn, traces the claim and payment flows end to end, shows the schemas behind the seat, hold, order, payment, and ledger stores, and compares correctness under failure, burst absorption, fairness, cost, and operating complexity.

## Artifacts

- [Readable design](../../examples/design-ticketing/DESIGN.md)
- [Structured source](../../examples/design-ticketing/design.json)
- Standalone report: `$TMPDIR/system-design-design-ticketing.html`
