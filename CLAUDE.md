This repository ships one agent skill: `skills/system-design/`.

Invariants a script cannot enforce:

- `SKILL.md` stays under 500 lines; the frontmatter `name` equals the folder name and the `description` stays under 1024 characters.
- Every sibling file (`INTERVIEW.md`, `HEURISTICS.md`, `ARCHETYPES.md`, `HTML-REPORT.md`, `EXAMPLES.md`) back-links `SKILL.md` in its opening lines, and `SKILL.md` links each sibling at the step that needs it. `EXAMPLES.md` is conditional help after a generic first draft, never default context.
- The two invocation settings stay in agreement whatever their value: `SKILL.md`'s `disable-model-invocation` and `agents/openai.yaml`'s `policy.allow_implicit_invocation` are inverses of each other, and Codex does not read the SKILL.md field. Model-invocable today means no `disable-model-invocation` in the frontmatter and `allow_implicit_invocation: true`.
- All renderer code lives in `assets/report-template.html`; `skills/system-design/scripts/render_report.py` performs the `__DESIGN_JSON__` substitution and is the only place that logic exists; the skill never reads the template into context.
- The skill must appear in the top-level `README.md` install/reference sections and in `.claude-plugin/plugin.json`.
- The frontmatter `metadata.version` and `.claude-plugin/plugin.json` `version` move together — plugin.json's version is the update cache key, so a content commit without a bump ships nothing to installed users.
- `AGENTS.md` is a symlink to this file — never a separate document.
- Skill content states principles without citing authors, books, or other skills. Provenance instead lives in `docs/provenance/<FILE>.md`, mirroring that runtime file's headings — a principle carrying a number, a threshold, or a correctness claim is incomplete without a row there, and a number rejected during verification is recorded with its reason so it cannot be quietly re-added. Contrastive examples apply already-proven runtime rules and do not introduce new universal thresholds.
- `HEURISTICS.md` owns every reusable mechanism and decision ladder; `ARCHETYPES.md` names them and adds only what a shape changes. Neither file restates the other, which is what keeps the two from contradicting each other.
- Every archetype pack back-links `../SKILL.md` in its opening lines, and every runtime pack has a same-named provenance pack under `docs/provenance/archetypes/` whose headings mirror it. The runtime and provenance routers link all six packs.
- Every archetype entry carries `Not when` and `Anti-gate`. Without the first, a shape gets applied to a system it does not fit and drags its machinery along; without the second, nothing states the envelope below which the shape is unjustified.
