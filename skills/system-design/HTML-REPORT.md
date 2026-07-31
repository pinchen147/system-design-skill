# HTML Report

The artifact and schema contract for [SKILL.md](SKILL.md): the component types used from **Establish the current truth** onward, and the output written at **Write, render, and verify**—one JSON source of truth, one committed doc, one rendered report.

## Contents

- [The three artifacts](#the-three-artifacts) · [Render mechanics](#render-mechanics)
- [Schema rules](#schema-rules) — read before writing `design.json`
- [design.json schema](#designjson-schema) · [Component types and icons](#component-types-and-icons)
- [What the rendered report does](#what-the-rendered-report-does) · [DESIGN.md format](#designmd-format)
- [ADR on decision](#adr-on-decision-repo-mode) · [Vocabulary](#vocabulary)

## The three artifacts

| Artifact | Location | Lifecycle |
|---|---|---|
| `design.json` | `docs/design/<slug>/` (git repo) or `./<slug>/` (no repo) | Source of truth; every iteration edits this first |
| `DESIGN.md` | Beside `design.json` | Regenerated from the JSON every iteration; a `## Notes` section, if present, is preserved verbatim |
| `system-design-<slug>.html` | `$TMPDIR` | A render, regenerated any time; never hand-edited, never committed |

## Render mechanics

Run the shipped script from the skill's own directory:

```
python3 <skill-dir>/scripts/render_report.py --design docs/design/<slug>/design.json --out "$TMPDIR/system-design-<slug>.html"
```

`<skill-dir>` is the directory holding `SKILL.md`; the script resolves the template relative to itself. It also opens the report once written—`open` on macOS, `xdg-open` or `wslview` on Linux, `start` on Windows—so no separate step can be missed. `--no-open` or `SYSTEM_DESIGN_NO_OPEN=1` suppresses it for scripted and headless runs; failing to open is reported but never fatal, since the file is already on disk.

Never read `assets/report-template.html` into context and never rebuild the report by hand. It is 82 KB of renderer code, the substitution is mechanical, and a 27 KB JSON payload full of `/` is corrupted by `sed` and by shell interpolation. The script asserts the placeholder appears exactly once, fails loudly on malformed JSON, and escapes `</` as `<\/` so that no string value can terminate the embedded `<script type="application/json">` block—an unescaped `</script>` inside any `note`, `label`, or `thesis` silently truncates the payload and renders a report titled `System design report` with most components missing.

If no opener works—headless box, remote session—print the absolute path and say the file is self-contained and portable: it can be copied, emailed, or dropped in a shared drive and double-clicked anywhere.

## Schema rules

1. **Stable ids.** A component keeps one `id` across every architecture in the file. Diff badges, the Compare tab, and steal-bits composition all derive from id identity — new name, new id; same box, same id.
2. **Layout is approximate and flow-first.** Every v2 component carries a center-point `position`; `grid` remains only for v1 compatibility. Place the primary flow left-to-right, owned state below/beside its service, async work downward, and external dependencies near the caller. The renderer snaps, aligns, resolves component overlaps, creates soft cluster bounds, routes around obstacles, and expands the canvas as needed. Ports are automatic.
3. **Every flow step references component ids present in that architecture.** Validate before writing the file.
4. **The distinctness rule.** Candidates must be distinct on at least one of: **structural style** (a different row of the [HEURISTICS.md](HEURISTICS.md) matrix), **zone-level topology** (a different data topology *and* a different async topology), or **data and consistency model** (a different representation, ordering authority, or conflict-resolution mechanism over the same component graph). A swapped database is a variant; a swapped conflict-resolution model is a candidate, because it changes the invariants rather than the vendor. Each `thesis` names the structural or data-model idea that makes the candidate distinct. A candidate composed from two others on user feedback is exempt from this rule; its `thesis` names what the combination buys.
5. **Reasoning cites.** Every `comparison.recommendation.reasoning` line and every `tradeoffs` entry chains to an estimate row, a `dataModel` decision, or a named principle from [HEURISTICS.md](HEURISTICS.md). No "more scalable" without the number that says why it matters here, and no citing the style matrix as evidence — its rows are priors, not measurements.
6. **Production contracts are first-class.** `domain.entities[].invariants`, `dataModel.entities`, `interfaces`, and two or three resolved `deepDives` are required in v2. When the design has structured persistence, `dataModel.schemas` gives an intuitive, non-executable view of every table or collection: essential fields, key roles, indexes, relationships, authority, and retention. Every queue/log states delivery and idempotency semantics; every store is identified as authoritative or derived in its `note` and carries the optional `state` contract described below. Every edge carries the optional `contract` described below. These fields are optional for backward compatibility, but mandatory in newly completed candidates. `requirements.priorities.top3` names exactly three ratings axes, is settled before any candidate is drawn, and every axis in it also appears in `comparison.axes`. Migration notes state how the change is undone; a migration that executes on hardware you do not control — shipped clients, embedded devices, on-prem installs — is one-way, and says how long the previous version keeps writing the old shape.
7. **Candidates stay complete.** Do not collapse losing candidates into partial sketches. Every candidate carries all components, edges, flows, trade-offs, and ratings needed for a direct comparison. A composed candidate is added, never a replacement — its parents stay drawn.

## design.json schema

```jsonc
{
  "version": 2,
  "slug": "design-messaging",
  "title": "Design a messaging service",
  "mode": "greenfield",                  // "repo" | "greenfield"
  "status": "draft",                     // "draft" | "decided"
  "decided": null,                       // architecture id once status is "decided"
  "updatedAt": "2026-07-30",

  "context": {
    "problem": "one paragraph",
    "constraints": ["mobile-first", "small team"],
    "vocabulary": []                     // terms adopted from the repo's CONTEXT.md (repo mode)
  },

  "requirements": {
    "functional": [
      { "id": "fr-1", "text": "1:1 text messaging", "priority": "core" }    // core | stretch
    ],
    "nonFunctional": [
      { "id": "nfr-1", "axis": "latency", "target": "p99 < 500 ms send-to-deliver (online)",
        "rationale": "user-stated" }
    ],
    "outOfScope": ["livestreaming"],
    "priorities": {                      // exactly three ratings axes; order is not a ranking
      "top3": ["scalability", "faultTolerance", "performance"],
      "source": "user",                  // user | assumed
      "rationale": "500M DAU stated; an acknowledged message may never be lost"
    },
    "conflicts": [                       // sanity-pass outcomes the user accepted, and doc-vs-code divergence
      { "text": "wants strong consistency AND 5-region sub-100ms writes", "resolution": "regional home leaders" }
    ]
  },

  "estimates": {
    "assumptions": [ { "text": "500M DAU", "source": "user" } ],            // user | assumed
    "rows": [
      { "metric": "write QPS", "value": "115k avg / 460k peak",
        "derivation": "500M × 20 msg ÷ 86,400; peak ×4" },
      { "metric": "cache footprint", "value": "n/a",
        "derivation": "no read-through path; every read is a cursor scan of the device inbox" }
    ]
  },

  "domain": {
    "entities": [
      {
        "name": "Message",
        "purpose": "immutable user-authored event",
        "invariants": ["acknowledged means durably accepted", "client message id is unique per sender device"]
      }
    ]
  },

  "dataModel": {                         // settled before candidates exist; see SKILL.md "Fix the data and consistency model"
    "entities": [
      {
        "name": "Message",
        "representation": "immutable row in a wide-row store, keyed (conversationId, messageId)",
        "identity": "snowflake messageId; clientMessageId dedups at the write",
        "orderingAuthority": "the conversation's log partition assigns the sequence",
        "conflictResolution": "none — messages are append-only and never mutate",
        "durabilityPoint": "the log partition commit, which is also the client acknowledgement",
        "gc": "delivered messages drop at 30 days; the undelivered backlog moves to the store"
      }
    ],
    "schemas": [                         // intuitive design artifact, never executable DDL
      {
        "name": "Message",
        "store": "Wide-row message store",
        "kind": "authoritative history", // authoritative | derived and rebuildable | cache, in plain language
        "fields": [
          { "name": "conversationId", "type": "ID", "key": "partition key", "references": "Conversation.id" },
          { "name": "messageId", "type": "ID", "key": "sort key" },
          { "name": "senderId", "type": "ID", "references": "User.id" },
          { "name": "body", "type": "text or media reference" }
        ],
        "indexes": ["(conversationId, messageId DESC) — conversation history"],
        "relationships": ["senderId → User.id", "conversationId → Conversation.id"],
        "notes": ["Immutable after acceptance; receipts are stored separately."]
      }
    ],
    "notes": ["ordering is per conversation, never global — cross-conversation order is not a product promise"]
  },

  "interfaces": [
    {
      "name": "Send message",
      "transport": "WSS SEND {conversationId, clientMessageId, body}",
      "purpose": "durably accept a message",
      "consistency": "ordered per conversation",
      "idempotency": "clientMessageId scoped to sender device",
      "style": "bidirectional command",       // interaction shape, such as "REST resource", "unary RPC", or "bidirectional command"
      "trustBoundary": "sender device → connection gateway", // identities or zones crossed and where untrusted input first terminates
      "deadline": "3 s to durable acceptance", // caller-visible time budget and the operation or milestone it bounds
      "retryability": "retry with the same clientMessageId after reconnect", // which outcomes may be retried, by whom, and with what stable key
      "backpressure": "server overload closes with 1013; client reconnects with jitter", // overload signal plus caller throttling, buffering, or shedding response
      "compatibility": "additive fields only within v1; ignore unknown fields", // versioning, evolution, and deprecation rule understood by both ends
      "failureResult": "ACCEPTED with messageId; REJECTED before commit; UNKNOWN if the deadline expires after commit may have occurred" // caller-visible outcomes, including ambiguity after a downstream timeout
    }
  ],

  "deepDives": [
    {
      "title": "Make acknowledgement the durability point",
      "pressure": "463k peak sends/s; no acknowledged-message loss",
      "decision": "acknowledge after the partitioned log commits",
      "alternatives": ["gateway memory", "synchronous history write"],
      "failureMode": "gateway dies after acknowledging",
      "evidence": ["write QPS estimate", "no-loss invariant"]
    }
  ],

  "architectures": [
    {
      "id": "a",                         // "current" (repo mode) | "a" | "b" | "c" | later letters for composed candidates
      "name": "Modular monolith + managed queue",
      "style": "modular-monolith",       // row name from the HEURISTICS.md matrix, kebab-case
      "thesis": "one sentence: the structural or data-model idea that makes this candidate distinct",
      "canvas": {
        "primaryFlow": "send-message"     // narrative centerline; first flow is the fallback
      },
      "components": [
        {
          "id": "chat-svc",              // STABLE across every architecture in the file
          "name": "Chat service",
          "type": "service",             // icon enum below
          "zone": "app",                 // edge | app | data | async | external
          "cluster": "core",              // optional soft cluster; zone supplies the default
          "position": { "x": 720, "y": 280 }, // preferred approximate center point
          "grid": { "col": 3, "row": 1 },// deprecated v1 fallback
          "tech": "Elixir",              // optional
          "note": "100k conns/node",     // required; shown in the canvas inspector
          "state": {                      // optional in legacy artifacts; required for stateful components in new candidates
            "role": "authoritative",      // authoritative | derived
            "acknowledgement": "quorum WAL commit", // authoritative only: exact externally acknowledged durability point
            "failureDomain": "three independently powered zones", // authoritative only: failures the acknowledged copies do not share
            "rpo": "0 for one-zone loss; < 5 min for region loss", // authoritative only: maximum acceptable recovered-data age, scoped by failure
            "rto": "< 60 s zone failover; < 30 min region restore", // authoritative only: maximum acceptable recovery time, scoped by failure
            "recovery": "promote by fenced quorum; restore snapshot plus WAL" // authoritative: promotion/restore procedure; optional for derived
          },
          "change": "unchanged"          // added | removed | modified | unchanged — vs current; omit in greenfield
        }
      ],
      "edges": [
        { "from": "lb", "to": "chat-svc", "kind": "sync", "label": "WSS",
          "importance": "primary",        // kind: sync | async | stream; importance: primary | secondary
          "contract": {                   // optional in legacy artifacts; required for every edge in new candidates
            "deadline": "500 ms of caller budget", // sync: completion deadline; async: handoff deadline or maximum acceptable age
            "retryOwner": "load balancer, once with jitter", // exactly one component/layer responsible for retries
            "backlogBound": "2k in-flight calls/instance; shed above it" // concrete concurrency, queue, in-flight, retention, or age bound
          }
        }
      ],
      "flows": [
        {
          "id": "send-message",
          "name": "Send message (online recipient)",
          "steps": [
            { "seq": 1, "from": "client", "to": "lb", "label": "WSS frame",
              "note": "client-generated message id makes retries idempotent" }
          ]
        }
      ],
      "tradeoffs": {
        "pros": ["one ACID store — no sagas at this write rate"],
        "cons": ["single-region write ceiling"],
        // repo mode only. S = lands in one release, no data migration · M = staged across a few
        // releases, or one bulk data migration · L = a compatibility path that runs beside the old
        // one for many releases. Notes name what data moves and whether rollback survives once
        // users write the new format.
        "migration": { "cost": "M", "notes": [
          "dual-write cutover on messages table",
          "one-way after the first new-format write — downgrade loses unsynced drafts"
        ] }
      },
      "ratings": {                        // 1–5; cost: 5 = cheapest. Architecture 0 is rated too.
        "deployability": 4, "elasticity": 2, "evolvability": 3, "faultTolerance": 3,
        "modularity": 4, "cost": 4, "performance": 3, "reliability": 4,
        "scalability": 3, "simplicity": 4, "testability": 4
      }
    }
  ],

  "comparison": {
    "axes": ["scalability", "simplicity", "faultTolerance", "performance", "cost", "evolvability"],  // the columns to emphasise, led by requirements.priorities.top3
    "recommendation": {
      "architecture": "b",
      "reasoning": [
        "115k write QPS rules out a single-region relational core (partition by conversation)",
        "read:write asymmetry favours fan-out-on-write inboxes with a celebrity pull path"
      ]
    }
  },

  "risks": [ { "text": "presence fan-out dominates at 50M concurrent", "horizon": "at 10× DAU" } ],
  "nextSteps": ["prototype gateway heartbeat reaping"],
  "adr": null                            // path to the ADR once written (repo mode, on decision)
}
```

`components[].state` is the auditable state-survival contract. `role` says whether the component is the authority whose acknowledgement creates the promise, or a rebuildable `derived` view. An authoritative component supplies `acknowledgement` (the exact durable event after which success may be exposed), `failureDomain` (the independent failure scope covered by that acknowledgement), `rpo` (maximum acceptable data loss or recovery-point age, with scope), `rto` (maximum acceptable recovery time, with scope), and `recovery` (the tested promotion/restore procedure). A derived component supplies `source` (the complete authoritative reconstruction input) and `cursor` (the durable position/checkpoint proving how far that source has been applied); `recovery` may describe rebuild or catch-up. Do not put `UNKNOWN` in authoritative lifecycle state: authoritative operations use `PENDING | RECONCILING | SUCCEEDED | FAILED | CANCELLED`; `UNKNOWN` is only the caller's observation after an ambiguous timeout.

`edges[].contract` is the dependency-completion contract. `deadline` is the caller-visible completion budget for a synchronous edge, or the maximum acceptable age/handoff deadline for an asynchronous or log edge. `retryOwner` names exactly one layer or consumer that retries and, when useful, its policy/key. `backlogBound` names the finite concurrency, in-flight, queue, retention, or lag bound and the saturation action. `n/a` is valid only when it states why that dimension cannot apply and names the alternative finite bound. Missing `state` and `contract` fields remain valid and render as absent sections, not placeholder or `undefined` values.

## Component types and icons

`type` selects a symbol from the template's inline library:

| type | Symbol | Use for |
|---|---|---|
| `client` | person silhouette | End users, browsers |
| `mobile` | phone outline | Mobile apps |
| `lb` | diamond | Load balancers, traffic routing |
| `gateway` | shield-hex | API gateways, edge auth |
| `service` | hexagon | Stateless app services, monolith modules |
| `ws` | double-arrow hexagon | Persistent-connection gateways (WebSocket) |
| `worker` | bolt-in-loop | Async workers, consumers, transcoders |
| `cron` | clock | Schedulers, periodic jobs |
| `db-sql` | cylinder | Relational stores |
| `db-nosql` | stacked cylinders | KV, wide-row, document stores |
| `db-graph` | connected nodes | Graph stores |
| `cache` | lightning chip | In-memory caches |
| `queue` | striped pipe | Queues, task buffers |
| `stream` | arrowed log | Replayable logs, event streams |
| `blob` | bucket | Object storage |
| `cdn` | globe | Edge delivery |
| `search` | magnifier | Search/inverted indexes |
| `ml` | sparkline chip | Model inference, ranking |
| `ledger` | double-entry book | Append-only financial records |
| `monitor` | pulse | Observability |
| `external` | plug | Third-party APIs |

A client-side architecture uses the same enum: `mobile` or `client` for the shell, `service` for a state owner or sync engine, `db-sql`/`db-nosql` for the on-device store, `cache` for an in-memory tier, `queue` for a mutation outbox, `worker` for background refresh. Unknown or convention-less types render as a filled rectangle with an internal mark, so a missing symbol degrades rather than breaks.

## What the rendered report does

- **Header** is the title and the date — nothing else, unless the user asks for more.
- **Tabs**, hash-routed and reload-stable: `#overview` · `#current` (repo mode) · one per candidate (`#a` `#b` `#c` …) · `#compare`. ←/→ cycle architectures.
- **Overview**: problem, FR/NFR tables, the top-three characteristics, estimates with derivations, the data and consistency model, accepted conflicts, and the recommendation banner with its reasoning chain.
- **Architecture tabs**: a flow-first white canvas with soft clusters and a permanent flow sidebar on the right. The complete board fits on load and tab switch. Scroll/trackpad pinch zooms toward the pointer; empty-canvas drag pans; `−`, `+`, `Fit`, and keyboard equivalents are visible. Semantic zoom automatically reveals technology subtitles and secondary edge labels as space permits.
- **Components**: pale family fills, saturated family strokes, black centered text, and conventional outer silhouettes—phones, hexagonal services, cylinders, cache chips, queue capsules, workers, buckets, and books.
- **Connections**: directional orthogonal routes with rounded bends, perimeter ports, arrowheads, and white-backed labels. Routes treat every component as an obstacle and never pass through one.
- **Selection**: clicking a flow (or cycling with ↑/↓) traces numbered crimson steps while its notes stay in the permanent sidebar. Clicking a component opens a closable floating inspector over the canvas without replacing the flow list. Escape clears; diff badges appear in repository mode.
- **Compare**: the ratings matrix (all candidates plus Architecture 0), pros/cons, migration row in repo mode, per-candidate diff chips, and the recommendation banner.
- **Diagnostics**: a hidden `report-diagnostics` element carries `data-component-overlaps`, `data-route-collisions`, `data-text-overflows`, and `data-fit-overflows` for the current route. All four read `0` on a clean render.
- Self-contained: no network requests, light mode only, Wikipedia-style type system (serif headings, standard sans body), keyboard-accessible, reduced-motion respected. Every component's `note` is required — it feeds the click-to-inspect panel.

## DESIGN.md format

Frontmatter: `date`, `mode`, `status`, `decided` (when set). Sections, in order: Context → Requirements → Core entities and invariants → Data and consistency model → System interfaces → Estimates → Candidates → Comparison and recommendation → Critical deep dives → Operations and rollout → Risks and what breaks first → Measurements that could overturn the decision → Next steps → Notes (user-owned; preserved verbatim on regeneration; created empty).

## ADR on decision (repo mode)

Offer once, when the user picks a winner: `docs/adr/NNNN-<slug>.md` with Title (numbered noun phrase) · Status (Accepted; and `Superseded by NNNN` written back into any ADR this replaces) · Context (the forces, the rejected candidates by name with the reason each lost, and the documents that previously owned this subject) · Decision (affirmative voice: "We will…") · Consequences (the trade-offs accepted, good and bad). Future runs read `docs/adr/` at **Establish the current truth** and do not re-litigate.

## Vocabulary

**Use exactly:** architecture, candidate, component, flow, step, zone, edge, envelope, estimate, characteristic, trade-off, recommendation.

**Never substitute:** box, node, block (for component) · path, journey (for flow) · lane, tier, layer (for zone) · option, variant (for candidate — a variant is what fails the distinctness rule).
