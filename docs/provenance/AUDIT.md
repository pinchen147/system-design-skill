# Provenance — AUDIT.md

Checked 2026-08-11.

Two conventions specific to this file. **Where a book originates a term, the book is the primary
source** and is cited as one; everywhere a number, threshold, or correctness claim appears, a paper,
specification, or first-party document carries it. And **edition matters more here than elsewhere** —
several of the works below differ enough between editions that a bare title is not a citation. Where
that is true the row says which edition was read.

## What counts as debt

| Claim | Source |
|---|---|
| Divergence caused by *insensitivity* is drift; divergence caused by *violation* is erosion; drift precedes and enables erosion | Perry & Wolf, *Foundations for the Study of Software Architecture*, ACM SIGSOFT SEN 17(4) 1992 · https://users.ece.utexas.edu/~perry/work/papers/swa-sen.pdf · doi:10.1145/141874.141884 |
| The reference model is the **currently desired** architecture, not the initially documented one — hence `stale-reference-model` | Li, Liang, Soliman & Avgeriou, *Understanding software architecture erosion*, JSEP 2022 · https://arxiv.org/abs/2112.10934 |
| Debt is limited to the *invisible* elements; new features and defects are excluded. Architectural debt is the invisible/evolvability quadrant | Kruchten, Nord & Ozkaya, *Technical Debt: From Metaphor to Theory and Practice*, IEEE Software 29(6) 2012 · https://www.sei.cmu.edu/documents/360/2012_019_001_58818.pdf |
| Unexploited flexibility is debt — "making the system more flexible and adaptable than it actually needs to be… if this added flexibility hinders future development without actually being exploited" | ibid. |
| The metaphor is a mismatch between the program and the team's current understanding, not "bad code written deliberately" | Cunningham, OOPSLA '92 experience report · http://c2.com/doc/oopsla92.html · and the 2009 correction, https://cmdev.com/papers/debt-metaphor/ |
| Interest is triggered by touching the code, not by elapsed time | Fowler, *TechnicalDebt* · https://martinfowler.com/bliki/TechnicalDebt.html |
| Complexity is weighted by the fraction of developer time spent in each part; complexity that is never touched costs almost nothing | Ousterhout, *A Philosophy of Software Design*, 1st ed. 2018, §2.1 p.6 |
| Change history predicts fault-proneness better than product metrics — "the number of times code has been changed is a better indication of how many faults it will contain than is its length" | Graves, Karr, Marron & Siy, IEEE TSE 26(7) 2000 · https://cs.uwaterloo.ca/~m2nagapp/courses/CS846/1171/papers/graves_tse98.pdf |
| The debt is the *unstated* trade-off, not the trade-off — "we should be very conscious of when we are cutting corners" | Kleppmann, *Designing Data-Intensive Applications*, **2015 Early Release**, Ch1 p.18 |
| A naive design that declares itself a starting point is correct; the silent one is debt | Xu, *System Design Interview*, **Volume 1**, p.185, p.124, p.203, p.205 |

**Rejected.** "Spend 10–20% of development time on investments." Ousterhout labels Figure 3.1
qualitative and writes that he is "not aware of any empirical measurements of the precise shapes of
the curves" (§3.3 p.16). The framing is usable; the number is not a measurement.

**Rejected.** "42% of developer time is wasted on technical debt." Traced to Stripe/Harris,
*The Developer Coefficient* (https://stripe.com/files/reports/the-developer-coefficient.pdf), which
never prints the figure — it is 17.3/41.1 hours of *maintenance*, a question whose stem includes
"modifying" code. Stripe's actual technical-debt question yields 33%. No sampling frame, response
rate, or margin of error is published. The defensible figure is 23%, from a seven-week diary study of
43 developers: Besker, Martini & Bosch, TechDebt '18 · doi:10.1145/3194164.3194178.

**Rejected.** CISQ's $2.41T / $1.52T and CAST's "$3.61 per line of code." CISQ projects forward from a
prior estimate by inflation, states it assumed no growth elsewhere, contradicts its own baseline
between Chapter 2 and Appendix B, is vendor-sponsored, and takes its debt-effort input from the same
Stripe survey above.

## The pipeline

| Claim | Source |
|---|---|
| In the studied Python project, 63.1% of PyExamine detections were expert-judged false positives; this is not a measured false-positive rate for model-generated architectural findings | *SmellBench*, Dinu, Mihăescu & Rebedea · https://arxiv.org/abs/2605.07001 · **preprint** |
| Refutation agreement reached κ 0.94 on 52 unambiguous cases; 13 ambiguous cases were excluded, and another tested agent wrongly dismissed genuine smells. No universal reliability claim follows | ibid. |
| Framing changed judgments in the tested model/smell cells; zero recall occurred in particular cells. Evidence-guided prompting helped some conditions, but Table 3 includes flip rates above the narrative 12–26% range | https://arxiv.org/html/2607.10411 · **preprint** |
| Temperature 0 is not deterministic — 4 models × 70 commits × 5 identical runs with cleared context still varied | https://arxiv.org/html/2502.20747 |
| LLMs score F1 < 0.40 on genuinely architectural smells while winning on Large Class and Long Method; ground truth from 76 developers over 268 candidates in 30 Java projects | https://arxiv.org/abs/2601.09873 |
| Agent-only code review correlates with worse outcomes: 45.20% merge rate vs 68.37% human-only; agent comments addressed 0.9–19.2% of the time vs ~60% | MSR '26 · https://arxiv.org/abs/2604.03196 · peer-reviewed |
| Conformance to explicit, code-inferable ADR decisions is the one task with >90% measured accuracy — 980 ADRs across 109 repositories; accuracy "falls short for implicit or deployment-oriented decisions" | https://arxiv.org/abs/2602.07609 · **preprint** |
| Comparing a declared high-level model against extracted dependencies yields three verdicts — convergence, divergence, absence | Murphy, Notkin & Sullivan, *Software Reflexion Models*, FSE '95 · https://www.cs.ubc.ca/~murphy/papers/rm/fse95.html · ACM SIGSOFT 2011 Retrospective Impact Paper Award |
| Independent identification before collaborative consensus, one dimension at a time | Ford & Richards, *Fundamentals of Software Architecture*, 1st ed. 2020, Ch.20 (risk storming) |
| Static architecture-compliance tools disagree materially with one another across 34 dependency types | Pruijt et al., *Software: Practice and Experience* 2017 · doi:10.1002/spe.2421 |

**Rejected.** A published effectiveness study for fitness functions. The concept is well specified
(Ford, Parsons & Kua, *Building Evolutionary Architectures*, 2017, Ch.2 — note this is **not** in
*Fundamentals of Software Architecture*, which gives only the definition and worked examples). No
systematic review or controlled study measuring whether teams using them experience less erosion was
found. Cite it as a defined practice, never as an evidence-backed intervention.

**Rejected.** “Models are reliable disprovers” as a universal rule; the cited evidence is task- and sample-specific. “Cannot decide means refuted” does not follow from the framing study and loses the difference between missing evidence and contradiction. The narrative 12–26% range is not a complete range of the table’s results; do not restore it as a universal bound.

## Stage briefs

| Claim | Source |
|---|---|
| The study evaluates a bundled evidence-guided prompting intervention; it does not isolate ordering from content | https://arxiv.org/html/2607.10411 |
| Files that change together reveal coupling invisible to static dependency analysis; validated over 20 releases of a large telecom switching system | Gall, Hajek & Jazayeri, ICSM '98 · https://plg.uwaterloo.ca/~migod/846/papers/gall-coupling.pdf |
| Bug-fix locality is measurable from version control — the number of source files touched per fix | Hunt & Thomas, *The Pragmatic Programmer*, 2nd ed. 2019, Topic 10 |
| Undecidable checks remain unknown; they cannot count as refutations or survived attempts | [REA coverage contract](https://github.com/morluto/rea/blob/705058f3e2df82503f1c601fc464aea7cbb626b8/docs/reconstruction-coverage.md) and local three-state audit policy. This is a correctness boundary, not a measured precision improvement |

## Categories and patterns

| Claim | Source |
|---|---|
| `dependency-cycle`, `hub-like-dependency`, `unstable-dependency`, god component — names and detection rules | Arcan, Arcelli Fontana et al. · https://essere.disco.unimib.it/wiki/arcan/ |
| `feature-concentration` and `scattered-functionality` — a component realising more than one concern, and one concern realised across components | Designite, Sharma et al. · https://www.designite-tools.com/docs/features_cs.html |
| `wrong-cuts` (split by technical layer rather than business capability), `shared-persistence`, `distributed-monolith`, megaservice, nanoservice — with perceived-harm scores from 72 developers | Taibi & Lenarduzzi, IEEE Software 35(3) 2018; expanded taxonomy at https://arxiv.org/pdf/1908.04101 |
| The three erosion symptoms developers actually flag: architectural violation, duplicate functionality, cyclic dependency — 21,274 OpenStack review comments manually classified, 502 erosion-related | Li, Soliman, Liang & Avgeriou · https://arxiv.org/pdf/2201.01184 |
| `information-leakage`, `temporal-decomposition`, `pass-through-component`, `shallow-component`, `special-general-mixture` — signatures and the direction of the fix (special-purpose code moves *up*) | Ousterhout, *A Philosophy of Software Design*, 1st ed. 2018, §5.2 p.31, §5.3 p.32, §7.1 p.46, §4.5 p.25, §9.4–9.5 pp.62–65 |
| A layer must eliminate complexity that would exist without it, or it is not paying for itself | ibid. §7.6 p.53 |
| `abandoned-component` — a component nothing routes to any more is a removal candidate | Netflix Janitor Monkey, as described in Ford & Richards, *Fundamentals of Software Architecture*, 1st ed. 2020, Ch.6 |
| `unbalanced-capacity`, `sla-inversion`, `no-steady-state`, `no-bulkhead`, `unbounded-result-set` | Nygard, *Release It!*, **1st ed. 2007**, §4.8 pp.96–99, §4.10 pp.102–105, §5.4 pp.124–130, §5.3 pp.119–123, §4.11 pp.106–109 |
| An unbounded result set is a handshaking failure — "the caller should always indicate how much of a response it is prepared to accept" | ibid. p.108 |
| A synchronous edge requires both ends to share operational characteristics for the duration of the call | Ford & Richards, ibid. Ch.7 (architecture quantum) |
| `two-writers` — shared mutable state, not mutable state, is the defect; aliasing makes the set of change sites unfindable | Abelson & Sussman, *SICP*, §3.1.3 pp.315–319 |
| Imposing an order on events requires communication between the processes — an ordering claim with no communication cost is unfunded | ibid. §3.4.2 p.428 |
| Merging streams from independent agents reinstates the ordering problem streams were meant to remove | ibid. §3.5.5 p.485 |
| A decomposition is useful when unshared state greatly exceeds shared state — the test behind `feature-concentration`'s *Not when* | ibid. §3.5.5 p.486 n.76 |
| `derived-without-source` / `derived-without-cursor` — derived data is defined by reconstructability, and catch-up requires an exact position in the source's change stream | Kleppmann, *DDIA*, **2015 Early Release**, Part II intro p.110 and Ch4 p.117 |
| `dual-write` — a denormalised copy kept in sync by application code moves complexity into the application | ibid. Ch2 p.42 |
| `acknowledgement-before-durability` — "a write is not guaranteed to be durable, even if it has been confirmed to the client"; and claiming synchronous replication while running asynchronous is "a recipe for problems down the line" | ibid. Ch4 p.116, p.128 |
| A transaction is not committed until the log is forced to its commit record; `fsync` returning success is not proof of durability | Petrov, *Database Internals*, 2019, Ch5 p.90 and p.89 |
| `unfenced-ownership` — a lease holder's operations carry a monotonic sequencer the resource validates | Burrows, *The Chubby Lock Service*, §2.4 · https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/ |
| `unstated-compatibility` — compatibility direction follows deploy order, and the check belongs in the build | https://protobuf.dev/programming-guides/proto3/#updating · https://avro.apache.org/docs/1.12.0/specification/#schema-resolution · https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html |
| `technological-gap` — debt that is "not the result of having made a wrong choice originally, but rather the result of the context's evolution" | Kruchten, Nord & Ozkaya, IEEE Software 29(6) 2012 |
| `superseded-decision-still-implemented` — the superseded status and its lifecycle | Nygard, *Documenting Architecture Decisions*, 2011 · https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions |

**Rejected.** Ranking patterns by an intrinsic severity. Across 31 open-source Java systems the *type*
of architectural smell did not significantly correlate with change frequency, and the effect reversed
in small artifacts — Sas, Avgeriou, Pigazzini & Arcelli Fontana, JSEP 34(1) 2022 ·
https://boa.unimib.it/bitstream/10281/332145/4/10281-332145_VoR.pdf. Severity is derived per instance
from context instead.

**Rejected.** "Vendor King" as an architecture anti-pattern attributed to *Fundamentals of Software
Architecture* — the term does not appear anywhere in that book.

**Rejected.** Any citation of the local *Designing Data-Intensive Applications* PDF for
linearizability, partitioning, transactions, change data capture, or schema compatibility. That file
is the 2015 Early Release, containing Chapters 1–4 only, where Chapter 4 is *Replication*;
"linearizability" and "serializability" do not appear in it at all. Those subjects require the 2017
second edition, whose chapter numbers shift by one from Chapter 4 onward.

**Rejected.** Any citation of the local *Release It!* PDF for Back Pressure, Shed Load, Governor, Let
It Crash, or Little's Law. That file is the 1st edition (2007) and contains none of them; its only
provider-side throttling pattern is Handshaking (§5.6).

**Rejected.** Any citation of the local *System Design Interview* PDF for ad click aggregation,
metrics monitoring, payments, hotel reservation, digital wallet, stock exchange, proximity service,
object storage, distributed message queue, or gaming leaderboard. Despite its filename that file is
Volume 1; those designs are Volume 2.

## Severity

| Claim | Source |
|---|---|
| Severity applies only to actual failures, and the nature of a result is a separate axis from its severity | OASIS SARIF v2.1.0 errata01 §3.27.9–3.27.10 · https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/sarif-v2.1.0-errata01-os-complete.html |
| Numeric priority values are not commensurable between producers — the spec's own caution on `rank` | ibid. §3.27.25 |
| CVSS "was designed to measure the technical severity of a vulnerability but is widely misused as a means of vulnerability prioritization… The scoring algorithm is not well justified and lacks the transparency needed" | CERT/CC, *Towards Improving CVSS*, 2018 · https://www.sei.cmu.edu/documents/574/2018_019_001_538372.pdf |
| The same scorers gave different severity ratings to the same vulnerabilities 68% of the time, and the inconsistency tracked properties of the scale rather than of the evaluators | Wunder et al., n=196 with a 59-person follow-up · https://arxiv.org/html/2308.15259 |
| Finer granularity did not buy discrimination: across 11,012 CVEs the top 2 scores accounted for 41.2% and the top 10 for 83.8%; only 51 of 75 possible scores were ever observed | Scarfone & Mell, ESEM '09 · https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=903020 |
| The categorical replacement built by the same institution emits four outcomes, each carrying a written action rather than a number | SSVC · https://certcc.github.io/SSVC/reference/decision_points/outcomes/ |
| Severity criteria should carry the action, not only the label | Deque axe-core impact definitions · https://raw.githubusercontent.com/dequelabs/axe-core/develop/doc/issue_impact.md |
| Exposure as an axis: debt in code nobody touches may be neither urgent nor impactful, and fixing it can be wasteful | CodeScene · https://codescene.io/docs/guides/technical/prioritize-technical-debt.html |
| Severity belongs to the instance in context, not to the rule — the reason severity moved from the rule to the issue-and-quality pair | SonarQube 10.2+ · https://docs.sonarsource.com/sonarqube-server/latest/user-guide/code-metrics/changing-modes/ |
| Where an issue affects several qualities to different degrees, a single mutually exclusive type is lossy by construction — the reason for `affects` | ibid., and https://docs.sonarsource.com/sonarqube-server/10.4/user-guide/clean-code/definition |

**The honest caveat, recorded so it is not lost.** The strongest formal paper on ordinal risk matrices
argues *against* them, not for them: Cox, *What's Wrong with Risk Matrices?*, Risk Analysis 28(2) 2008
· doi:10.1111/j.1539-6924.2008.01030.x — poor resolution ("can correctly and unambiguously compare
only a small fraction (e.g., less than 10%) of randomly selected pairs of hazards"), range
compression, and "worse than useless" where frequency and severity are negatively correlated. It is
routinely miscited as support for small scales. What it licenses is a deliberate trade of resolution
for reproducibility, stated as such. **No inter-rater reliability study exists for four-level
engineering severity scales**; the case for four rests on the CVSS results above, not on a measurement
of four.

**Rejected.** Any numeric score, debt index, or health rating. SonarQube's Maintainability Rating
scores AUC 0.60 against ground truth from 70 professional developers over 304 files, while a naive
275-line threshold scores AUC 0.95 — Borg, Ezzouhri & Tornhill, ICSME 2024 ·
https://arxiv.org/abs/2408.10754 (note two of three authors are CodeScene employees and CodeScene
wins the benchmark; the line-count baseline embarrasses their product too, and the replication package
is public). Corroborating: SonarQube precision 18% against manual ground truth across 47 projects
(Lenarduzzi et al., JSS 198 2023 · https://fpalomba.github.io/pdf/Journals/J51.pdf); only 25 of 202
Java rules showed even low fault-proneness (SANER 2020 · https://arxiv.org/abs/1907.00376).

**Rejected.** Remediation effort in minutes, hours, or currency. The denominator in the standard model
is a predefined constant of 30 minutes per line of code with no calibration study behind it, and when
developers were timed actually fixing the items the estimates were overestimated in most projects —
Saarimäki, Baldassarre, Lenarduzzi & Romano, IST 128:106377 2020 · doi:10.1016/j.infsof.2020.106377.
The canonical SQALE definition document's own home at sqale.org now returns 404.

**Rejected.** Any composite that divides impact by effort. Beyond multiplying uncertain estimates
while looking precise, dividing by effort structurally starves foundational work — a debt panel ranked
by a formula that deprioritises debt defeats itself. That last property is mechanical rather than
measured; no study of it was found.

## Suppressions

| Claim | Source |
|---|---|
| Identical code is not duplicated knowledge — the worked counter-example is two byte-identical validators that must stay separate | Hunt & Thomas, *The Pragmatic Programmer*, 2nd ed. 2019, Topic 9 |
| Deliberate near-duplication can encode a different intent; duplication against an external contract is unavoidable and should be mitigated rather than eliminated; a cached derived value is a finding only when the duplication escapes its module | ibid. Topic 9 |
| Where decoupling is the goal, duplication is the intended trade | Ford & Richards, *Fundamentals of Software Architecture*, 1st ed. 2020, Ch.16 |
| "Count of patterns applied" is never a good quality metric | Nygard, *Release It!*, 1st ed. 2007, p.110 |
| Findings must be justified by a named threat, not by an absent field | ibid. p.144 |
| An unbalanced capacity ratio is a signal to add protection, not to equalise capacity — equalising can be a gross misuse of capital | ibid. p.98 |
| Building for scale you do not need "is wasted effort, and may lock you into an inflexible design. In effect, it is a form of premature optimization" | Kleppmann, *DDIA*, 2015 Early Release, About this Book p.8 |
| Sophisticated machinery is not over-engineering when the stated requirements demand it | Xu, *System Design Interview*, Volume 1, p.88 |
| A missing component paired with a stated reason is a decision, not a gap | ibid. p.223, p.259, p.210, p.54 |
| Where no non-functional targets are stated, the finding is that they are missing | *The Ultimate System Design Playbook*, McCandless 2025, p.7 |
| Absence of Byzantine tolerance is not debt outside an adversarial deployment | Petrov, *Database Internals*, 2019, p.193, p.309 |
| Eventual consistency works in practice; a single leader is a simplification; manual failover can be correct; last-write-wins is a legitimate deliberate choice | ibid. p.235, p.212, p.119 (via DDIA Ch4), p.233 |
| Neither storage engine can be asserted to amplify writes more than the other — "comparing the two directly may lead to incorrect assumptions" | ibid. Ch7 p.144 |
| Prototype code may legitimately ignore correctness, completeness, robustness and style | Hunt & Thomas, ibid. Topic 13 p.121 |
| Speculative flexibility is itself the defect; the sanctioned answer is replaceability, not extensibility | ibid. Topic 27 p.224 |
| Deviating from a well-known company's published architecture is not a finding | ibid. Topic 50 p.446 |
| Information hiding only makes sense when the hidden information is not needed outside the module — this bounds the configuration-parameter rule | Ousterhout, ibid. §5.9 pp.37–38 |
| Layering violations and transactional guarantees are in tension; relieving one worsens the other | Abelson & Sussman, *SICP*, §3.4.2 p.417 |
| Developers ignore analysers when they cannot tell which findings will never be fixed for other reasons — the empirical basis for the exposure axis and for suppressing inert findings | Ernst, Bellomo, Ozkaya, Nord & Gorton, FSE 2015, n=1,831 · https://cs.unibg.it/esecfse_proceedings/fse15/p50-ernst.pdf |
| An "effective false positive" is one after which the developer took no action; a non-blocking check should stay at or under 10% | Sadowski, Aftandilian, Eagle, Jaspan & Miller-Cushon, CACM 61(4) 2018 · https://cacm.acm.org/research/lessons-from-building-static-analysis-tools-at-google/ |
| Success is measured in defects corrected, not findings presented | ibid. |
| Only 6–9% of analyser warnings are removed by bug-fix changes | Kim & Ernst, ESEC/FSE 2007 · https://home.cse.ust.hk/~hunkim/images/e/e8/Papers_kim_2007_fse.pdf |
| Suppressions accumulate and 50.8% of them affect no warning at all — 7,357 suppressions across 46 Python projects | Hu, Wang, Rubin & Pradel, FSE 2025 · https://people.ece.ubc.ca/~mjulia/publications/Suppressed_Static_Analysis_Warnings_FSE2025.pdf |
| Presentation, not only false positives, is a stated barrier — results "dumped onto his screen with no distinct structure" | Johnson, Song, Murphy-Hill & Bowdidge, ICSE 2013, n=20 · https://cs.gmu.edu/~johnsonb/docs/icse2013.pdf |

**Note on scale.** Every study above measures analysers producing hundreds to thousands of findings.
None measures a report of ten to twenty. The mechanisms — effective false positives, warning
blindness, presentation as a barrier — generalise by argument; the magnitudes do not. The 10% ceiling
is applied here as a design budget, not as a measured property of this feature.

## Never recommend

| Claim | Source |
|---|---|
| A rewrite is not an audit outcome — the tiger-team race the story exists to forbid, observed running ten years | Martin, *Clean Code* (in the 2012 Collection), p.5A |
| Work that exceeds a refactor must be reclassified and scheduled, with affected consumers told | Hunt & Thomas, ibid. Topic 40 p.358 |
| Restructuring without tests is not sanctioned; where coverage is absent it is the first item | Ousterhout, ibid. §19.3 p.154; Hunt & Thomas, ibid. Topic 40 p.356 |
| Subdivision has four intrinsic costs — the component count, each new interface, the management code, and the duplication the split introduces | Ousterhout, ibid. Ch.9 intro pp.59–60 |
| Decoupling middleware is expensive, close to irreversible, and often decided above the team | Nygard, ibid. pp.142–143 |
| Synchronous by default, asynchronous when necessary — asynchrony brings data synchronisation, deadlocks, race conditions, and debugging cost | Ford & Richards, ibid. Ch.18 |
| Complexity added for performance with no measurement behind it should be backed out | Ousterhout, ibid. §20.2 p.161 |
| Understanding why a decision was made prevents a refactoring that reintroduces the problem it solved — the gRPC-to-messaging worked example | Ford & Richards, ibid. Ch.19 |
| The most aggressive repair agent produced the worst net outcome | *SmellBench* · https://arxiv.org/abs/2605.07001 |
| Every replacement carries a cost assumption that must be stated rather than assumed | Hunt & Thomas, ibid. Topic 38 n.53 |

## Identity and merge

| Claim | Source |
|---|---|
| Missing current coverage does not establish disappearance; retain historical decisions with unknown verification | [REA scoped-coverage boundary](https://github.com/morluto/rea/blob/705058f3e2df82503f1c601fc464aea7cbb626b8/docs/reconstruction-coverage.md) and local audit identity policy. Historical severity is not a newly verified verdict. |
| A fingerprint must be "the same for all results that are logically identical, and different for any two results that are logically distinct… resistant to changes that do not affect the logical identity" | SARIF v2.1.0 errata01 §3.27.16 |
| Partial fingerprints carry only what a matcher cannot derive for itself; the producer contributes ingredients, the management system computes the identity | ibid. §3.27.17 |
| Fingerprint keys are versioned hierarchical strings, and a matcher uses the greatest version common to both records | ibid. §3.5.4.2 |
| Absolute line numbers must not enter a fingerprint | ibid. Appendix B (normative) |
| The bar is "stable enough to reduce the number of results that are erroneously reported as 'new' to a low enough level that the development team can manage" | ibid. Appendix B |
| `baselineState` is present on every result or on none | ibid. §3.27.24 |
| The four baseline states and their consumer semantics | ibid. §3.27.24 |
| A suppression records who accepted it and why, so a later reviewer can audit the decision | ibid. §3.35 |
| Hashing a renameable name, or an ordinal index, defeats matching across renames and reordering — the published post-mortem | Semgrep · https://github.com/returntocorp/semgrep/pull/7218 |
| One hash is brittle; several narrow overlapping ones let a matcher degrade | ibid. |
| The largest deployment of this mechanism consumes a single key and computes it for tools that omit it, because omission produced duplicate alerts | GitHub Code Scanning · https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning |
| An accepted item should resurface when the condition that justified accepting it changes | Snyk ignore semantics · https://docs.snyk.io/scan-fix-and-prevent/fix/prioritize-issues-for-fixing/ignore-issues.md |

**Note.** Component ids in this skill are already stable across every architecture in a design file by
its own schema rule, which is why the identity scheme rests on them. That property is this repository's
own, not borrowed.

## Recording the audit

| Claim | Source |
|---|---|
| Checked categories identify inspected scope, not proof of absence; unknown checks expose identity, missing evidence, and next probe | Local output contract applying the scoped-coverage rule. Unknowns do not count toward survived checks. |
| Suppressed items are shown as suppressed rather than omitted, so they remain searchable and auditable | Datadog Code Security · https://docs.datadoghq.com/security/code_security/static_analysis/ |
| Accepting an item should state what accepting it costs, not merely record a dismissal | SonarQube 10.4 release notes · https://www.sonarsource.com/products/sonarqube/whats-new/sonarqube-10-4/ |
| Triage reasons reduce in practice to false positive, acceptable risk, and no time | Semgrep PR-comment triage verbs · https://semgrep.dev/docs/ |
| Failing items are always visible; only passed, warning, manual and not-applicable groups collapse, each with a count | Lighthouse report renderer · https://github.com/GoogleChrome/lighthouse/blob/main/report/renderer/category-renderer.js |
| A short description should be a single sentence understandable on one line, because a viewer with limited space will truncate the long one | SARIF v2.1.0 errata01 §3.49.9–3.49.10 |
| Rules get renamed, and the alias mechanism belongs in the schema from the start | ibid. §3.49.4, §3.49.6, §3.49.8 |
| Tools cannot detect structural and architectural debt, so equating debt with what a tool finds leaves large amounts unrecorded — the reason `checked` and the unverified list are written | Kruchten, Nord & Ozkaya, IEEE Software 29(6) 2012 |
| Bad architecture choices are the top-ranked debt source (54% of top-three rankings, mean rank 4.3), while 41% of teams use no tools for it and 16% found the tools they had gave appropriate detail | Ernst et al., FSE 2015 · https://cs.unibg.it/esecfse_proceedings/fse15/p50-ernst.pdf |
| Run-to-run recall of a model-authored finding set is not established by any published work | No source. Stated as a limitation for exactly that reason. |
