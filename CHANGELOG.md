# Changelog

All notable changes to this project are documented here.

## 1.4.0 — 2026-10-21

### Added

- Bundled Python CLI for tracked evidence, questions, unknowns, checks, stale-write protection, source freshness, and explicit checkpoint recovery. The installed coding agent supplies reasoning; no model SDK or server is required.
- Additive investigation display in reports, including legacy coverage limitations and separate check outcomes.
- Research provenance for the evidence lifecycle and scoped verification contracts.

### Fixed

- Undecidable audit checks remain unknown instead of becoming refutations or survived attempts.
- Invocation evaluation rejects incomplete/error trials, retains optional attempt evidence, and reports unavailable costs honestly.

## 1.3.4 — 2026-10-21

### Fixed

- Treat timeouts as unknown caller observations in payment and workflow contracts, calculate recovery in time units, and include UUIDv7 as a time-ordered alternative.

## 1.3.3 — 2026-10-21

### Fixed

- Apply conversion once in unit economics, distinguish avoidable loss from gross revenue, and scope package withdrawal rules to npm.

## 1.3.2 — 2026-10-21

### Fixed

- Read and write reports explicitly as UTF-8 and report invalid Unicode through the existing diagnostic.

## 1.3.1 — 2026-10-14

### Added

- `scripts/eval-invocation.py` sends every invocation fixture to a headless Claude Code session that loads only this plugin, and grades whether the skill was invoked. Discovery is decided by the description alone, so a description change is now measured against a live agent before it ships rather than approved by reading it.

### Fixed

- A small architecture choice with numbers attached never reached the skill. The first live run passed 12 of 14 fixtures: both direct-answer cases, sharding at 20 writes per second and cache-aside versus write-through at 10 writes and 500 reads per second, were answered without invoking it in 3 of 3 runs, so the overengineering gates never ran. The description now names that ask, and all 14 cases pass in 3 of 3 runs, the five that must not invoke included.

## 1.3.0 — 2026-10-13

### Added

- A design records the code it describes. Repository runs write `context.observed` into `design.json`: the commit they read, and whether in-scope paths had uncommitted changes. A resumed run diffs from that commit and re-reads only what changed, so a drift audit of a design recorded a year ago starts from what actually moved. A commit the history no longer contains, or one read alongside uncommitted changes, leaves the drift unknown, and the run reads the whole tree.
- The skill states what a run may write: `design.json`, `DESIGN.md`, the rendered report, and at the decision step the ADR and docs-index link the user accepts. Implementing a candidate or changing code is a separate request.

## 1.2.0 — 2026-10-13

### Added

- Every ask has a stated starting point. A routing table maps what the user brings to where the run starts: a choice the numbers may settle, an existing design to resume, a change or a drift audit in the current codebase, a new system, or a pick between rendered candidates. A drift audit or a pick resumes the recorded design first rather than redrawing what was already decided.
- The run ends by answering the ask. Step 9 stopped once the report opened, and nothing said what to tell the user. A run now goes back to the ask, marks each part answered, partly answered, or open, and leads with the recommendation, the assumed inputs it rests on, the measurement that would overturn it, and what was not verified.
- Render failures map to a next step. A table in step 9 quotes the renderer's own messages and gives the meaning and the remedy for each, from a design the page cannot parse to a headless session with no way to open the report.

### Changed

- The description says when not to run. It listed every reason to fire and none to stay out, while five of the invocation fixtures expect no invocation. Explaining a technology or existing code, debugging, and code-level edits are now named as outside the skill.
- Step 7 carried two checklists that restated three of the same checks in different words. The restatements are gone, except for the recovery path, which the completion contract does not name and which stays as its own check. The debt checks, which sat in step 7 under the pre-render list, now close step 8, where the findings are produced.

### Fixed

- The render command failed wherever `TMPDIR` is unset, which includes most Linux shells: `--out "$TMPDIR/..."` became `/system-design-<slug>.html`, which any user who cannot write to `/` cannot create. The command now uses `${TMPDIR:-/tmp}`.
- A `design.json` holding `NaN`, `Infinity`, or a top-level value other than an object rendered with exit 0 and opened as the empty report template, because Python's parser accepts what the page's does not; a top-level list also crashed after writing. The renderer now refuses all of them before writing anything.
- Recording a decision set only `status`, so `decided` stayed empty and `DESIGN.md`'s frontmatter went stale. Step 10 now sets both and regenerates `DESIGN.md`.

## 1.1.1 — 2026-08-12

### Fixed

- The debt panel opened by describing itself. A hardcoded sentence under the heading said the findings were ordered by severity, cited their evidence, and had survived an attempt to disprove them — the ordering is visible, the evidence sits on every row, and the count it opened with was repeated in the live region directly beneath it. It printed on every report and told a reader nothing. The closing caveat now carries both limits a reader cannot see instead of one: that the set of findings does not converge across runs, and that nothing in the report edits the code.

## 1.1.0 — 2026-08-12

### Added

- Repository runs now audit the architecture they started from. The skill drew candidates and never graded the system already in front of it, so a codebase that had come apart from its recorded design got redrawn rather than examined. A new step compares the implemented architecture against the intended one — the recorded design and the accepted ADRs — and reports where the two have separated. Greenfield runs skip it; there is nothing implemented to audit.
- Findings have to survive being disproved. A model is an unreliable detector of architectural problems and a reliable disprover of them, so candidates are generated cheaply per category, put through gates that check whether the repository actually does the thing and whether anyone still touches it, then handed to verifiers that see the claim but never the argument behind it. Deletion is reserved for the two verdicts that make a finding factually wrong; the two that are judgement calls demote and print their objection instead, because a wrong deletion is invisible and a wrong demotion is not.
- `design.json` gains a `debt` register. `status`, `justification`, `acceptedUntil`, `firstSeen`, and `aliases` are carried forward across runs, so a finding you have accepted stays accepted; everything else is regenerated. A finding's identity is its pattern and its components and nothing else — prose is rewritten every run, and a line number moves for reasons that have nothing to do with whether it is the same finding.
- A `#debt` tab, present only when a design carries findings. Findings group by category and sort by severity then confidence, each a native disclosure whose collapsed row carries everything worth searching for. Filtering hides rows that already exist rather than rebuilding the list, so an expanded finding stays expanded, and group counts relabel to `k of N` while a filter is applied. Accepted findings and ones no longer present stay on the page in their own sections.
- The report prints. There was no print stylesheet at all, so a printed report contained whichever tab happened to be open, with every collapsed row still collapsed. Every panel and every disclosure now opens for print, and severity is a bordered text chip rather than a filled badge — browsers drop backgrounds when printing, and colour alone carries no meaning to a reader who cannot see it.

### Fixed

- Any in-page anchor threw the reader to the overview tab and scrolled to the top. The router read the whole hash as a tab name, so `#anything-else` fell through to the fallback. The tab is now the part before the first slash, and the remainder selects and opens a finding.
- The arrow keys were guarded only against text inputs, so moving between buttons on a non-architecture tab flung the reader into the architecture carousel.
- `label-occlusions` has been asserted by the browser test since 1.0.1, but `SKILL.md` and `HTML-REPORT.md` both still told a run to check four diagnostics. The documented `DESIGN.md` section order was also missing `Database schemas`, and the version invariant named two files where the contract test enforces three.

## 1.0.2 — 2026-07-31

### Changed

- The renderer opens the report itself as soon as it is written, so a finished run always ends with the report on screen. Opening was previously a separate instruction a run could skip, which left the artifact on disk for nobody to look at. `--no-open`, or `SYSTEM_DESIGN_NO_OPEN=1`, suppresses it for scripted and headless runs; a failure to open is reported and never fatal, since the file is already written.

## 1.0.1 — 2026-07-31

### Fixed

- The final step lost its own commands. The render path and the open command lived in `HTML-REPORT.md` while the step that needed them lived in `SKILL.md`, so a run that did not re-read the former wrote `design.json` and `DESIGN.md` and stopped without producing a report. Step 8 now carries a runnable block, defines the skill directory where it is used, and states that a design without a report is an unfinished run.
- The post-render check reported a parse failure that had not happened. The report title is set at run time, so the static file keeps the template placeholder; the check now reads the embedded payload instead.
- Edge labels were painted before the components and could be covered by them, and were placed with no collision test. Labels now paint last, and placement searches every segment of a route before escalating perpendicular until the label is clear of components and of other labels.
- Dragging the canvas started a native text selection that highlighted the diagram, the legend, and the sidebar. Panning now suppresses the default, and the page-level guard applies only while a pan is in flight.

### Changed

- The canonical example is a high-demand ticket on-sale: three candidate architectures, seven database schemas, and estimate rows that each reproduce.
- The browser test asserts against whatever design it is given. Component ids, schema field names, and interface contract values were literal strings from the previous example, so no other design could pass.
- New `label-occlusions` diagnostic, asserted at zero alongside the existing four.

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
