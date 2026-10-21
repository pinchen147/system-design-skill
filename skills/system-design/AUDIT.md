# Debt audit

The audit protocol [SKILL.md](SKILL.md) runs at **Audit the architecture for debt**, after the recommendation is settled and before anything is rendered. It runs that late because a finding's exposure is measured against the candidate the run recommends, which does not exist until then. Repository mode only: an audit needs an implemented architecture to compare against, and greenfield has none.

The subject is the gap between the architecture that is intended and the architecture that exists. Reusable mechanisms and decision ladders stay in [HEURISTICS.md](HEURISTICS.md); this file owns only what it takes to find, disprove, and record a finding.

**This is a survey, not a rescue.** It reports; it never edits. Every remedy is a proposal for a later session to accept, reject, or schedule, and a repository deep in debt will get real findings without getting a way out of the mud. Say so in the report, so nobody reads a list of findings as a plan of record.

## Contents

- [What counts as debt](#what-counts-as-debt) — the four tests, and what is excluded
- [The pipeline](#the-pipeline) — eight stages, the kill rules, and what runs without a subagent
- [Stage briefs](#stage-briefs) — the input, the output contract, and the framing for each stage
- [Categories and patterns](#categories-and-patterns) — the closed enum, with signatures and disqualifiers
- [Severity](#severity) — derived from two axes, never chosen
- [Suppressions](#suppressions) — the findings that must not be raised
- [Never recommend](#never-recommend) — remedies that are out of bounds whatever the finding
- [Identity and merge](#identity-and-merge) — how a finding survives a re-run
- [Recording the audit](#recording-the-audit) — what is written, including what was not established

## What counts as debt

Debt is a structural choice that makes future change more expensive, where the cost was never written down. It is invisible by nature: a missing feature is a backlog item, a defect is a bug, and neither is debt. The interest is paid when someone touches the code, not while it sits.

A candidate finding is debt only if it passes all four tests. Each is a separate stage in the pipeline, and each is checked by something other than the agent that raised it.

| Test | The question | Fails when |
|---|---|---|
| **Real** | Does the repository actually do this? | The cited file, schema, identifier, or edge does not support the claim |
| **Uncovered** | Has this already been decided? | A settled ADR, a recorded conflict, a stated assumption, or a declared trade-off already accounts for it |
| **Unstated** | Was the cost written down? | The design names the trade-off and accepts it — a trade-off is not debt, an undeclared one is |
| **Live** | Does anyone touch it? | The components carry no changes in the observed history and sit outside the primary flow |

Weight every finding by how often its components actually change, and say when that history was unavailable. Complexity nobody reads and nobody edits costs almost nothing; the same complexity on a path the team works weekly is expensive.

Two exclusions, both tempting. Unexercised flexibility built for a future that never arrived **is** debt — it constrains change without paying for itself. A deliberately simple starting point that says it is one, and names the condition that would force the next step, **is not** — that is a design, and reporting it as debt punishes exactly the discipline the process asks for.

## The pipeline

Models can both invent findings and incorrectly dismiss real ones. Generate candidates, then attempt to refute them against scoped evidence. Separation is a review discipline, not a guarantee of correctness; retain uncertainty and calibrate the judgments against independently checked cases.

Stages pass conclusions, never arguments. A stage that reads the previous stage's reasoning can adopt its assumptions. Each stage restarts from the artifact before it.

| # | Stage | Runs on | Produces |
|---|---|---|---|
| 0 | **Facts** | always | the component graph, edge contracts, the ADR inventory with statuses, per-path change counts, components that change together, the envelope rows, and the ids of every invariant and non-functional target |
| 1 | **Find** | once per category | candidate findings with a pattern, components, evidence, and a claimed consequence and exposure |
| 2 | **Gates** | every candidate | the `real` and `live` verdicts |
| 3 | **Red team** | scaled by provisional severity | one refutation attempt per lens, each with its objection |
| 4 | **Re-derive** | every survivor | severity recomputed from what was verified |
| 5 | **Remedy** | every survivor | the action, its cost, which candidates resolve it, and whether it can be undone |
| 6 | **Merge** | always | the prior run joined in, baseline states set |
| 7 | **Record** | always | the `debt` object, including what could not be established |

Only stages 1 to 3 carry the argument; the rest is reading, a lookup, and bookkeeping. Spend the budget on generating findings per category and then trying to destroy them.

**Provisional severity gates depth, verified severity is what ships.** The consequence and exposure a finder claims give a provisional severity by the same lookup the verified one uses, and that provisional value decides how many lenses stage 3 spends. Stage 4 then recomputes severity from what survived. A claim that asserts `blocking` earns both lenses and may still end up `low`.

### Kill rules

| Verdict | Effect | Why |
|---|---|---|
| **Real** refuted | Delete | The claim is untrue; there is nothing to weigh |
| **Uncovered** refuted | Delete | A recorded decision makes this a decision, not debt |
| **Unstated** refuted | Drop `confidence` one level, and the objection becomes the finding's disconfirming line | Whether a trade-off is adequately stated is a judgement, and a wrong deletion is invisible |
| **Live** refuted | Set `exposure` to `off-path` | Change history is a proxy, so this lowers the finding rather than removing it — and an untouched component on the primary flow can still break |

**Unknown is a separate outcome.** When a check cannot decide, set `gates.real` or `gates.live` to `"unknown"` for a gate, or a lens’s `refuted` to `null`. In `debt.unverified`, put the candidate id and check name in `check`, and the missing evidence plus next probe in `reason`, so the report exposes both. Unknown Real or Uncovered checks defer a new candidate; they do not confirm it or delete it as false. If Live cannot establish either exposure value, defer a new candidate rather than inventing an axis for the severity lookup. For a prior finding, retain its exposure as historical, mark verification unknown, and explain that the old severity was not re-established. Only explicit `refuted: false` counts toward survived refutation attempts. A missing legacy verdict means not established.

Deletion is silent, survival is visible: reserve it for the two verdicts that make a finding factually wrong, and let the reader adjudicate the rest.

`severity` has exactly one source — the lookup in [Severity](#severity) — so a lens that lowers a finding moves an **input** instead: *Live* moves `exposure`, *Unstated* moves `confidence`, which the lookup never reads. Stage 4 re-derives from whatever the lenses left, so a reader who disagrees is arguing with an axis rather than a verdict that appeared from nowhere.

### Tools

Use whatever verification a harness offers — repository search, documentation lookup, a verification tool — at your discretion, and record which ones actually ran. **The audit completes when none of them exist.** A finding verified only against the repository is still a finding: it carries lower confidence, names the check it could not make, and ships.

Network lookup is confined to `obsolescence`, the one category a repository cannot answer for itself: whether a dependency is abandoned, whether a version is superseded, whether a technique has a known failure the repository has not met yet. Every other category is decided from the repository and its history. Send a package name, a version, or a technique name; never the design, the topology, or the code. Where the harness has no network, `obsolescence` findings carry low confidence and say which lookup was unavailable.

### Without a subagent

The stages are the contract; delegating them is an optimisation. Where a subagent primitive exists, run stage 1 as one agent per category and stage 3 as one agent per lens, and merge. Where it does not, run the same stages inline as separate passes, restating the brief and discarding the prior stage's reasoning at each boundary. Finding and judging stay in separate passes either way.

## Stage briefs

The framing each stage runs under is load-bearing: a verification prompt that opens by describing the design as careful or reviewed suppresses the very findings it was asked for.

**Stage 0 — Facts.** Collect without judging. The component graph and every edge with its declared contract; every ADR with its status and the structures it decided; change counts per path over the observed window; pairs of paths that change in the same commit; the estimate rows; and the identifier of every invariant and non-functional target so later stages can cite them. Record the window and any part of the history that was unavailable. Emit no verdicts — a fact block containing an opinion contaminates every stage after it.

**Stage 1 — Find.** One pass per category, reading the facts and this file's patterns. Do not read the prior run's findings: a finder primed with last week's list reproduces it and discovers nothing. Emit candidates only; prose is rewritten later, so spend the effort on the evidence.

```jsonc
{ "pattern": "shared-persistence", "components": ["billing-svc", "orders-db"],
  "evidence": [ { "text": "both services map the orders table as authoritative",
                  "source": "billing/models.py; fulfilment/schema.sql" } ],
  "claimedConsequence": "breaking",   // breaking | friction
  "claimedExposure": "on-path" }      // on-path | off-path
```

**Stage 2 — Gates.** Cheap, mechanical, and run on every candidate without exception. *Real*: open what the evidence cites and confirm it says what the finding claims. *Live*: look up the change counts for the cited components. These two catch the errors that cost the least to find and the most to publish.

**Stage 3 — Red team.** One agent per lens, each seeing the facts and the claim but not the finder's argument. Each is asked to **test a refutation** of the finding against the facts. Return `refuted: true` only with evidence contradicting the claim, `false` when the stated check supports survival, and `null` when the available evidence cannot decide. Give the missing source and next probe for an unknown result; do not convert it into a deletion or a survived check. `blocking` and `high` candidates get *Uncovered* and *Unstated* as separate agents. `medium` and `low` get one combined pass.

```jsonc
{ "lens": "uncovered", "refuted": false,
  "objection": "ADR-0004 records the shared table but only for reads; writes were never decided",
  "confidence": "high" }
```

**Stage 4 — Re-derive.** Recompute consequence and exposure from what the gates and lenses established, not from what stage 1 claimed, then look up severity. A finding whose `breaking` claim rested on evidence the *Real* gate softened is no longer breaking.

**Stage 5 — Remedy.** A fresh author who has not seen stages 1 through 3. It receives a confirmed problem, the facts, and the [Never recommend](#never-recommend) list, and it is not defending anything. Give the action, what it costs, which candidates already resolve it, and whether it can be undone once shipped.

**Stage 6 — Merge.** [Identity and merge](#identity-and-merge).

**Stage 7 — Record.** [Recording the audit](#recording-the-audit).

## Categories and patterns

Seven categories, closed. The category is the grouping axis, in the artifact and in the report; the pattern is the rule. Components are carried on every finding and drive filtering, not grouping — a finding names as many components as it spans, so grouping by component would either duplicate it or force an arbitrary choice of one. Where a finding genuinely affects several characteristics, name one category and list the rest under `affects` using the ratings axes in [HTML-REPORT.md](HTML-REPORT.md#designjson-schema) — forcing a multi-quality problem into a single bucket loses the part that was not chosen, and loses it silently.

Every pattern carries a **Not when** clause. Without one a signature gets matched against a system it does not fit, and the audit spends its credibility on a design that was right.

### boundaries — where responsibility is drawn

| Pattern | Signature | Remedy | Not when |
|---|---|---|---|
| `wrong-cuts` | Components split by technical layer rather than capability; one product flow crosses every component | Re-cut along the flow | The layers are separate deployment units with genuinely different scaling or trust needs |
| `feature-concentration` | One component protects more than one invariant, or its own description needs "and" to state its job | Split by protected invariant | The concerns share more state than they own, so splitting distributes a transaction |
| `scattered-functionality` | The same rule is implemented at two or more hops of one flow, or named in two components' notes | Consolidate to one owner | The repetition is a deliberate isolation boundary with a stated reason |
| `temporal-decomposition` | Component names track pipeline stages, and consecutive stages both parse the same format | Merge the stages that share the format knowledge | The stages scale independently and the format between them is a published contract |
| `pass-through-component` | Almost every edge forwards, and the contract is near-identical to the downstream's | Expose the downstream, redistribute the work, or merge | It terminates a trust boundary, or it dispatches among two or more implementations |
| `shallow-component` | The interface is a one-to-one projection of the store behind it | Deepen it, or fold it into its caller | It is a deliberate insulating layer over a contract you do not control |

### data-ownership — who may write, and who decides the order

| Pattern | Signature | Remedy | Not when |
|---|---|---|---|
| `two-writers` | Two or more components write one entity and no ordering authority is named | Name one authority, or prove the writes commute | The writes are to disjoint fields with an entity-level merge already stated |
| `shared-persistence` | Two or more components treat the same table or collection as authoritative | One owner; the others read a derived view or call the owner | One is a read-only consumer and its read path is declared |
| `dual-write` | A flow writes two stores in sequence with no outbox, change log, or compensation | Tail the authority's change log, or write an outbox row in the effect's transaction | The second write is a cache whose staleness bound is stated |
| `derived-without-source` | A component marked derived names no reconstruction input | Name the authoritative source, or reclassify it as authoritative | It starts empty and repopulates on demand, and the cold-start cost is stated |
| `derived-without-cursor` | A derived component names a source but no durable position | Record the cursor that proves how far the source has been applied | The view is rebuilt whole on every refresh and the rebuild cost is stated |
| `unstated-conflict-resolution` | An entity reachable by concurrent writers with no per-field-class resolution, or whole-entity last-write-wins beside a claim that no write is lost | Apply the conflict-resolution ladder in [HEURISTICS.md](HEURISTICS.md#replication-and-consistency), and name what the chosen rule discards | Writes for one entity are routed to a single home and the routing is enforced |

### coupling — what cannot move without something else moving

| Pattern | Signature | Remedy | Not when |
|---|---|---|---|
| `dependency-cycle` | A directed cycle in the component graph | Break it with an interface, an event, or a merge | The cycle is inside one deployment unit and one team's ownership |
| `hub-like-dependency` | One component's inbound plus outbound degree stands far above the graph's median | Split by consumer group, or invert the direction | It is a gateway or a bus whose whole purpose is fan-in |
| `unstable-dependency` | A component depends on one that is more volatile than itself | Invert through an interface the stable side owns | The volatile side is a vendor boundary already wrapped |
| `information-leakage` | One decision — a wire format, a partition key, a retry policy, a token shape — is encoded in two or more components | Merge the components, or extract the decision behind an interface that hides it | Extracting it would replace a hidden dependency with an equally wide public one |
| `distributed-monolith` | Components that change in the same commit repeatedly and cannot deploy independently | Merge them, or make the seam asynchronous | They are versioned and released together on purpose, and that is recorded |
| `special-general-mixture` | A shared, common, or platform component whose code, schema, or configuration names one specific consumer | Pull the specific part up into that consumer | The consumer is the only one and the component is not shared in fact |

### dependency-contracts — what each caller is owed

| Pattern | Signature | Remedy | Not when |
|---|---|---|---|
| `no-deadline` | An edge crossing a process boundary with no completion budget, in the artifact or in the code | Assign a deadline inside the caller's remaining budget | The call is in-process and cannot block on a network |
| `no-retry-owner` | No layer owns the retry, or two layers both retry the same call | Name exactly one owner, with capped backoff and jitter | The operation is not safely retryable and says so |
| `unbounded-backlog` | A queue, stream, pool, or edge with no bound on the work that can accumulate | State the bound and what happens at saturation: block, shed, or spill | The producer is rate-limited upstream and that limit is stated |
| `unbounded-result-set` | An interface returning a collection with no caller-specified limit | Put the limit in the protocol, and paginate with a stable cursor | The result is provably bounded by the domain, and the bound is stated |
| `unstated-idempotency` | A retryable operation with no key, or a key whose scope and retention are unstated | Scope the key to caller and operation, and state its retention | The operation is naturally idempotent and that is stated |
| `unstated-compatibility` | A schema or wire change with no compatibility direction and no deploy order | State the direction from the deploy order, and put the check in the build | Reader and writer ship as one unit and can never skew |

### failure-containment — what stops one failure becoming all of them

| Pattern | Signature | Remedy | Not when |
|---|---|---|---|
| `unbalanced-capacity` | A synchronous edge whose caller concurrency materially exceeds what the callee can serve, with no breaker, handshake, or bulkhead | Add the protection; do not equalise the capacity | The callee sheds load explicitly and the caller handles the rejection |
| `no-bulkhead` | One pool, fleet, or queue serves callers of different criticality | Partition by caller or by capability, and accept the lower utilisation | Every caller shares one criticality and one failure consequence |
| `sla-inversion` | An availability target above what the product of its synchronous dependencies can support | Decouple, degrade, or lower the target to what the dependencies allow | The dependency is on a path that degrades rather than fails |
| `no-steady-state` | Something accumulates — logs, sessions, tombstones, rows, cache entries — with no named reclamation | Name the reclaiming mechanism and prove it keeps up | The accumulation is bounded by a stated retention that is enforced |
| `acknowledgement-before-durability` | The acknowledgement point precedes the durability the recovery target promises | Move the acknowledgement, or restate the promise | The loss window is stated and accepted |
| `untested-recovery` | An authoritative store with recovery targets and no evidence any restore has been exercised | Run a timed restore and record what it achieved | The store is derived and its rebuild path runs routinely |
| `unfenced-ownership` | A leader or lease with no epoch that the resource itself validates | Add a monotonic token and check it at the resource | Ownership never moves, and the design says what happens when the owner dies |

### over-engineering — machinery that outruns its evidence

| Pattern | Signature | Remedy | Not when |
|---|---|---|---|
| `machinery-outruns-envelope` | A mechanism whose anti-gate the measured envelope does not clear | Remove it and name the number that would bring it back | The envelope is projected rather than measured, and the projection is stated |
| `gold-plating` | Extension points, configuration, or generality with no consumer exercising them | Delete the unused path; make the thing replaceable instead of extensible | A second consumer is committed and dated |
| `unjustified-distribution` | Components split with no differing characteristic, no independent scaling, and no separate failure domain | Merge them | The split follows a team or trust boundary that is real |
| `cargo-culted-architecture` | A pattern present with no chain to a number, an invariant, or a named failure mode | Remove it, or supply the chain | The pattern is the conventional baseline and the deviation would need the argument |
| `unexercised-abstraction` | An interface with exactly one implementation and no second named | Inline it | It exists to make an untestable dependency testable, and that is stated |

### obsolescence — decisions the world moved past

| Pattern | Signature | Remedy | Not when |
|---|---|---|---|
| `technological-gap` | A choice that was correct when made and that context has since invalidated | Restate the decision against today's constraints | The original constraint still holds |
| `superseded-decision-still-implemented` | An ADR marked superseded whose structure is still in the code | Finish the migration, or un-supersede the ADR | The migration is in flight with a recorded end date |
| `stale-reference-model` | The design or an ADR describes something the code has deliberately and correctly moved past | **Update the document.** The finding is against the reference model, not the system | The code is wrong and the document is right — then it is a different finding |
| `abandoned-component` | A component with no inbound edges and no external trigger | Remove it | It is invoked out of band — by an operator, a schedule, or a disaster path — and that is recorded |

`stale-reference-model` is the finding an audit is most likely to get backwards. The intended architecture is what the team currently wants, not what it wrote on day one. When the implementation has moved on for good reasons and nobody updated the design, the debt is in the document — and raising that as a violation punishes correct work.

## Severity

Severity is looked up from two axes and never chosen directly. Store both axes with the finding: a reader who disagrees should be arguing with an input, not with a verdict.

**Consequence** — `breaking` when the finding violates a named invariant, misses a named non-functional target, or creates a loss or corruption path that cannot be recovered. `friction` when it costs effort, coupling, or risk but nothing stated is currently violated.

**Exposure** — `on-path` when the components sit on the primary flow, inside something the recommended candidate changes, or in a zone the migration touches. `off-path` otherwise.

| | on-path | off-path |
|---|---|---|
| **breaking** | `blocking` — fix with this change | `high` — schedule it |
| **friction** | `medium` — fix while you are in there | `low` — record only |

`note` is not a severity. It is an observation with no remedy, and it carries none of the four verdicts; severity belongs only to findings that assert something is wrong.

Rules that keep the scale honest:

- `blocking` must cite the specific invariant or non-functional target it violates, by id. A finding that cannot name one is not blocking, whatever it feels like.
- Confidence is shown beside severity and never folded into it. A `blocking` finding held with low confidence sorts below a `blocking` one held with high.
- Do not add a fifth level. Two axes give four cells; a fifth level would have no rule behind it.
- Say in the report what this scale does and does not do: four cells buy agreement and cheap communication at the cost of resolution, and they do not rank-order the findings inside a cell.

## Suppressions

Patterns that look like debt and are not. Check them before emitting, and again in the *Unstated* lens.

**About repetition and duplication.** Identical code is not duplicated knowledge — two rules that happen to coincide today and would change for different reasons tomorrow are correctly separate. Deliberate near-duplication can encode a different intent. Duplication against an external contract you do not control is unavoidable; report it as something to mitigate, never to eliminate. A cached derived value is only a finding when the duplication escapes its module. Where decoupling is the stated goal, duplication is the intended trade and not a defect.

**About simplicity.** A single node, a single store, a synchronous call, a monolith, or a hand-rolled queue is not debt. A design that starts simple, says it is starting simple, and names the condition that forces the next step is complete. Silence is the defect, not simplicity. The scaling substrate in [HEURISTICS.md](HEURISTICS.md#scaling-substrate) is a sequence of triggers, and a rung not yet taken is only debt once its trigger has fired.

**About distributed mechanisms.** Absence of Byzantine tolerance is not debt outside an adversarial or untrusted-tenant deployment. Eventual consistency is not debt; an unstated conflict-resolution rule is. Whole-entity last-write-wins is a legitimate choice unless the design also claims no acknowledged write is lost. A single leader is a simplification, not a smell. Manual failover can be correct. Never assert that one storage engine amplifies writes more than another — flag a missing amplification story instead.

**About judgement calls already made.** A missing component paired with a stated reason is a decision. A trade-off the design names and accepts is a decision. Sophisticated machinery is not over-engineering when the stated targets demand it — gate every over-engineering finding on the declared targets, never on component count. Deviating from what a well-known company published is not a finding. When the design states no non-functional targets at all, the finding is that the targets are missing, not that a component is wrong.

**About the code's own kind.** Prototype and spike code is meant to be incomplete; classify what kind of code a path is before judging it. Generated code, vendored code, and fixtures are out of scope. A component with no changes in the observed window carries near-zero debt whatever its shape.

**About the audit's own reflexes.** Never score a design by how many patterns it contains — the count of mechanisms present is not a quality measure, in either direction. Never raise both a layering violation and a missing transactional guarantee on the same edge without naming the trade-off between them, because relieving one worsens the other. Never demand numbers a design at this stage cannot have.

## Never recommend

Bounds on the remedy, whatever the finding.

- **A rewrite.** Remedies are incremental. Where the work genuinely exceeds a refactor, say so, size it, and put it on a schedule with the affected consumers named — that is a different artefact from a cleanup.
- **Asynchronous middleware as a routine fix.** It is expensive, close to irreversible, and frequently not the team's choice to make. Recommend it only as a deep dive with its costs stated: the data synchronisation, the failure modes, and what the team must now operate.
- **A restructure into untested code**, unless the first item of the remedy is the coverage that makes it safe.
- **Splitting a component** without paying the four costs of the split: the new component, its new interface, the coordination between the parts, and whatever gets duplicated across the seam.
- **An abstraction layer for a future you are guessing at.** Where the future is unknown the answer is replaceability, not extensibility.
- **An optimisation with no measurement behind it.** And where complexity was added for performance and no measurement supports it, that complexity is itself the finding.

Every `replace` recommendation states the cost it assumes rather than leaving it implied. Every remedy that cannot be undone once shipped says so.

## Identity and merge

A finding must survive a re-run. Prose will be rewritten every time and must not move the identity.

```
id = "dbt-" + pattern + "--" + sorted(componentIds).join("-")
```

Nothing else contributes: line numbers, paths, array position, timestamps and prose hashes all move for reasons unrelated to whether it is the same finding. Component ids are already stable across every architecture in the file, which makes them the one identifier here a rename cannot break.

Record the ingredients alongside the id, so a later run can match on something better without re-deriving them from prose:

```jsonc
"identity": { "scheme": "pattern+components/v1", "pattern": "shared-persistence",
              "components": ["billing-svc", "orders-db"] }
```

Version the scheme and keep `aliases` per finding. When the scheme changes, match old records by their recorded identity and write the superseded id into `aliases`; a design document written months ago still resolves. Two findings that collide on pattern and components are the same finding — merge them. Never disambiguate with a counter: that reintroduces the positional identity the scheme exists to avoid. A genuine need to split means the pattern is too coarse and needs a new member.

The merge, in order:

1. Read the prior `design.json` and index every finding by its id **and** every alias.
2. Run stage 1 without showing it that index.
3. Join this run's findings to the prior ones.
4. Set `baselineState`: `unchanged` when nothing material moved, `updated` when severity, components, or remedy changed, `new` when unmatched, `absent` for a prior finding with no match after the relevant checks completed. If unavailable or stale evidence prevented those checks, retain the prior finding and its human decisions, mark `baselineState: updated`, set affected verification to unknown, and link an unverified check. Do not label missing coverage as disappearance.
5. Carry forward, never regenerate: `status`, `justification`, `acceptedUntil`, `firstSeen`, `aliases`. These record human decisions, and a re-run must never silently reopen an accepted finding.
6. Regenerate freely: title, consequence prose, remedy text, evidence, blast radius, disconfirming line.
7. Keep `absent` findings for one further run, shown in a collapsed section. A finding that disappeared is at least as likely to have been missed as fixed, and one run of visibility lets a human decide which. Drop them after that.
8. On the first run, omit `baselineState` from every finding rather than marking them all new — it is present on all findings or on none.

## Recording the audit

Write the `debt` object into `design.json` before rendering; the schema is in [HTML-REPORT.md](HTML-REPORT.md). It is the debt register, and it is the only place an acceptance can persist.

Three things belong there beyond the findings themselves.

**What was examined.** `checked` lists every category the audit ran. A category that produced nothing reads as examined within recorded coverage, not proven clean or omitted — without it, silence is ambiguous and the reader has to assume the worst.

**What could not be established.** Every check that wanted evidence the run could not reach: history outside the observed window, a component with no readable source, an ADR that points somewhere unavailable, a claim that needed a tool the harness does not have. Record it as an unverified check, not as a finding and not as nothing.

**How each finding was verified.** Which gates ran and their verdicts, each lens with its objection and whether it refuted, which tools were actually available, and how many completed refutation attempts the finding survived. Unknown and missing verdicts never count as survived. A finding that beat two adversaries and one that faced none are different claims, and a reader who cannot tell them apart has to treat all of them as the weaker kind.

The disconfirming line is the strongest objection the red team actually raised and the finding survived. It is not a self-authored counterargument: the agent that raised a finding writes a weak case against it, and a weak case against it is worse than none.

State the audit's own limits in the report, in its own voice. Two of them, both load-bearing:

**A finding that reappears is matched reliably. The set itself is not stable.** Run twice, get a different list — the identity scheme fixes what happens to a finding that returns, and promises nothing about which findings return. A report that claims completeness it does not have costs more than the findings are worth.

**This does not converge, and it is not meant to be looped.** A pass is a list of leads. Acting on the ones with a citation behind them and stopping is the intended use; running it repeatedly until it comes back clean is not, because it will not. Where a run genuinely found little, the severities say so — a page of `low` is the audit reporting a quiet system in the only way it has.
