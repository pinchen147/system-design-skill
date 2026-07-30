# Provenance

Skill content states principles without citing authors, books, or other skills. That rule keeps the
skill readable and keeps a model from arguing by authority, but it also means a maintainer reading
`HEURISTICS.md` cannot tell which sentences are load-bearing and which are folklore.

This directory is the answer. One file per skill file, mirroring its `##` headings, one row per claim:
what the skill asserts, where it comes from, and when that source was last checked.

Nothing links here from `SKILL.md`, so the model never opens it and it costs zero tokens at run time.

## Rules

- A principle that carries a number, a threshold, or a correctness claim needs a row. A stylistic or
  organisational sentence does not.
- Prefer, in order: original papers and specifications · standards bodies · first-party product
  documentation · first-party engineering writing. A secondary source is a placeholder, not a citation.
- Record the date checked. A source that has moved or changed is worse than no source, because it
  reads as verified.
- When a number was rejected during verification, record it under **Rejected** with the reason. That
  is the most useful column in the file — it stops the same wrong number being re-added later.

## Files

- [HEURISTICS.md](HEURISTICS.md) — the decision rules, the ladders, the envelope numbers
- [ARCHETYPES.md](ARCHETYPES.md) — per-shape numbers anchors and anti-gates
