# Demo: design a greenfield system

Install once:

```bash
npx skills@latest add pinchen147/system-design-skill
```

Then describe the product:

```text
/system-design Design WhatsApp: reliable 1:1 and small-group messaging for 500M DAU
```

## What happens

With no repository to inspect, the skill extracts everything already stated by the prompt and asks only for decisions that can change the architecture:

- the acknowledgement and durability contract;
- online delivery latency;
- offline retention;
- group-size and multi-device boundaries;
- ordering, presence, media, and privacy requirements.

It derives the load before drawing:

- 10 billion messages per day;
- roughly 116,000 average and 463,000 peak writes per second;
- 50 million concurrent connections;
- about 500 GB of fleet-wide connection memory;
- media ingest large enough to keep blobs out of the message path.

Three complete architectures make different structural bets:

1. a service-based delivery spine;
2. an event-driven log backbone;
3. cell-based isolation.

The report keeps every candidate fully drawn, traces its critical flows, and compares durability, ordering, burst absorption, failure isolation, cost, and operating complexity.

## Artifacts

- [Readable design](../../examples/design-whatsapp/DESIGN.md)
- [Structured source](../../examples/design-whatsapp/design.json)
- Standalone report: `$TMPDIR/system-design-design-whatsapp.html`
