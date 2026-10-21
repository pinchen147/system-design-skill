---
name: system-design
description: Design or evolve a production system from repository evidence, measurable requirements, capacity math, protected invariants, and explicit trade-offs. Draws structurally distinct candidates, recommends one with a chained evidence argument, and writes an interactive HTML report, a structured design.json, and a DESIGN.md a later session can resume; in an existing repository it also audits the implementation for architectural debt against the intended design. Use for evolving a repository's architecture, greenfield systems, scaling and sharding plans, datastore or consistency choices, capacity and cost sizing, recording a decision as an ADR, or auditing drift from a recorded design. Also use for a single architecture choice with workload numbers attached, even one that looks small: it checks them against overengineering gates and answers in a paragraph when they settle it. Skip for explaining how a technology or existing code works, debugging, and code-level edits such as refactoring a function.
license: MIT
metadata:
  author: pinchen147
  version: "1.3.2"
---

# System Design

Architecture is decided by invariants, workload numbers, failure modes, and operating constraints—not vibes. Draw the simplest production-viable candidate first, add only evidence-surviving alternatives that differ on a load-bearing axis, recommend one with an evidence chain, and leave a design artifact another coding-agent session can continue.

The process is identical in repository and greenfield work; interview-grade reasoning falls out of production discipline.

Every recommendation must cite an envelope number, a correctness invariant, a named failure mode, or a principle from [HEURISTICS.md](HEURISTICS.md).

Do not load examples by default. Only if a first-draft recommendation or interface remains generic, consult the matching BAD/GOOD contrast in [EXAMPLES.md](EXAMPLES.md), then replace generic language with the relevant number, invariant, ownership boundary, or failure behavior.

A run writes only its own artifacts: `design.json` and `DESIGN.md` in the design directory, the rendered report under `${TMPDIR:-/tmp}`, and, at step 10, the ADR and docs-index link the user accepts. Implementing a candidate or changing code is a separate request.

## Route the ask

Start from what the user brought:

| The user brings | Route |
|---|---|
| A choice a number or a recorded decision may already settle | Step 0. Answer in a paragraph when a gate or decision closes it; otherwise continue |
| An existing design to resume or revise | Step 1 loads it; apply the feedback before any new discovery |
| A change to this codebase, or an audit of its drift from a recorded design | Step 1 resumes a design that covers it; otherwise the full process in repository mode |
| A system with no implementation yet | The full process in greenfield mode; step 8 does not run |
| A pick between candidates already rendered | Step 1 locates the design, then step 10 |
| An explanation of a technology or existing code, a bug, or a code-level edit | Outside this skill. Answer with ordinary tools and run none of these steps |

## Process

### 0. Size the ask before running the process

This process earns its cost when a decision is hard to reverse, the numbers are load-bearing, or several structurally different designs are genuinely live. Sketch the envelope first. If it lands below the anti-overengineering gates in [HEURISTICS.md](HEURISTICS.md), or one recorded decision already forces the answer, say which gate or decision closed it and answer directly in a paragraph—no artifacts. A false choice rendered as peer tabs is worse than no document.

When the process does run, draw the simplest production-viable design first. Add a candidate only when it remains viable after the envelope and invariants and changes a load-bearing axis—for example, the measured scale boundary or the dominant correctness, failure-isolation, cost, or operability risk. Record options closed by a requirement, gate, or named failure as one-line rejections; do not draw, rate, or audit them as peers. Three candidates is the ceiling, not a target.

### 1. Locate and resume

List existing designs—`docs/design/*/design.json`, or `./*/design.json` outside a git repo—and read each one's `slug`, `title`, and `status`. If one covers this ask, load it and apply the user's feedback before doing new discovery; if two could, name both and ask which.

A loaded design that records `context.observed.commit` says which code it described. Run `git diff --stat <commit>..HEAD`; at step 2, once the in-scope paths are classified, re-read the ones it lists rather than the whole tree. When the history no longer contains that commit, or the design recorded `uncommittedChanges: true`, the drift is unknown: read the in-scope tree as if nothing had been recorded.

Otherwise derive a kebab-case slug naming the system or subsystem, not the phrasing of the request (`commerce-layer`, not `add-a-commerce-layer`), and choose:

- **Repository mode** when the ask concerns the current codebase. The existing system is Architecture 0.
- **Greenfield mode** when no implementation exists yet.

State the mode, reason, whether you resumed, and the target directory in one line.

### 2. Establish the current truth

In repository mode, first classify every top-level directory as system code, first-party vendored code under active development, or dependency, sample, and build output. Only the first two are in scope. Directory size is not evidence of importance—the largest tree is usually not the system, and `git log --format=format: --name-only -200 | sed 's#/.*##' | sort | uniq -c | sort -rn` settles most cases. State the classification in one line, including where it contradicts the ask's framing. Record what you are reading as `context.observed`: the commit `git rev-parse HEAD` reports, and whether `git status --porcelain` lists changes in the in-scope paths. Outside git, omit it.

Restricted to in-scope paths, read architecture docs, ADRs, domain vocabulary, config, and the hot paths from recent history—plus whatever carries state and effects in this system's shape: schemas, APIs, and queues in a networked service; entry points and lifecycle, state owners, write and flush paths, persisted key namespaces, on-disk formats, entity identity keys, and process or sandbox boundaries in a client, desktop, or embedded codebase. Stop when the flows and invariants below close. Code and schema outrank prose when they disagree—record the divergence under `requirements.conflicts`, and ask rather than picking a side silently when it changes an invariant.

Settled ADRs are constraints, but an ADR that is a stub, superseded, duplicated, or pointing outside this repository is unavailable evidence rather than a constraint; list what you could not read. These ADRs are also the reference model the audit at step 8 measures against, so record each one's status: a decision that is accepted and quietly violated is a different finding from one that was superseded and never removed. Name the documents that already own this subject—when one already decides part of the ask, say what it settles and aim the run at what it leaves open. Trace the user-facing flows end to end and inventory every component using the types in [HTML-REPORT.md](HTML-REPORT.md).

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

- every queue/log declares delivery and idempotency semantics;
- every store is source-of-truth or derived;
- every authoritative store names the recovery path that meets its RPO and RTO;
- offered load is stated against drain capacity, including the amplification retries add exactly when capacity is lowest;
- every structured store has an intuitive schema whose fields, keys, indexes, and relationships support its stated access patterns and invariants;
- every schema and wire-contract change names its compatibility direction and the order in which readers and writers deploy;
- the design survives its own clients: duplicate submits, reconnect storms, cold caches, and a dependency that slows instead of failing;
- burst, skew, fan-out, hot keys, and partial failure are addressed;
- security, privacy, abuse, retention, and deletion are addressed where relevant;
- no critical deep dive has been deferred into a vague next step.

### 8. Audit the architecture for debt

Repository mode only, and only now: a finding's exposure is measured against the candidate this run recommends, which did not exist until the previous step. Greenfield has no implemented architecture to compare against and skips this step entirely.

Follow [AUDIT.md](AUDIT.md). The order of its stages is the substance, not the ceremony: collect the structural facts—graph, edge contracts, ADR statuses, change history—before forming any verdict; generate candidate findings one category at a time, without showing the finder the previous run's list; put every candidate through the mechanical gates; hand the survivors to a red team that sees the claim but never the argument behind it. A model is an unreliable detector of architectural problems and a reliable disprover of them, so nothing reaches the report until something has tried to destroy it.

Where a subagent primitive exists, run one finder per category and one verifier per lens. Where it does not, run the same stages inline, restating the brief and discarding the previous stage's reasoning at each boundary. A single pass that finds and judges at once is the one shape that does not work.

Write the result into `design.json` under `debt`, including what was checked and what could not be established. Findings may seed `risks` and `nextSteps`; they never generate a candidate, and they never become an ADR.

The audit is done when every finding cites evidence and passes all four debt tests, every `blocking` finding names by id the invariant or target it violates, and `debt.checked` lists every category examined, with every check the run could not establish recorded rather than dropped.

### 9. Write, render, and verify

Write `design.json` and regenerate `DESIGN.md` beside it, preserving any user-owned `## Notes` verbatim. Validate all ids and flow references.

Then render and open it. The run is not complete until the report exists on disk and has been opened, or its path handed over where nothing can open it—a design.json and a DESIGN.md with no report is an unfinished run, not a finished one.

`<skill-dir>` is the directory containing this file, wherever it is installed; the script resolves the template relative to itself, so an absolute path always works:

```bash
python3 <skill-dir>/scripts/render_report.py \
  --design docs/design/<slug>/design.json \
  --out "${TMPDIR:-/tmp}/system-design-<slug>.html"
```

The script opens the report itself once it is written, so there is no separate step to forget. Pass `--no-open` only when nobody is watching—a scripted or headless run. Whatever fails, iterate through `design.json`: never read [assets/report-template.html](assets/report-template.html) into context, rebuild the report by hand, or edit the rendered HTML; see [HTML-REPORT.md](HTML-REPORT.md). The report must contain only its own title/date chrome—no prototype or harness wrapper.

Then confirm the render survived. The page sets its title at run time, so the static file's `<title>` tag keeps the template's `System design report` placeholder; check instead that the embedded `application/json` block carries the design's own `title` and that no `__DESIGN_JSON__` remains. With a browser tool, load every architecture route and read the hidden `report-diagnostics` element: `data-component-overlaps`, `data-route-collisions`, `data-text-overflows`, `data-fit-overflows`, and `data-label-occlusions` must all be `0`.

When a command or check does not go as described, act on what you observe:

| You observe | It means | Next |
|---|---|---|
| `render_report: cannot read design …`, `malformed JSON in …`, or `… must hold a JSON object` | `design.json` is missing, is not valid JSON (`NaN` and `Infinity` included), or is not an object; nothing was written | Fix the path or the file at the place the message names, then re-render |
| `render_report: cannot write <path>` | The `--out` directory is not writable; a path of `/system-design-…` means `$TMPDIR` was unset | Re-run with the `${TMPDIR:-/tmp}` form above, or another writable path |
| `render_report.py` not found, `render_report: cannot read template …`, or `… must contain __DESIGN_JSON__ exactly once` | `<skill-dir>` is unknown or names a damaged copy of the skill | `ls ~/.claude/skills/system-design/scripts/render_report.py ~/.agents/skills/system-design/scripts/render_report.py 2>/dev/null` covers both standalone installs; a plugin install lives under `~/.claude/plugins/cache/` |
| `render_report: warning: … has no design title` | `design.json` lacks `title`, so the page heading reads `System design report` | Add `title`, then re-render |
| The page reads `This is the empty report template` | The payload never reached the page | Re-render with the installed skill's `render_report.py`, never a copied or hand-filled template; if the script's own output still shows this, report it as a renderer defect |
| Any non-zero `report-diagnostics` value | A `design.json` layout defect | Shorten names or move positions, then re-render |
| `render_report: no opener found` or `render_report: could not open the report` | A headless session; the file is already written | Hand over the absolute path the script printed: the report is self-contained and portable |
| No browser tool | Diagnostics and interactions cannot be read | Say the report was rendered but not inspected, and claim nothing it would have shown |
| `python3` is missing | The report cannot be produced here | Report the run as unfinished, with `design.json` and `DESIGN.md` written |

Finish by answering the ask, not by listing the files written. Go back to what the user asked for and mark each part answered, partly answered, or open, naming what is still missing. Lead with the recommendation and its evidence chain in a few lines; name the `assumed` inputs it rests on and the measurement that would overturn it; state what was not verified, such as an uninspected report or audit checks the run could not establish; then give the report and `design.json` paths. End with the decision that belongs to the user, which step 10 records.

### 10. Record the decision

When the user chooses, set `status: decided` and `decided` to the chosen architecture's id, then regenerate `DESIGN.md`, whose frontmatter carries both. In repository mode, offer an ADR under `docs/adr/` that records the accepted candidate, rejected candidates, evidence, and consequences. Name the owning documents from step 2 in its Context, mark any ADR it replaces as superseded, and link `DESIGN.md` from wherever the repo indexes its docs. Future runs must read it and not re-litigate it without new evidence.
