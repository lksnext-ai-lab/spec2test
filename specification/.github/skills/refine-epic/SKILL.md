---
name: refine-epic
description: Writes, reviews, and improves requirement epic files under paths.epics, keeping structure, IDs, states, acceptance criteria, and sections aligned with .project.yml and the configured epic template. Use when an epic, feature, or scenario must be written, reviewed, or improved.
---

# Refine Requirement Epic

Writes, reviews, and improves requirement epic Markdown files under
`paths.epics`.

> This skill edits specification files only. Epic-level GitHub issues belong to
> `manage-epic`; implementation tasks belong to `create-task`.

## Modes

Pick the mode, then read only its reference file:

| Mode | When | Read |
|------|------|------|
| 1. Write | Create a new epic | [references/write.md](references/write.md) |
| 2. Review | Report gaps or inconsistencies (read-only) | [references/review.md](references/review.md) |
| 3. Improve | Complete sections, add features or scenarios, fix format | [references/improve.md](references/improve.md) |

Modes 1 and 3 also apply [references/content-rules.md](references/content-rules.md)
(code-derived content, source types, contradictions, traceability matrix).

## Configuration contract

Read `.project.yml` before any mode (or use the resolved values the caller
passes) and consume these values; never hardcode them:

| Concern | Keys |
|---------|------|
| Location and index | `paths.epics`, `paths.templates`, `paths.requirements_index`, `paths.domain_model`, `paths.glossary` |
| Language | `project.language` (the epic is written in this language) |
| IDs | `identifiers.epic.prefix/pattern/file_pattern`, `identifiers.feature.*`, `identifiers.scenario.*`, `identifiers.numbering.zero_padding`, `identifiers.numbering.reuse_existing_ids` |
| States | `specification.states` (epic, feature, scenario), `specification.task_states` (Tasks table), `specification.verification_states` (E2E automation) |
| Priorities | `specification.priorities` |
| Acceptance criteria | `specification.acceptance_criteria_format` |
| Completion gate | `workflow.human_validation_required_for_completion` |
| E2E | `modules.e2e`, `features.e2e.enabled` |
| Traceability and sources | `paths.traceability_matrix`, `paths.requirement_sources` |
| Code evidence | `paths.tasks`, `integrations.codebase_memory.evidence_path` (audits) |
| Index and consolidation | `scripts/idx.py`, `scripts/consolidate-epics.py`, `modules.consolidate_epics`, `features.consolidate_epics.enabled` |

`EPIC-N`, `FEAT-N-M`, and `ESC-N-M-K` in this skill are the default patterns.
Always use the configured prefixes and patterns.

If a value needed for the operation is unresolved (see the unresolved-value
rule in `project-workflow.instructions.md`), report it and ask the user before
relying on it.

## Mandatory conventions

### Template and headings

The template in `paths.templates` (`template-epic.md`) is authoritative for
sections, order, columns, and headings. Refer to sections by role and copy the
headings from the template for `project.language`. Canonical headings:

| Role | `es` | `en` |
|------|------|------|
| Scenarios table | `### Escenarios` | `### Scenarios` |
| State field | `**Estado:**` | `**Status:**` |
| Priority field | `**Prioridad:**` | `**Priority:**` |
| Feature index | `## Índice de features` | `## Feature Index` |
| E2E section | `### Verificación E2E` | `### E2E Verification` |
| Change history | `## Historial de cambios` | `## Change History` |

### File naming

- New files follow `identifiers.epic.file_pattern` (default `epic-NN-name.md`).
- Render `NN` with `identifiers.numbering.zero_padding`: without padding
  `epic-7-orders.md`, with padding `epic-07-orders.md`.
- `name` is lowercase kebab-case in `project.language`.
- Never rename existing files; report deviations only.

### IDs

- Hierarchy: epic → feature → scenario, using the configured patterns.
- New features and scenarios take the next number after the highest existing
  one. Never reuse a number unless `identifiers.numbering.reuse_existing_ids`
  is `true`.
- **Never renumber, reorder, or change an existing ID without explicit user
  confirmation.** Existing IDs are referenced by issues, E2E tags, and the
  traceability matrix. Gaps in numbering are reported, never closed
  automatically. Duplicates are reported with a proposed fix that is applied
  only after confirmation.

### States

- Write literally one of the values configured in `specification.states` for
  epics, features, and scenarios; `specification.task_states` for the Tasks
  table; `specification.verification_states` for E2E automation.
- Never translate, re-spell, or add emoji to state values in the file. Emoji
  may appear only in chat reports.
- A closed issue or code evidence never means completed. Use the configured
  completed state only after recorded human validation when
  `workflow.human_validation_required_for_completion` is `true`. A feature is
  completed only when all its scenarios are; an epic only when all its
  features are.

### Scenarios and acceptance criteria

- Scenario descriptions and acceptance criteria follow
  `specification.acceptance_criteria_format` exactly (keywords, casing, and
  punctuation as configured; no extra bold).
- Use the configured scenario table columns from the template.

### E2E section

Generate the E2E section only when both `modules.e2e` and
`features.e2e.enabled` are `true`. Otherwise the section and the E2E counts of
the progress summary must be absent; their absence is correct, not a warning.

When enabled, the table has the six template columns: Scenario ID, E2E Feature,
E2E Scenario, Automation, Last result, Evidence. New rows use the configured
"not defined" verification state. E2E content is maintained by `link-e2e`; this
skill never infers E2E coverage from issues or `.feature` files.

### Change history

Add a row to the template's change history section for every modification.
Record Author and Agent per
`.github/instructions/references/change-history.md`.

## Index and consolidation

After writing or improving an epic, always regenerate the index:

```console
python scripts/idx.py build
```

When `modules.consolidate_epics` and `features.consolidate_epics.enabled` are
both `true`, also run:

```console
python scripts/consolidate-epics.py
```

`idx.py build` regenerates `paths.requirements_index` and
`consolidate-epics.py` writes `<paths.epics>/epics-consolidated.md`. Both are
generated files: never edit them by hand, and commit them together with the
epic changes. Report the generated files. When the consolidation flags are not
both `true`, skip only the consolidation and say so.
