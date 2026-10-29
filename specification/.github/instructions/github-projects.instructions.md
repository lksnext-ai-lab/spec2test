---
applyTo: '.github/agents/product-owner.agent.md,.github/skills/create-task/**,.github/skills/manage-epic/**,.github/skills/configure-project/**,**/epics/**,**/plans/**,**/tasks/**'
description: 'Guidelines for creating and managing tasks and GitHub Project items. Repository responsibilities and language settings are defined in .project.yml.'
---

# Task and GitHub Projects Instructions

Read `.project.yml` before applying these instructions.

These instructions apply where tasks and Project items are handled: the
`product-owner` agent, the `create-task`, `manage-epic`, and
`configure-project` skills, and the epic, plan, and task documents whose Tasks
tables and change history they update (default `paths.epics`, `paths.plans`,
and `paths.tasks` locations). They are not applied to unrelated files, so
requirement or code work does not load GitHub Projects rules it cannot use.

Use the following configuration values:

- `project.language` for task descriptions, technical documentation, and
  user-facing text.
- `repositories` for repository aliases, slugs, responsibilities, and
  technology stacks.
- `github_projects` for GitHub Projects settings and field definitions.
- `labels.default` and `labels.by_repository` for issue labels.
- `specification.task_states` for task states recorded in requirement files.
- `integrations.github_cli` for the CLI fallback (`enabled`, `token_env_var`,
  and `required_scopes`).

If `.project.yml` is missing, invalid, or does not contain the required
configuration, stop and request clarification. Do not infer repository aliases,
languages, project fields, labels, or workflow states.

Apply the unresolved-value rule of `project-workflow.instructions.md`. Do not
create or synchronize issues, labels, GitHub Projects items, or fields while
any value they depend on is unresolved. The template may retain these markers until project
initialization, but operational workflows must wait until they are replaced with
valid values.

Create issues only after the approval required by
`workflow.approval_required_before_issues`.

The GitHub Projects rules in this file apply only when `github_projects.required`
is `true`.

When `github_projects.required` is `false`, manage tasks locally or through the
configured alternative. Do not run scripts, skills, or tools that synchronize
GitHub Project fields.

## Repository assignment

When creating or updating a task:

1. Assign the task to one enabled repository alias from `repositories` in
   `.project.yml`.
2. Use the repository's configured `responsibility` and `stack` to determine the
   correct assignment.
3. Never invent or assume aliases such as `backend`, `frontend`, or
   `management`.
4. If no repository can be selected confidently, ask for clarification.

The `create-task` skill offers task profiles (for example, server-side,
client-side, and management work) in its `references/` folder. A profile is
selected from the chosen repository's `responsibility` and `stack`; it is not a
repository alias and never replaces the configured alias.

## Task creation

Every task must include:

1. A short, clear, action-oriented title.
2. A description written in `project.language`.
3. The repository assignment.
4. The applicable project fields.
5. The labels resolved from `labels.default` plus `labels.by_repository` for the
   selected alias, when configured.
6. An assignee, if one is known; otherwise leave the task unassigned.

The task description should contain the following sections when relevant:

- Objective
- Acceptance Criteria
- Technical Details
- Dependencies

Reference cross-repository dependencies using the format
`<repository-alias>#<issue-number>`. The alias must exist in `.project.yml`.

## GitHub Project fields

Apply these rules only when `github_projects.required` is `true`.

Use only fields and values defined in `.project.yml`. Never invent additional
fields, options, statuses, or iterations.

### Status

`Status` is required. Its value must be one of the options defined in:

```text
github_projects.fields.Status.options
```

Keep the status up to date.

### Priority

Use only values defined in:

```text
github_projects.fields.Priority.options
```

Apply the field when it is configured and relevant.

### Size

Use only values defined in:

```text
github_projects.fields.Size.options
```

Apply the field when it is configured and relevant.

### Estimate

Use only the numeric values defined in:

```text
github_projects.fields.Estimate.values
```

Do not assume that the scale represents points or hours unless `.project.yml`
specifies it.

### Epic

If the `Epic` field is configured, use the format defined in
`github_projects.fields.Epic.pattern` with the configured epic prefix, for
example `EPIC-2` with the default configuration.

Do not create or assign an epic value when the field is not configured or the
relationship is unknown.

### Sprint

Use `Sprint` only when it is explicitly configured in `.project.yml` and the task
belongs to a known sprint.

## Task categorization

Categorize each task according to the responsibility and technology stack of the
configured repository alias.

Do not impose fixed repository categories such as backend, frontend, testing, or
management unless those categories are explicitly defined in `.project.yml`.

## Dependencies

When a task depends on work in another repository:

1. Create the task in the repository that owns the primary responsibility.
2. Reference related tasks using `<repository-alias>#<issue-number>`.
3. Ensure that the alias exists in `.project.yml`.
4. Describe the dependency clearly in the task description.
5. Include a dedicated `Dependencies` section when the dependency affects
   implementation order or delivery.

## Task workflow

When GitHub Projects is enabled:

1. Use only the workflow states configured in
   `github_projects.fields.Status.options`.
2. Update the `Status` field whenever the task's state changes.
3. Do not close, archive, or move a task based solely on assumptions.
4. Preserve existing field values unless the requested change requires updating
   them.
5. A closed issue or a done Project status does not complete a requirement;
   completion follows `workflow.human_validation_required_for_completion`.

## Best practices

- Break large features into small, independently deliverable tasks.
- Use consistent, action-oriented naming.
- Link related tasks with issue references.
- Keep task status and estimates current.
- Add technical details as comments when they are discovered after task creation.
- Assign each task to the repository that owns its primary responsibility.
- Use `Size` and `Estimate` according to their configured meanings.
- Avoid modifying unrelated tasks or project fields.
- Keep task descriptions concise, specific, and testable.

## GitHub tools

Use the GitHub MCP server tools (`github/<tool>`) to create or update tasks and
GitHub Project items when automation is required and those tools are available.
When GitHub CLI is used instead, read the token from the environment variable
named by `integrations.github_cli.token_env_var`, verify the scopes in
`integrations.github_cli.required_scopes`, and never print the token.

If the required tool is unavailable, do not simulate a successful operation.
Report what could not be completed and provide the information needed to perform
the operation manually.
