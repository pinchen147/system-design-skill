# Harness lessons applied to system design

Research date: 2026-10-21. Scope: an installable skill used by an existing coding agent, with bundled local tools. This is not a hosted agent service or an autonomous model runner.

## Evidence and boundaries

| Source | Lesson carried forward | Limit |
|---|---|---|
| [REA router and tool contracts](https://github.com/morluto/rea/blob/705058f3e2df82503f1c601fc464aea7cbb626b8/docs/tool-design.md) | Small routing instructions, narrow operations, retained evidence, explicit unknowns, useful error recovery | Its reverse-engineering tools are not needed for ordinary repository architecture analysis |
| [REA reconstruction coverage](https://github.com/morluto/rea/blob/705058f3e2df82503f1c601fc464aea7cbb626b8/docs/reconstruction-coverage.md) | Evidence identity and sufficient proof are different; absent coverage cannot become a pass | A digest proves which bytes were read, not whether an architectural claim is true |
| [Local REA reference revision](https://github.com/morluto/rea/tree/a2d8b94dd50dab8d966239dd63ab84718aa8b4b4) | Diagnose the observed blocker, repair supported failures, then resume the original task | Local skill v41 differs from reviewed upstream v44; the stated v6.8 plans are roadmap context, not shipped guarantees |
| [Claude Code loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) | Distinguish intermediate messages, observed tool requests, and terminal results | Routing success does not prove the skill completed its task |
| [Hermes session storage](https://github.com/NousResearch/hermes-agent/blob/c93b7ec54c6886a3806a58e8a6e13724f3bd83ca/website/docs/developer-guide/session-storage.md) | Durable canonical state supports multiple context views and resumable work | This skill uses tracked JSON by product choice, not Hermes's storage stack |
| [MUSE](https://arxiv.org/html/2606.03005v1) | Separate structured representation, parsing, verification, and repair | Task-specific simulators and annotations do not validate open-ended architectural judgments |
| [Agent evaluation guidance](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | Retain trials and judge observable outcomes with criteria matched to the task | A passing test count is not a general reliability or quality guarantee |

The earlier REA reading used [rea-agents-6.5.0](https://github.com/morluto/rea/tree/3b79af28e80785afce9f5998d8f03289402a1847). Pinning these revisions prevents later behavior from being silently attributed to the earlier research.

## Generation, selection, and delivery are separate

The Looksmith experiments motivating this work produced owner-approved candidates that the controller rejected, and selected other candidates the owner disliked. Later owner feedback also made the original “evaluation pending” summary stale. These are local project observations, not a public benchmark or evidence that a particular architectural reviewer is accurate.

Transfer the failure shape: retain candidate evidence, the actual recommendation, the checks used to select it, and the delivered artifact separately. A valid report does not establish a valid design. A model's self-rating is not an independent measurement. A newer unresolved observation must remain visible beside an older conclusion.

## Missing evidence is not refutation

The previous audit protocol told a verifier to report a finding refuted when it could not decide. Its deletion rules could then discard the finding. That loses the difference between disproving a claim and failing to inspect it. The report renderer compounded this by rendering a missing or null `refuted` field as “survived.”

Use three states for verification: refuted, survived a stated check, or unknown. Unresolved claims need the missing source, the affected question, and the next useful probe. They must neither become confirmed findings nor disappear as resolved debt. Repeated model agreement still needs calibration against independently checked cases.

[SmellBench](https://arxiv.org/html/2605.07001v2) supports a narrow claim about refuting detected smells under its tested conditions. Its strongest agreement result excludes ambiguous cases; it does not establish that models reliably disprove every architectural problem. The [framing study](https://arxiv.org/html/2607.10411v1) motivates neutral evidence-led prompts, not a policy that uncertainty means false.

## Durable records should make recovery cheap

The shared source remains `design.json`. An additive investigation register holds evidence, requested questions, unknowns, and checks. The bundled CLI records scoped source hashes, detects stale writes, preserves JSON checkpoints, and reports concrete recovery actions. The coding agent still chooses what to investigate and evaluates the meaning of the evidence.

Atomic replacement and concurrency checks protect local writes. They do not replace review of Git merge conflicts between separately edited clones. A recovered checkpoint restores recorded state; freshness checks and outstanding uncertainty still apply. Re-reading or re-rendering retained work should not require repeating expensive investigation.

## Test the boundary that failed

The invocation evaluator accepted intermediate assistant text followed by a terminal error as valid non-invocation. It could also exclude failed trials from the denominator, allowing one valid trial and two errors to pass a three-trial gate. Stopped runs reported missing costs as zero.

The release policy is explicit: invalid trials block the gate, every retained attempt remains distinguishable, unknown cost is unknown, and no automatic retry silently selects favorable samples. Invocation evaluation remains a discovery test. It does not establish recommendation quality, debt recall, or successful report delivery.

## Prefer native, replaceable mechanisms

The repository's own [audit implementation notes](../plans/2026-08-11-architectural-debt-audit.md) preserve reversals from custom disclosure to native details, component grouping to category grouping, and focus-moving filters to stable filtering. Those concrete corrections support testing the user-visible behavior before adding UI machinery.

The runtime is Python standard library shipped with the skill. Reports remain self-contained HTML with native disclosure controls. The host retains model choice, authentication, tool permissions, and reasoning. MCP, provider SDKs, daemons, and autonomous scheduling need a demonstrated requirement before they enter the package.

## Verification claims to keep separate

- Structural validation: supported fields, references, types, and transitions are consistent.
- Evidence freshness: the scoped bytes still match, or the limitation is explicit.
- Semantic review: a stated claim was evaluated by a named method against sufficient evidence.
- Delivery: the actual artifact was written and, when available, inspected in a browser.

No combination of successful schema checks and model agreement warrants a promise of 100% reliability. The useful contract is recoverable work, visible uncertainty, and precise claims about what was checked.
