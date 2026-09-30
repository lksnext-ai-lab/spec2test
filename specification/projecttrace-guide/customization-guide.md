# Customization Guide

This guide describes how to maintain project decisions and configuration as the requirements and domain evolve.

## Principles

Keep these concerns separate:

- **Reusable methodology:** requirements structure, identifiers, traceability, acceptance criteria, and workflow.
- **Project configuration:** names, paths, repositories, tools, owners, and statuses.
- **Domain content:** epics, features, scenarios, glossary, sources, and decisions.

Review affected files and links across the repository whenever a configuration or domain decision changes.

## Decision log

Record human preparation decisions in this section of this file
(`projecttrace-guide/customization-guide.md` in the destination), replacing the
example row; `analyst-quality-auditor` reads the log here and compares it with
`.project.yml`. Use a table such as:

| ID | Decision | Confirmed value | Rationale | Impact | Affected files | Status |
|----|----------|-----------------|-----------|--------|----------------|--------|
| BOOT-N | [Question or decision] | [Value] | [Rationale] | [Impact] | [Paths] | Active |

`.project.yml` keeps operational values; the log keeps context, rationale, impact, and scope. When a decision changes, add a linked entry. For manual installations use `manual` or `not applicable`.

## Central configuration

Complete `.project.yml` before running automation. Review:

- `project`: name, slug, description, and language.
- `repository`: the project repository, its default branch (`default_branch`), and the Pull Request target (`pull_request_target`).
- `requirements`: `same_repository` or `external_repository` mode and external data.
- `paths`: `epics`, `templates`, `decisions`, `requirement_sources`, `domain_model`, `requirements_index`, and `traceability_matrix` are resolved under `<requirements.local_root>/<paths.requirements>`; `plans` and `tasks` are relative to the project repository root.
- `identifiers`: prefixes, patterns, names, and numbering.
- `repositories`: aliases, responsibilities, paths, and technologies.
- `github_projects`: organization, number, URL, fields, and options.
- `workflow`, `specification`, `integrations`, and `features`.
- `workflow.analyst_branch_prefix` and `workflow.analyst_commit_tag`: analyst branch prefix and commit/Pull Request tag. When empty, the `en` defaults are `analyst/` and `[ANALYSIS]`.

## Requirements location

Choose exactly one mode:

```yaml
requirements:
  mode: "same_repository"
```

With `same_repository`, paths are resolved from `requirements.local_root`.

```yaml
requirements:
  mode: "external_repository"
  repository:
    organization: "organization"
    name: "requirements-repository"
    url: "https://github.com/organization/requirements-repository"
    local_path: "../requirements-repository"
  local_root: "."
```

With `external_repository`, paths are resolved from `requirements.local_root` inside the external repository. Verify `paths.epics`, `paths.templates`, `paths.domain_model`, and `paths.traceability_matrix` when enabled. The installed scripts already read `requirements.mode` before looking for files.

## Structure and identity

Decide the paths for:

```text
requirements/
requirements/sources/
requirements/epics/
requirements/templates/
requirements/domain-model.md
requirements/domain-model/glossary.md
requirements/decisions/
requirements/requirement-sources/
plans/
tasks/
```

If names change, update only `.project.yml`: instructions, agents, skills, and scripts resolve paths and identifiers from it. The validator, `idx.py`, and `consolidate-epics.py` read `identifiers.*.prefix` (one alphanumeric word, no hyphens, three distinct values); when you change a prefix, the installer rewrites the patterns that still hold the kit default (`identifiers.*.pattern`, `github_projects.fields.Epic.pattern`, and the E2E `tag_pattern`) and reports them as `derived_patterns`; patterns you customized are kept. In an existing destination, run the installer again in `integrate` mode to apply it. If the recommended hierarchy is retained, document:

```text
EPIC-N -> FEAT-N-M -> ESC-N-M-K -> TASK-N
```

Define leading zeroes, ranges, ID reuse rules, filename format, and E2E tag format.

## Language and domain

Customize documentation and user-facing language, technical names, terms that remain in English, date format, and official vocabulary. The glossary must define entities, roles, statuses, actions, relationships, ambiguous synonyms, and acronyms before new epics or scenarios are drafted.

## Repositories and teams

For every repository define its alias, location, responsibility, technology, owners, branches, commit convention, pull-request destination, and review rules. Example:

| Alias | Repository | Responsibility | Local path | Technology |
|-------|------------|----------------|------------|------------|
| backend | organization/repository | API and persistence | ../backend-repository | [stack] |
| frontend | organization/repository | Interface and client | ../frontend-repository | [stack] |
| tests | organization/repository | E2E tests | ../e2e-repository | [stack] |
| management | organization/repository | Requirements and management | . | Markdown |

## GitHub Projects

Read `github_projects.required` first:

- `true`: complete organization, number, URL, fields, statuses, options, and permissions.
- `false`: do not run synchronization, field, or item-creation commands.

If GitHub is not used, replace the workflow with the selected tool and remove dependencies on `gh` or MCP.

## Workflow and final adaptation

Confirm each stage's input, owner, output, tool, completion criterion, and
approval. Stage identifiers come from `workflow.stages` and are used literally:

```text
specify -> analyze -> plan -> approve -> create_tasks -> implement -> test -> trace
```

Recommended order: identity, structure, repositories, IDs, statuses, glossary, templates, scripts, skills, agents, validations, and the first test epic.
