---
applyTo: '**/*'
description: 'Global workflow rules for requirements traceability, collaboration, and evidence-driven project work.'
---

# Project Workflow Rules

`.project.yml` is the source of truth for project identity, requirements mode,
paths, identifiers, repositories, modules, integrations, language, states, and
validation options. Read it before making changes.

Detailed rules live in `.github/instructions/references/` (not auto-loaded).
Read the named `workflow-rules.md` section or file before:

- creating or changing a requirement document or resolving requirement paths:
  § *Requirement documents* and § *Evidence*;
- any branch, commit, pull request, merge, or deletion of requirements,
  sources, decisions, or evidence: § *Collaboration and change control*;
- choosing repositories, specialists, tasks, or issue links:
  § *Repository roles and tasks*;
- collecting code evidence or claiming test results: § *Code evidence and
  testing*;
- writing any change-history row or author attribution:
  `.github/instructions/references/change-history.md` (the single definition
  of the Author and Agent rule).

## Evidence and invented values

Never invent requirements, epics, features, scenarios, tasks, decisions,
sources, issues, repositories, aliases, states, priorities, authors, agents,
test results, or configuration values. When evidence is unavailable, mark the
limitation explicitly instead of inferring a result.

## Unresolved configuration values

Treat a configuration value as unresolved when it is empty where a value is
required, or equals `pending`, `[CONFIGURAR]`, `[PENDIENTE]`, or the value of
`validation.unresolved_marker`.

- Never use an unresolved value as a branch, owner, repository name, URL,
  project number, path, or field value.
- Block every remote or Git operation (branch, checkout, pull, push, pull
  request, issue, Project item, or field update) that depends on an unresolved
  value, report the exact key, and ask the user to resolve it.
- Local drafting that does not depend on the unresolved value may continue.

## Configured values

Use the literal values of `specification.states` (requirements),
`specification.task_states` (tasks), `specification.verification_states`
(E2E), `specification.priorities`, and `github_projects.fields.*` (Project
fields, sizes, estimates); never hardcode them in another language or
spelling. Refer to a specific state by its role (for example, "the
in-development value of `specification.states`"). Emoji are allowed only in
chat reports, never in table cells or requirement fields.

A closed issue never implies completion. When
`workflow.human_validation_required_for_completion` is `true`, set the
completed value of `specification.states` only after recording the human
validation that confirms the behavior.

## Stages and approval gates

Follow `workflow.stages` in their configured order.

- `workflow.approval_required_before_issues`: do not create issues or Project
  items before the user approves the analysis or breakdown.
- `workflow.approval_required_before_implementation`: do not start
  implementation before the user approves the implementation plan.

## Identifiers

Prefixes and patterns come from `identifiers.*`. Never renumber existing
identifiers automatically; report gaps and duplicates. Renumbering requires
explicit user confirmation because it breaks issues, E2E tags, and the
traceability matrix.

## Language and scope of changes

Use `project.language` and the configured paths for operational
documentation; do not silently assume a language, repository, or platform.
Keep changes focused, preserve unrelated work, and update documentation and
traceability when behavior, configuration, or requirements change.

## Portable automation

Do not create, copy, invoke, or depend on PowerShell files (`*.ps1`, `*.psm1`,
`*.psd1`, or `*.ps1xml`) in project-owned artifacts. Implement automation in
Python or another existing cross-platform toolchain, and label shell-neutral
command examples as `console`.
