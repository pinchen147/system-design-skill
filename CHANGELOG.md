# Changelog

All notable changes to this project are documented here.

## 1.0.0 — 2026-07-31

First public release.

### The process

- Surveys an existing repository and reconstructs its current system as Architecture 0, classifying which directories are system code before reading any of them.
- Sizes the ask before running: when a gate or a recorded decision already closes the question, it answers in a paragraph rather than manufacturing a document.
- Closes unresolved requirements through focused, recommendation-backed question rounds, and proceeds on visible defaults when no one is there to answer.
- Derives the numbers that gate the system — throughput, storage, bandwidth, concurrency, burst, skew, fan-out, availability composition, and unit economics — and verifies the arithmetic before it enters a document.
- Fixes the data and consistency model per entity before drawing anything: representation, identity, ordering authority, conflict resolution, durability point, and garbage collection.
- Draws structurally distinct candidates, three by default, compares them on invariants, numbers, failure modes, migration cost, and operability, and recommends one with a chained evidence argument.
- Resolves the two or three decisions under the greatest pressure, each recording decision, rejected alternatives, failure behaviour, and evidence.

### The reference material

- Decision rules and mechanism ladders for data models, storage engines, schema and encoding evolution, caching, replication and consistency, partitioning, transactions, streaming and time semantics, communication, and scaling.
- Archetypes indexed by the invariant they protect rather than by the product that made one famous, routed through a protected-invariant index into six packs — authoritative state, derived serving, realtime and sync, traffic and work, control and security, data delivery.
- Every archetype carries a `Not when` disqualifier and an `Anti-gate` below which its machinery is unjustified complexity, so a shape is rejected before its moves are imported.
- Provenance for every principle carrying a number lives under `docs/provenance/`, including numbers rejected during verification and the reason, so they are not quietly reintroduced.

### The artifacts

- A structured `design.json` as the source of truth, a durable `DESIGN.md` a later session can resume, and a self-contained interactive HTML report with fitted architecture canvases, conventional component shapes, obstacle-aware connectors, zoom and pan, a permanent flow sidebar, and component inspection.
- Authoritative stores declare acknowledgement, failure domain, recovery objectives, and restore path; derived views declare their source and cursor; every dependency edge declares its deadline, retry owner, and bounded backlog.

### Distribution

- MIT licensed. Works with Claude Code, Codex, Cursor, and other Agent Skills-compatible agents, as both a standalone Agent Skill and a versioned Claude Code plugin.
