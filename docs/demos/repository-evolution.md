# Demo: evolve an existing repository

Install once:

```bash
npx skills@latest add pinchen147/system-design-skill
```

Then run inside the repository:

```text
/system-design Evolve Excalidraw collaboration and persistence for reliable late join, history, and self-hosting
```

## What happens

The skill reads the monorepo before asking questions. In this run it reconstructed Architecture 0 from the editor packages, Socket.IO relay, browser storage, encrypted Firebase rooms, and encrypted share-link store.

It then closed only the unresolved product and operating decisions:

- whether encrypted history may exist server-side;
- how long collaboration history must survive;
- which existing protocols must remain compatible;
- whether self-hosting or minimum migration risk has priority.

The operating envelope placed the pressure on collaboration fan-out and recovery, not raw document storage. Three complete evolutions followed:

1. **Unified sync service** — one encrypted operation log replaces the relay, Firebase room storage, and share store.
2. **Scaled relay** — keeps the blind-relay model, shards rooms, and adds encrypted snapshots.
3. **Microkernel editor** — optimizes editor extensibility rather than the collaboration and persistence bottleneck.

The recommendation favored the unified sync service because only it changed the storage model responsible for the stated failures. Migration cost remained a first-class comparison axis because this was an existing system, not a blank slate.

## Artifacts

Every run writes the same three, beside each other:

- `docs/design/<slug>/DESIGN.md` — the readable design
- `docs/design/<slug>/design.json` — the structured source of truth
- `$TMPDIR/system-design-<slug>.html` — the standalone report

See [examples/design-ticketing](../../examples/design-ticketing/DESIGN.md) for a complete pair.

Run `/system-design` again with feedback and it resumes from the JSON instead of surveying the repository again.
