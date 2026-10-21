# Provenance — System Design

Sources for changed process contracts in [SKILL.md](../../skills/system-design/SKILL.md). Mechanism provenance lives in [HEURISTICS.md](HEURISTICS.md), [AUDIT.md](AUDIT.md), and [RUNTIME.md](RUNTIME.md).

## Route the ask

| Claim | Source |
|---|---|
| Small routing entry point and conditional reference loading | [Pinned REA router](https://github.com/morluto/rea/blob/705058f3e2df82503f1c601fc464aea7cbb626b8/.agents/skills/reverse-engineer-anything/SKILL.md); adapted to architecture work, which REA itself excludes. |

## Process

### 1. Locate and resume

| Claim | Source |
|---|---|
| Unchanged HEAD does not identify staged, unstaged, or untracked working-tree bytes | Git working-tree/index/commit distinction; runtime hashes the actual scoped source bytes. |
| Installed local runtime maintains tracked investigation state and explicit recovery | [RUNTIME provenance](RUNTIME.md); selected product design. |

### 2. Establish the current truth

| Claim | Source |
|---|---|
| Observed, derived, and inferred evidence retains scope and limitations; unanswered questions remain explicit | [Evidence lifecycle](HEURISTICS.md#evidence-and-uncertainty). |

### 8. Audit the architecture for debt

| Claim | Source |
|---|---|
| Finder and verifier are fallible; uncertainty is neither confirmation nor refutation | [Audit pipeline provenance](AUDIT.md#the-pipeline). |

### 9. Write, render, and verify

| Claim | Source |
|---|---|
| Structural validation, semantic review, and browser inspection establish distinct properties | [Evidence lifecycle](HEURISTICS.md#evidence-and-uncertainty); report diagnostics only inspect rendering. |
