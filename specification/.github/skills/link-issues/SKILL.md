---
name: link-issues
description: Queries open and closed GitHub issues in the configured repositories, matches them to the scenarios of a feature, and proposes Tasks table rows, scenario implementation states, and traceability matrix updates; never manages the E2E section. Use when a feature's scenarios must be linked to GitHub issues or its implementation state refreshed.
---

# Link Issues

Answers: *"Which issues correspond to each scenario of this feature, and what
is its implementation state?"*

It does not determine E2E validation; that belongs to `link-e2e`.

## Allowed tools

Issue read tools of the GitHub MCP server only:

| Tool | Purpose |
|------|---------|
| `github/list_issues` | List open and closed issues of a repository |
| `github/search_issues` | Search issues by scenario or feature ID |
| `github/issue_read` | Read one issue body when the match is unclear |

Do not use pull request, release, Actions, or write tools.

## Configuration

Read `.project.yml`:

- `repositories[]`: enabled aliases; owner and repository from each `slug`
  (`owner/name`). Skip aliases whose slug is unresolved (see the
  unresolved-value rule in `project-workflow.instructions.md`) and report
  them.
- `identifiers.feature.pattern`, `identifiers.scenario.pattern` (defaults
  `FEAT-N-M`, `ESC-N-M-K`).
- `specification.task_states`: values for the Tasks table (roles: open issue,
  closed issue, no issue).
- `specification.states`: values for scenarios.
- `workflow.human_validation_required_for_completion`.

Write every state literally as configured; no emoji in the file.

## Workflow

### 1. Read the feature

Resolve the epic under `paths.epics`, read the feature, its scenarios, and any
existing Tasks rows.

### 2. Query issues

For every enabled alias, query both open and closed issues. Prefer
`github/search_issues` with the feature and scenario IDs; fall back to
`github/list_issues` with pagination and filter by title and body.

### 3. Match issues to scenarios

- Scenario ID in the title or body: confident match.
- Same domain and action without ID: probable match; ask the user to confirm.
- No clear match: leave the scenario with the configured "no issue" task state.

One scenario can have issues in several aliases: one row per issue, repeating
the scenario ID. Never merge repositories into one row.

### 4. Propose Tasks table rows

Use the columns of the template's Tasks table:

```markdown
| <scenario ID> | [<alias>#N](<issue URL>) | <configured open or closed task state> | <alias> | <description> |
| <scenario ID> | - | <configured no-issue task state> | - | No linked issue |
```

### 5. Derive the scenario implementation state

| Issue evidence | Scenario state (configured value by role) |
|----------------|--------------------------------------------|
| No issue | Keep the current state. A scenario already in the configured completed state with recorded human validation (for example behavior implemented before the kit) is never downgraded for lacking an issue |
| At least one open issue | The configured in-development state |
| All issues closed | The configured in-development state, or the configured testing state when verification is actually in progress |
| All issues closed and human validation recorded | The configured completed state |

A closed issue is evidence about the task, never proof that the scenario is
completed. Completion requires recorded human validation when
`workflow.human_validation_required_for_completion` is `true`. Never downgrade
a more advanced state already in the file; report the discrepancy instead.
In the traceability matrix such a scenario keeps the configured "no issue" task
state with an evidence note of the prior implementation and its validation
(see the traceability matrix rules of `refine-epic`).

### 6. Propose the traceability matrix updates

For each affected scenario, propose the values of the `Issue / task` and
`Implementation status` columns of its row in `paths.traceability_matrix`
(one row per scenario, as the matrix template defines), using the configured
task state of its Tasks rows literally. Never propose values for the E2E
columns.

### 7. Return the proposal; `analyst-requirements` applies it

This skill never writes the epic or the matrix. It returns the proposed Tasks
rows, the proposed scenario states, the proposed matrix values, and the
conflicts found. Only `analyst-requirements` applies them, after explicit user
confirmation: it updates the feature's Tasks table, the state column of its
scenarios table, and the matrix rows, never touches the E2E section or E2E
columns, and adds a row to the change-history section recording Author and
Agent per `.github/instructions/references/change-history.md`.

## Chat report

Emoji are allowed in the chat report only:

```markdown
## Result: <feature ID> - <title>

Implementation: 3/5 scenarios with issues (1 open, 2 closed, awaiting validation)

| Scenario | Issue | Alias | Issue state | Title |
|----------|-------|-------|-------------|-------|
| <scenario ID> | <alias>#42 | <alias> | closed | <issue title> |
| <scenario ID> | - | - | no issue | - |

Proposed Tasks rows: <rows ready to paste>

Proposed matrix values:

| Scenario | Issue / task | Implementation status |
|----------|--------------|-----------------------|
| <scenario ID> | <alias>#42 | <configured closed task state> |
| <scenario ID> | - | <configured no-issue task state> |
```

If nothing is found: "No issues were found for <feature ID> in the enabled
repositories."

## Notes

- Always query open and closed issues.
- Issues created by `create-task` contain the scenario IDs in the body; use
  them as the strongest match signal.
- Include every issue for a scenario (original and follow-up fixes), one per
  row.
- Never modify the epic; return the proposal to `analyst-requirements`.
