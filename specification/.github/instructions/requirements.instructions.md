---
applyTo: 'requirements/**'
description: 'Rules for creating, updating, and validating requirements specifications.'
---

# Requirements Specification Rules

The `applyTo` pattern matches the configured requirements root of this
repository.

These rules are the canonical requirements-specific instructions. They apply
together with the global workflow rules in
`.github/instructions/project-workflow.instructions.md` (workflow stages,
approval gates, configured-value rules, unresolved-value rules, identifier
stability), its reference `.github/instructions/references/workflow-rules.md`
(requirement-document procedure), and
`.github/instructions/references/change-history.md` (the change-history
attribution rule). This file does not repeat them.

## Requirements root

The actual requirements path must be resolved from `.project.yml`.

Resolve the effective requirements root as follows:

1. Start at `requirements.local_root` relative to the operational workspace
   root.
2. Resolve `paths.requirements` relative to that requirements root.
3. When `requirements.mode` is `external_repository`, use
   `requirements.repository.local_path` (resolved relative to the main
   repository root; it may point outside it, for example a sibling
   directory) as the repository root for the requirements paths. This is a
   filesystem path, not a workspace switch: the operational workspace stays
   the main repository.

The configured paths resolve as follows in both modes:

| Keys | Resolved relative to |
|------|----------------------|
| `paths.requirements`, `paths.epics`, `paths.templates`, `paths.decisions`, `paths.requirement_sources`, `paths.domain_model`, `paths.glossary`, `paths.requirements_index`, `paths.traceability_matrix` | The requirements root (under `requirements.repository.local_path` in external mode) |
| `paths.plans`, `paths.tasks` | The main repository root (`repository.local_root`), also in external mode |

Do not treat `paths.requirements` as a second workspace root or resolve it
relative to the parent repository when `requirements.local_root` is present.

`.github/`, `scripts/`, `plans/`, and `tasks/` are installed only in the main
repository; the external requirements repository holds requirement documents
only, with no agents, skills, or scripts of its own. Never install this
instruction file, or any other `.github/` content, in the requirements
repository, and never open it as a separate workspace: doing so would leave
it without the agents and scripts that this rule and the surrounding
workflow depend on. Because the `applyTo` pattern only matches paths under
the workspace root, it does not by itself cover files under
`requirements.repository.local_path` in external mode; apply this instruction
manually whenever a requirement document is read or changed there, exactly
as if `applyTo` had matched it.

If the requirements path cannot be resolved, stop and request clarification. Do
not create files in an assumed location.

## Hierarchical identifier system

Read the identifier prefixes and patterns from `identifiers.*` in
`.project.yml`:

- `identifiers.epic.prefix` and `identifiers.epic.pattern` for epics;
- `identifiers.feature.prefix` and `identifiers.feature.pattern` for features;
- `identifiers.scenario.prefix` and `identifiers.scenario.pattern` for
  scenarios;
- `identifiers.task.prefix` and `identifiers.task.pattern` for tasks;
- `identifiers.numbering` for padding and reuse rules.

With the default configuration the hierarchy reads as follows; the configured
values always take precedence:

```text
EPIC-N -> FEAT-N-M -> ESC-N-M-K -> TASK-N
```

- An epic identifier numbers epic `N`.
- A feature identifier numbers feature `M` of epic `N`.
- A scenario identifier numbers scenario `K` of feature `M` of epic `N`.
- A task identifier numbers a technical implementation task derived from a
  requirement.

Preserve existing identifiers when updating a specification. Never renumber or
rename identifiers automatically; report gaps or duplicates instead and
renumber only after explicit user confirmation (see the identifier rule of
`project-workflow.instructions.md`).

## File structure

- Create one file per epic under the path configured by `paths.epics`.
- Use the filename pattern configured by `identifiers.epic.file_pattern`.
- Use the domain terminology and model defined in
  `<paths.domain_model>` and `<paths.glossary>`, when
  configured.
- Do not invent paths, filename patterns, domain terms, priorities, or states.
- `paths.requirements_index` and `<paths.epics>/epics-consolidated.md` are
  generated files: never edit them by hand. After editing epics, always
  regenerate the index with `python scripts/idx.py build`; regenerate the
  consolidated file with `python scripts/consolidate-epics.py` only when
  `modules.consolidate_epics` and `features.consolidate_epics.enabled` are both
  `true`.

## Epic structure

The epic template under `paths.templates` (`template-epic.md`) is the only
source of truth for section names, column order, and placeholders. Read it
before creating or editing an epic and reuse its headings literally in the
configured `project.language`. Refer to sections by their role, for example:

- the feature heading, followed by the priority and status fields of the
  template;
- the scenarios table of the epic template;
- the acceptance criteria and technical notes sections;
- the tasks table;
- the E2E verification section, only when E2E is enabled (see below);
- the change-history section of the template.

Do not add historical structures, alternative headings, or translated variants
of the template headings. If the template and an existing epic diverge, report
the divergence instead of silently rewriting the epic.

## Allowed values

- Priorities: only the values of `specification.priorities`.
- Requirement states: only the values of `specification.states`.
- Task states: only the values of `specification.task_states`.
- Verification states: only the values of `specification.verification_states`.

Write these values literally, without emoji, in every table cell and field.

## E2E verification

Apply this section only when both of the following conditions are true:

```text
modules.e2e == true
features.e2e.enabled == true
```

When either value is `false`, do not create, require, or fill the E2E
verification section of the template.

Implementation traceability and functional E2E verification are independent
dimensions:

- The tasks table records implementation issues and technical work.
- The E2E verification section records the relationship between requirement
  scenarios and E2E features.
- A closed issue does not imply that an E2E test exists or has passed.
- A Gherkin scenario does not imply that its step definitions are implemented.
- E2E verification must not change the implementation state of the scenario,
  feature, or epic.

### E2E scenario identification

When a configured E2E repository verifies a requirement scenario, prefer the
exact tag built from `features.e2e.tag_pattern`, for example:

```text
@ESC-N-M-K
```

The tag must match the documented scenario identifier.

If the tag does not exist, matching by scenario name or Gherkin text is
provisional. Mark the relationship as a warning in the E2E traceability
information and do not present provisional matches as confirmed matches.

### E2E verification state

The E2E verification section uses the values of
`specification.verification_states`, independent from the implementation state
of the scenario. Do not infer that an implemented test has passed unless the
test result is explicitly available.

## Language

- Use `project.language` for requirements documentation.
- Use `project.language` for user-facing text when it is configured.
- Keep technical terms in English when no established translation exists, for
  example `endpoint`, `hook`, and `schema`.
- If `project.language` is missing or unsupported and the language affects the
  requested operation, stop and request a decision.
- Do not silently assume Spanish, English, or any other language.

## Cross-references

Use the following formats, with the configured identifier prefixes:

- Cross-repository issue: `<repository-alias>#45`
- Cross-epic reference: `See FEAT-3-2`
- Epic dependency: `Depends on EPIC-2`

Repository aliases must be declared in `.project.yml`.

## Conventions

- Write scenarios and acceptance criteria using
  `specification.acceptance_criteria_format`.
- Write acceptance criteria as checklists.
- Put technical notes at the end of each feature.
- Do not modify unrelated requirements or reorder existing content without a
  reason.
- Keep requirements testable, unambiguous, and independently verifiable.

## Change history

Every modification to an epic must add one row to the change-history section of
the template, using the template's columns. Fill the author and agent
columns exactly as defined in
`.github/instructions/references/change-history.md`; if that rule
cannot be satisfied, stop before editing.
