# Project Trace Kit Operational Guide

This guide describes the requirements and traceability workflow in this repository. Read `.project.yml` for its language, repositories, paths, modules, and enabled integrations.

## Project configuration

Use `project.language` for documentation and resolve requirements paths from `requirements.local_root` and `paths.*`. When `requirements.mode` is `external_repository`, keep this repository as the operational workspace and resolve `requirements.repository.local_path` relative to its root (it may point outside it, for example a sibling directory); never open the requirements repository as a separate workspace, since it holds requirement documents only.

## Working order

1. Review `.project.yml` and resolve the requirements root and enabled modules.
2. Read `.github/instructions/requirements.instructions.md` and `.github/instructions/project-workflow.instructions.md`.
3. Consult the configured sources, decisions, domain model, and glossary before changing requirements.
4. Start requirements work with `@analyst-requirements`: it delegates documentary sources, code discovery, issue and E2E traceability to its subagents and is the only agent that edits epics, the domain model, the glossary, and the matrix.
5. Follow the configured approval workflow, then validate affected documents and links.

Do not infer missing project values or create example requirements as real project data.

## First tasks

These walkthroughs take a new team member through the first real work. Each one lists the `.project.yml` keys that must hold real values (no `validation.unresolved_marker`, by default `[CONFIGURAR]`, and no `pending`), the agent to open, an example prompt, the files it writes, and how to validate. Agents show each proposal and ask for confirmation before writing files or running state-changing commands.

Common validation after changing epics: `python scripts/idx.py build --check` (without `--check` it regenerates the index) and, only when `modules.consolidate_epics` and `features.consolidate_epics.enabled` are `true`, `python scripts/consolidate-epics.py --check`. The full validator runs from a kit checkout, as described in [Validation and Checklist](harness-reference.md#validation-and-checklist).

### Configure the project

- **Prerequisites:** the installed `.project.yml`.
- **Fill:** `project.name`, `project.slug`, `project.description`; `repository.organization`, `repository.name`, `repository.url`; each `repositories[]` entry with `alias`, `slug`, `local_path`, `responsibility`, `stack` and `enabled`; `requirements.repository.*` only in `external_repository` mode. For tasks, also `github_projects.organization`, `github_projects.number`, `github_projects.url` (or `github_projects.required: false`) and `integrations.github_cli.*`. `integrations.codebase_memory.enabled` is optional.
- **Agent:** none; edit the file by hand. Details per key are in [Central configuration](customization-guide.md#central-configuration) and [Repositories and teams](customization-guide.md#repositories-and-teams).
- **Validate:** search `.project.yml` for the marker and classify remaining ones as blocking, optional, or belonging to disabled modules; then run the validator from a kit checkout.

### Add a documentary source

- **Prerequisites:** `project.*`, `requirements.*`, and `paths.*` resolved.
- **Steps:** put the original document in `<requirements root>/sources/` and open `@analyst-requirements`.
- **Example prompt:** "Incorporate `sources/<document>` into the requirements."
- **Writes:** a new `RSRC-N` entry in `<paths.requirement_sources>/requirement-sources.md`, one `REQ-N` decision per requirement in `<paths.decisions>/decisions.md` (through `@analyst-source-traceability`), and, for approved requirements, the epic changes with `refine-epic`, the domain model, the glossary, and the matrix.
- **Validate:** `python scripts/idx.py build --check` and consolidation when enabled. See [Sources, decisions, and traceability](harness-reference.md#sources-decisions-and-traceability).

### Discover requirements in existing code

- **Prerequisites:** the `repositories[]` entry of the code with `alias`, `local_path`, and `enabled: true`. With `integrations.codebase_memory.enabled: true` (optional), `@operator-codebase-memory` installs and indexes CBM with separate approvals and confirms `codebase_memory_project` and `codebase_memory_project_status`.
- **Agent:** `@analyst-requirements`. **Example prompt:** "Discover the requirements of the orders domain in `<alias>`."
- **Flow:** audit (`audit-domain`, written under `<paths.tasks>/<integrations.codebase_memory.evidence_path>/`) → your validation of each finding (approved, defect, or open question) → domain model and glossary (`create-domain-model`) → epic (`refine-epic`) and matrix.
- **Validate:** review the audit's limitations and confidence levels, then `python scripts/idx.py build --check`. See [Evidence with codebase-memory-mcp](harness-reference.md#evidence-with-codebase-memory-mcp).

### Write or improve an epic

- **Prerequisites:** `project.*`, `paths.*`, and `identifiers.*`.
- **Agent:** `@analyst-requirements` (`refine-epic` skill: write, review, or improve). **Example prompt:** "Review `EPIC-1` and complete its missing acceptance criteria."
- **Writes:** the epic under `paths.epics` with its change history, plus the reconciled domain model, glossary, and matrix; the agent regenerates the index with `python scripts/idx.py build` (and `python scripts/consolidate-epics.py` when enabled). Never edit the index by hand.
- **Validate:** `python scripts/idx.py build --check` and consolidation when enabled.

### Link issues and E2E

- **Prerequisites:** issues: `repositories[]` with `slug` and `enabled: true`, and `integrations.github_cli.*`. E2E: `modules.e2e` and `features.e2e.enabled` set to `true` and `features.e2e.*` filled.
- **Agent:** `@analyst-requirements`, which delegates to `@analyst-issue-traceability` and, when E2E is enabled, to `@analyst-e2e-traceability`. **Example prompt:** "Link the scenarios of `FEAT-1-1` to their issues and E2E tests."
- **Writes:** after your confirmation, the Tasks rows, implementation states, and E2E section of the epic, plus the matrix. A closed issue never marks a scenario as completed without human validation.
- **Validate:** `python scripts/idx.py build --check`. See [E2E and retrospective audit](harness-reference.md#e2e-and-retrospective-audit).

### Plan and create tasks

- **Prerequisites:** an approved feature; `repositories[]` (optionally `specialist_agent`), `github_projects.*` (or `github_projects.required: false` to document tasks locally), and `integrations.github_cli.*`.
- **Agent:** `@analyst-requirements` for the analysis (`analyze-impact`, `analyze-requirement`) under `paths.tasks`. **Example prompt:** "Analyze the impact of `FEAT-1-2` and break it down into tasks."
- **Next:** approve the breakdown and use the "Plan and implement feature" handoff to `@orchestrator-implementation`, which prepares the implementation plan, waits for your approval, and hands off to `@product-owner` to create the issues and Project fields. Follow the agent's instructions for the plan.
- **Approval gates:** `workflow.approval_required_before_issues` and `workflow.approval_required_before_implementation`; the user approves, never an agent. See [Agents, skills, and scripts](harness-reference.md#agents-skills-and-scripts).

### Publish the changes

- **Prerequisites:** `repository.default_branch`, `repository.pull_request_target`, and optionally `workflow.analyst_branch_prefix` and `workflow.analyst_commit_tag`.
- **Agent:** `@analyst-requirements` (`run-analyst-workflow` skill). **Example prompt:** "Publish my requirement changes in a pull request."
- **Flow:** it creates your analyst branch from the base branch when missing (or synchronizes it), runs the pre-commit checks (index and, when enabled, consolidation), makes the tagged commit, pushes, and opens the pull request from the template, confirming each command.
- **Validate:** review the pull request checklist. The manual steps are in the [Analyst guide](../analyst-guide.md#pull-requests).

## Minimum contract

The files every installation must include are listed in the
[template contract](harness-reference.md#template-contract) of the harness reference.

## Specialized references

- [Customization Guide](customization-guide.md): identity, `.project.yml`, requirements location, structure, IDs, language, repositories, GitHub Projects, and workflow.
- [Harness Reference](harness-reference.md): requirements model, sources, decisions, traceability, E2E, `codebase-memory-mcp`, agents, skills, scripts, templates, and validation.

## Quick Validation

Validate this project as described in
[Validation and Checklist](harness-reference.md#validation-and-checklist).

Install and configure `codebase-memory-mcp` only with explicit consent, following
[Evidence with codebase-memory-mcp](harness-reference.md#evidence-with-codebase-memory-mcp)
(pinned version, `CBM_ALLOWED_ROOT`, cache location, and separate approvals).

Before finishing, confirm that no secrets, caches, or absolute paths are introduced, and that internal links work.
