# Demo: work through an interview prompt

Install once:

```bash
npx skills@latest add pinchen147/system-design-skill
```

Then start with the prompt exactly as given:

```text
/system-design Design Ticketmaster
```

## What happens

The process is the same one used for production architecture work. The skill first makes the vague prompt measurable:

- 10 million fans may converge on one on-sale in five minutes;
- one event has roughly 60,000 seats;
- the seat claim may never double-book;
- search must remain responsive while booking stays consistent;
- payment card data stays with the payment provider.

The envelope reveals two different systems inside one product. Browse and search are read-heavy and may be slightly stale. Seat claims are a small, strongly consistent serialization problem hidden behind an extreme arrival burst.

Three candidates expose the real trade-off:

1. **Throttled ACID core** — a waiting room converts 33,000 arrivals per second into a controlled admission rate; one relational primary serializes seat claims.
2. **In-memory seat grid** — one authoritative in-memory owner per event, backed by a replicated log.
3. **Log-ordered allocator** — purchase intents enter one ordered partition and a deterministic allocator assigns seats.

The first candidate wins because the waiting room keeps the booking core near 600 writes per second, while a 7.5 KB CDN availability bitmap collapses millions of read requests into a small origin load. The other two designs solve a write-scaling problem the stated envelope does not yet have.

## Artifacts

The run produces:

- `docs/design/design-ticketmaster/design.json`
- `docs/design/design-ticketmaster/DESIGN.md`
- `$TMPDIR/system-design-design-ticketmaster.html`

The value is not memorizing the winning components. It is showing how requirements, invariants, and workload numbers eliminate architectures that are either unsafe or unnecessarily complex.
