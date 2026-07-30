---
name: system-design
description: Design or evolve a production system from repository evidence, measurable requirements, capacity math, protected invariants, and explicit trade-offs. Reads an existing codebase as the current architecture, closes the requirements it cannot recover on its own, then draws structurally distinct candidates and recommends one with a chained evidence argument. Produces an interactive HTML report, a structured design.json, and a durable DESIGN.md a later session can resume. Use for repository architecture work, greenfield systems, scaling and sharding plans, datastore or consistency choices, capacity and cost sizing, or recording a decision as an ADR. Answers directly when the numbers already settle the choice instead of manufacturing a document.
license: MIT
metadata:
  author: pinchen147
  version: "1.0.0"
---

# System Design

Architecture is decided by invariants, workload numbers, failure modes, and operating constraints—not vibes. Draw the simplest production-viable candidate first, add only evidence-surviving alternatives that differ on a load-bearing axis, recommend one with an evidence chain, and leave a design artifact another coding-agent session can continue.

The process is identical in repository and greenfield work; interview-grade reasoning falls out of production discipline.

Every recommendation must cite an envelope number, a correctness invariant, a named failure mode, or a principle from [HEURISTICS.md](HEURISTICS.md).

Do not load examples by default. Only if a first-draft recommendation or interface remains generic, consult the matching BAD/GOOD contrast in [EXAMPLES.md](EXAMPLES.md), then replace generic language with the relevant number, invariant, ownership boundary, or failure behavior.

## Process

### 0. Size the ask before running the process

This process earns its cost when a decision is hard to reverse, the numbers are load-bearing, or several structurally different designs are genuinely live. Sketch the envelope first. If it lands below the anti-overengineering gates in [HEURISTICS.md](HEURISTICS.md), or one recorded decision already forces the answer, say which gate or decision closed it and answer directly in a paragraph—no artifacts. A false choice rendered as peer tabs is worse than no document.

When the process does run, draw the simplest production-viable design first. Add a candidate only when it remains viable after the envelope and invariants and changes a load-bearing axis—for example, the measured scale boundary or the dominant correctness, failure-isolation, cost, or operability risk. Record options closed by a requirement, gate, or named failure as one-line rejections; do not draw, rate, or audit them as peers. Three candidates is the ceiling, not a target.

### 1. Locate and resume

List existing designs—`docs/design/*/design.json`, or `./*/design.json` outside a git repo—and read each one's `slug`, `title`, and `status`. If one covers this ask, load it and apply the user's feedback before doing new discovery; if two could, name both and ask which.

Otherwise derive a kebab-case slug naming the system or subsystem, not the phrasing of the request (`commerce-layer`, not `add-a-commerce-layer`), and choose:

- **Repository mode** when the ask concerns the current codebase. The existing system is Architecture 0.
- **Greenfield mode** when no implementation exists yet.

State the mode, reason, whether you resumed, and the target directory in one line.

### 2. Establish the current truth

In repository mode, first classify every top-level directory as system code, first-party vendored code under active development, or dependency, sample, and build output. Only the first two are in scope. Directory size is not evidence of importance—the largest tree is usually not the system, and `git log --format=format: --name-only -200 | sed 's#/.*##' | sort | uniq -c | sort -rn` settles most cases. State the classification in one line, including where it contradicts the ask's framing.

Restricted to in-scope paths, read architecture docs, ADRs, domain vocabulary, config, and the hot paths from recent history—plus whatever carries state and effects in this system's shape: schemas, APIs, and queues in a networked service; entry points and lifecycle, state owners, write and flush paths, persisted key namespaces, on-disk formats, entity identity keys, and process or sandbox boundaries in a client, desktop, or embedded codebase. Stop when the flows and invariants below close. Code and schema outrank prose when they disagree—record the divergence under `requirements.conflicts`, and ask rather than picking a side silently when it changes an invariant.

Settled ADRs are constraints, but an ADR that is a stub, superseded, duplicated, or pointing outside this repository is unavailable evidence rather than a constraint; list what you could not read. Name the documents that already own this subject—when one already decides part of the ask, say what it settles and aim the run at what it leaves open. Trace the user-facing flows end to end and inventory every component using the types in [HTML-REPORT.md](HTML-REPORT.md).

In both modes, define:

- core entities and the invariants that must never break;
- system interfaces and their consistency/idempotency contracts;
- critical end-to-end flows, including failure and recovery flows;
- source-of-truth stores versus derived views.

Ask the user only for decisions that cannot be recovered from the repo or prompt.

### 3. Close the requirement frontier

Use [INTERVIEW.md](INTERVIEW.md) to fill only the unresolved frontier. Ask numbered questions in at most three rounds of at most eight, each with a recommended default; with no user present to answer, take the defaults instead of asking. Functional scope, excluded scope, numerical non-functional targets, workload shape, team/cost constraints, and the top three characteristics must be explicit. Label every assumption.

### 4. Run and challenge the envelope

Compute the numbers that gate *this* system. For request-serving systems that is average and peak QPS, storage growth, bandwidth, cache footprint, concurrency, and the domain's load-bearing distribution (burst, skew, fan-out, hot keys, object sizes). Where the binding constraint sits on a device, compute it in the units that bind there: bytes and round trips per session, request volume against provider quotas and their cost, memory ceiling in a process the OS can kill, on-device storage growth, cold-start budget, and offline divergence window. Where money crosses a boundary, compute the unit economics of the events the design protects. Record any standard metric that does not apply as `n/a` with a one-line reason; never invent a number to fill a row. Show derivations and verify arithmetic with a shell command.

Run the physics/CAP sanity pass in [INTERVIEW.md](INTERVIEW.md). Use the compact router in [ARCHETYPES.md](ARCHETYPES.md) to select by protected invariant, then load only the selected pack. Do not load every pack by default. Test the envelope against each selected archetype's **Shape**, and its **Numbers anchor** where it has one. An archetype whose **Not when** clause fires is the wrong match—drop it and say so, rather than importing machinery this system does not need. Resolve contradictions before drawing candidates.

### 5. Fix the data and consistency model

Topology that is correct for the wrong data model is not a design. Before drawing anything, state for each core entity: its representation in memory and at rest, its identity scheme, which component holds ordering authority, how conflicts resolve per field class, the point at which a write becomes durable, and the garbage-collection or compaction story. Use the conflict-resolution rule in [HEURISTICS.md](HEURISTICS.md); it is chosen by the coordination available, not by sophistication.

Write this into `dataModel` before candidates exist. For every structured store, also generate intuitive database schemas: name each table or collection, list only the fields that explain the design, mark primary, partition, sort, and deduplication keys, and state important indexes, relationships, source-of-truth status, and retention notes. Use human-readable cards like `Ticket — id, eventId, seat, price, status, userId`; no executable DDL. Where candidates disagree on any of these, that disagreement is itself a candidate axis—see step 6.

### 6. Draw the candidates

Fully draw the simplest production-viable architecture. Add another only if it survives the envelope and invariants and differs on a load-bearing structural, data-model, consistency, cost, or operability axis. Useful surviving alternatives often optimize for the measured scale boundary or the dominant correctness, failure-isolation, cost, or operability risk. Keep every closed option as a one-line rejection with the requirement, gate, or failure mode that closed it. Never invent a peer merely to fill a tab; stop after three.

In repository mode, each is an evolution of Architecture 0 and migration cost is first-class. Candidates must satisfy the distinctness rule in [HTML-REPORT.md](HTML-REPORT.md#schema-rules). Where the difficulty lives in the data model rather than the component graph—collaborative editing, consensus, ledgers, indexes—generate candidates on the data-model axis and hold topology fixed.

Every distributed mechanism must earn its place with a number, invariant, or named failure mode. Every candidate must state at least one honest weakness, and must clear the **Staff gate** of every archetype it touches in the packs selected through [ARCHETYPES.md](ARCHETYPES.md)—those are the questions a plausible diagram does not answer.

A gate is cleared by answering it in this design's own terms: the component that does it, the number it holds to, or the behaviour it accepts. Repeating the gate's wording is not an answer, and quoting it as evidence for a design that does not implement it is the failure this rule exists to catch. Where an archetype's gate does not apply because you took a different structure, say which structure replaced it and what now covers the failure that gate was guarding—an obligation is discharged or explicitly retired, never dropped. If a candidate deviates from the conventional baseline, name that baseline and prove how the deviation still covers its failure modes.

Author a flow-first canvas for every candidate: set `canvas.primaryFlow`, give every component an approximate center-point `position`, keep names short enough to stay centered inside a conventional shape, and follow the layout rule in [HTML-REPORT.md](HTML-REPORT.md#schema-rules), which also lists what the renderer resolves on its own.

### 7. Decide and deep-dive

Rate every candidate using [HEURISTICS.md](HEURISTICS.md), led by the user's top three characteristics. Recommend one with a chained evidence argument. A rating may not appear in that chain—it is a candidate's opinion of itself. The chain rests on an envelope number, an invariant, or a named failure mode.

Resolve the two or three decisions with the greatest correctness, cost, or operability pressure. Each deep dive must record pressure, decision, rejected alternatives, failure mode, and evidence. State retries, timeouts, idempotency, reconciliation, failover, observability, rollout, what breaks first, and the measurement that would overturn the recommendation.

A design is complete only when:

- every critical flow ends at a named durable or final effect;
- every invariant has one enforcement authority;
- every dependency has a deadline, retry owner, and bounded backlog;
- every authoritative store has an acknowledgement point, failure domain, RPO, and RTO;
- every derived view names its reconstruction source and cursor;
- every candidate has a named first failure;
- every recommendation has a falsifiable evidence chain;
- every unresolved uncertainty is recorded as an assumption or measurement;
- all artifacts pass structural and render checks.

Before rendering, verify:

- every critical flow reaches a durable or final effect;
- every queue/log declares delivery and idempotency semantics;
- every store is source-of-truth or derived;
- every dependency edge names a deadline, who owns the retry, and a bound on the work that can queue behind it;
- offered load is stated against drain capacity, including the amplification retries add exactly when capacity is lowest;
- every authoritative store names its failure domain, its recovery path, and the loss and downtime that path accepts;
- every structured store has an intuitive schema whose fields, keys, indexes, and relationships support its stated access patterns and invariants;
- every schema and wire-contract change names its compatibility direction and the order in which readers and writers deploy;
- the design survives its own clients: duplicate submits, reconnect storms, cold caches, and a dependency that slows instead of failing;
- burst, skew, fan-out, hot keys, and partial failure are addressed;
- security, privacy, abuse, retention, and deletion are addressed where relevant;
- no critical deep dive has been deferred into a vague next step.

### 8. Write, render, and verify

Write `design.json` and regenerate `DESIGN.md` beside it, preserving any user-owned `## Notes` verbatim. Validate all ids and flow references.

Then render and open it. The run is not complete until the report exists on disk and has been opened—a design.json and a DESIGN.md with no report is an unfinished run, not a finished one.

`<skill-dir>` is the directory containing this file, wherever it is installed; the script resolves the template relative to itself, so an absolute path always works:

```bash
python3 <skill-dir>/scripts/render_report.py \
  --design docs/design/<slug>/design.json \
  --out "$TMPDIR/system-design-<slug>.html"
open "$TMPDIR/system-design-<slug>.html"        # macOS; xdg-open on Linux, start on Windows
```

If the skill directory is not known, find it rather than skipping the step: `ls ~/.claude/skills/system-design/scripts/render_report.py ~/.agents/skills/system-design/scripts/render_report.py 2>/dev/null` covers both standalone installs, and a plugin install lives under `~/.claude/plugins/cache/`. Never read [assets/report-template.html](assets/report-template.html) into context or rebuild the report by hand; see [HTML-REPORT.md](HTML-REPORT.md). The report must contain only its own title/date chrome—no prototype or harness wrapper.

Then confirm the render survived. The *rendered page* must show the design's own `title` rather than the template's `System design report` placeholder—a mismatch means the JSON never parsed. The title is set at run time, so the static file still contains the placeholder in its `<title>` tag; grep the embedded `application/json` block instead, or check that no `__DESIGN_JSON__` remains. With a browser tool, load every architecture route and read the hidden `report-diagnostics` element: `data-component-overlaps`, `data-route-collisions`, `data-text-overflows`, and `data-fit-overflows` must all be `0`. Any non-zero value is a `design.json` defect—shorten names, move positions, re-render. Without a browser tool, say the report was rendered but not inspected rather than claiming interactions you cannot see.

Iterate through `design.json`, never by hand-editing rendered HTML.

### 9. Record the decision

When the user chooses, set `status: decided`. In repository mode, offer an ADR under `docs/adr/` that records the accepted candidate, rejected candidates, evidence, and consequences. Name the owning documents from step 2 in its Context, mark any ADR it replaces as superseded, and link `DESIGN.md` from wherever the repo indexes its docs. Future runs must read it and not re-litigate it without new evidence.
