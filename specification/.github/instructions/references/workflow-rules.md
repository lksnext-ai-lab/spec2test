# Project Workflow Reference Rules

Detailed workflow rules referenced by the always-loaded core in
`.github/instructions/project-workflow.instructions.md`. This file is not
auto-injected: read the section you need when the core, an agent, or a skill
points to it. Section names below are stable anchors; other files cite them as
`workflow-rules.md` § *Section*.

## Evidence

- Preserve traceability between requirements, implementation tasks, code
  changes, and verification evidence.
- Keep implementation status separate from E2E verification status and test
  results.
- A code capability, an issue, or a Gherkin scenario does not by itself prove
  that a requirement is implemented or that a test has passed.

## Requirement documents

Before creating or changing a requirement document:

1. Read `.project.yml` and resolve the configured requirements root.
2. Read the applicable instruction files under `.github/instructions/`.
3. Read the configured templates, domain model, glossary, and source records.
4. Preserve existing identifiers and add change-history evidence where
   required.
5. Validate the affected requirements and links before reporting completion.

Resolve the requirements paths, in both `same_repository` and
`external_repository` mode, as defined in the *Requirements root* section of
`.github/instructions/requirements.instructions.md` (the canonical path table:
requirement paths under the requirements root, `paths.plans` and `paths.tasks`
under the main repository root, and the main repository as the only
operational workspace). Do not create a second assumed `requirements/` root in
the implementation repository.

Refer to template sections by their role (for example, "the scenarios table of
the epic template" or "the change-history section of the template") and reuse
the literal headings of the installed templates.

E2E sections and E2E workflows apply only when both `modules.e2e` and
`features.e2e.enabled` are `true`.

## Collaboration and change control

- Make changes through the repository's configured review workflow.
- Do not commit directly to the configured base branch or merge your own
  change without the required review.
- Analyst documentation branches and commits use
  `workflow.analyst_branch_prefix` and `workflow.analyst_commit_tag`.
- Reference issues in commits and pull requests with `Refs #N`; never use
  closing keywords such as `Closes`, `Fixes`, or `Resolves`, because
  completion requires human validation.
- Do not delete existing requirements, sources, decisions, or evidence without
  an explicit decision and a traceable replacement.
- Files generated inside ignored dependency or environment directories, such
  as `.venv` or `node_modules`, are not project artifacts and must not be
  committed or copied into prepared destinations.

## Repository roles and tasks

- Use only repository aliases declared in `.project.yml`.
- The main repository is `repository.organization`/`repository.name`; each
  implementation repository is identified by `repositories[].slug`
  (`owner/name`) and its base branch is `repositories[].default_branch`, or
  `repository.default_branch` when that field is empty.
- A repository specialist agent exists only when
  `repositories[].specialist_agent` names an agent file under
  `.github/agents/`. When it is empty, the delegating agent performs a local
  read-only inspection of that repository and records it as a limitation.
- Tasks represent implementation work and must not be used to claim E2E
  coverage or test success.
- Link tasks to the relevant scenario and issue only when the relationship is
  supported by evidence.
- Do not create fictitious tasks, issues, or project-board values.

## Code evidence and testing

When code evidence is needed, use the configured codebase-memory integration
when it is enabled. Record the repository alias, project, commit or
generation, query scope, and limitations. If the integration is unavailable,
use local search and state the reduced scope of evidence. Audits are stored
under
`<paths.tasks>/<integrations.codebase_memory.evidence_path>/audit-<domain>-<YYYY-MM-DD>.md`.

When tests are available:

- reference requirement IDs in test names or evidence where the project
  convention supports it;
- report the exact command, date, commit, and result when claiming
  verification;
- do not convert a scenario into a passed test without an explicit result.

## Change history

The change-history attribution rule (Author and Agent) is defined only in
`.github/instructions/references/change-history.md`.
