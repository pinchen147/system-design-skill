# System Design Skill Launch Kit

Canonical repository: <https://github.com/pinchen147/system-design-skill>

Release: <https://github.com/pinchen147/system-design-skill/releases/tag/v1.0.0>

Install:

```bash
npx skills@latest add pinchen147/system-design-skill
```

Claude plugin:

```bash
claude plugin marketplace add pinchen147/system-design-skill
claude plugin install system-design-skill@pinchen-skills
```

## X

System design from evidence, not vibes.

I open-sourced `/system-design`, a free MIT Agent Skill that reads an existing repository, gets the unresolved requirements out of you, runs the capacity math, and aims for three structurally distinct, viable architectures before recommending one.

Outputs: one self-contained HTML report, `design.json`, and `DESIGN.md`.

Works with Claude Code, Codex, Cursor, and other Agent Skills-compatible coding agents.

Install:

`npx skills@latest add pinchen147/system-design-skill`

<https://github.com/pinchen147/system-design-skill>

## LinkedIn

I have open-sourced a system-design workflow for coding agents.

The failure I wanted to fix was familiar: ask an agent to design a system and it often jumps straight to a confident diagram. The requirements are incomplete, no one has run the numbers, and the architecture is a list of fashionable components rather than a defensible decision.

`/system-design` follows a more disciplined sequence:

1. Survey the existing repository as Architecture 0.
2. Ask only for unresolved product and engineering decisions.
3. Define entities, invariants, interfaces, and critical flows.
4. Derive QPS, storage, bandwidth, concurrency, burst, skew, and fan-out.
5. Aim for three structurally distinct candidates that survive the envelope and invariants.
6. Compare them using numbers, failure modes, migration cost, and operating constraints.

It outputs a self-contained single-page HTML report, a structured `design.json`, and a durable `DESIGN.md`.

The skill is free, MIT licensed, and works with Claude Code, Codex, Cursor, and other compatible agents:

`npx skills@latest add pinchen147/system-design-skill`

<https://github.com/pinchen147/system-design-skill>

## Reddit

### Suggested title

I open-sourced a repo-first system-design skill that compares three viable architectures before recommending one

### Post

I built this because coding agents tend to jump from a vague prompt straight to one confident architecture.

`/system-design` starts by reading the existing repository and reconstructing Architecture 0. It then asks only for unresolved decisions, runs the workload and capacity math, and aims for three viable candidates: simplest production-viable, measured-scale boundary, and dominant-risk.

The output is:

- a self-contained interactive HTML report;
- `design.json` as the source of truth;
- a durable `DESIGN.md` future agent sessions can resume.

It is free and MIT licensed:

```bash
npx skills@latest add pinchen147/system-design-skill
```

Repository: <https://github.com/pinchen147/system-design-skill>

I would especially value feedback on the requirements interview and whether each candidate earns its complexity in your own repositories.

## Hacker News

### Title

Show HN: System Design from Evidence, Not Vibes – a Free Agent Skill

### Submission URL

<https://github.com/pinchen147/system-design-skill>

### First comment

I built this after repeatedly seeing coding agents answer incomplete system-design prompts with one polished diagram and no capacity math.

The skill reads an existing repository first, asks only for decisions it cannot recover, derives the load envelope, and aims for three structurally distinct architectures that remain viable. It renders the result as a local, self-contained HTML page and writes JSON plus Markdown so later agent sessions can continue from the same reasoning.

There is no service or account behind it. The package is Markdown, JSON contracts, and a local HTML/SVG renderer under MIT.

I would be interested in feedback from people using coding agents on real existing systems, particularly where the current architecture and migration constraints matter more than a clean-slate answer.

## Newsletter or podcast pitch

### Subject

Free system-design skill for Claude Code, Codex, and Cursor

### Message

Hi,

I have released `system-design`, a free MIT Agent Skill for turning an existing repository or incomplete prompt into a defensible architecture decision.

The skill surveys the current system, interviews the user only on unresolved requirements, derives the capacity envelope, and aims for three viable architectures with explicit trade-offs and failure modes before recommending one. The outputs are a self-contained interactive HTML report, a structured JSON source, and a durable Markdown design.

The repository includes real repository-evolution, greenfield, and interview examples:

<https://github.com/pinchen147/system-design-skill>

Install:

```bash
npx skills@latest add pinchen147/system-design-skill
```

If this fits your audience, I would be happy for you to try it against an existing repository and share an honest result.

Best,

Pin Chen

## Publishing status

These drafts are prepared locally because this environment does not have authenticated publishing access to X, LinkedIn, Reddit, Hacker News, or a newsletter platform. They can be posted verbatim or adapted to the norms of a specific community.
