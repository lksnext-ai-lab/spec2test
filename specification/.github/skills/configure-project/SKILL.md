---
name: configure-project
description: Shared GitHub Projects configuration workflow that reads the project, repositories, fields, and labels from .project.yml, resolves field IDs dynamically, and sets issue fields with the bundled Python script (default route) or with GitHub MCP Projects tools when the agent declares them. Use when an issue was created and its GitHub Project item and fields must be set.
---

# Configure Project

Shared configuration used by `create-task` and `manage-epic` to place issues in
the configured GitHub Project and set their fields.

## Activation

Read `github_projects.required` in `.project.yml`:

- `true`: Project items and fields are created and synchronized.
- `false`: skip every Project operation; tasks stay documented locally.

Apply the unresolved-value rule of `project-workflow.instructions.md`. Do not
run any remote operation when `github_projects.organization`,
`github_projects.number`, or the target `repositories[].slug` is unresolved;
ask the user to configure it.

## Configuration sources

| Concern | Keys |
|---------|------|
| Project | `github_projects.organization`, `number`, `url` |
| Repositories | `repositories[]`: `alias`, `slug` (`owner/name`), `responsibility`, `stack`, `enabled` |
| Fields | `github_projects.fields.<Name>` with `type`, `options`, `values`, `pattern`, `default` |
| Labels | `labels.default`, `labels.by_repository.<alias>` |
| Credentials | `integrations.github_cli.token_env_var`, `integrations.github_cli.required_scopes` |

## Fields

Use the exact values declared in `.project.yml`; copy spelling, accents, and
casing literally. Option values depend on `project.language`; never assume
them, read them from the configuration.

| Field | Rule | Value shown as |
|-------|------|----------------|
| Status | one of `fields.Status.options`; new items use `fields.Status.default` | `<Status option>` |
| Priority | one of `fields.Priority.options` (same list as `specification.priorities`); new items use `fields.Priority.default` | `<Priority option>` |
| Size | one of `fields.Size.options`; new items use `fields.Size.default` | `<Size option>` |
| Estimate | one of `fields.Estimate.values` | `<Estimate value>` |
| Epic | text matching `fields.Epic.pattern` (derived from `identifiers.epic.prefix` while it is the kit default or missing) | `<epic prefix>-N`, e.g. `EPIC-N` |

## Choosing the repository

There is no keyword list. Compare the task with the `responsibility` and
`stack` of each enabled alias and pick the matching one; ask the user when
more than one or none matches. `create-task` selects the task profile the same
way.

## Field IDs

Field and option IDs are not stored in any file. Resolve them at run time from
the GitHub API (GitHub MCP tools or GraphQL through `gh`) using the configured
organization and Project number.

## Script (default route)

Use `.github/skills/configure-project/scripts/set-project-fields.py`. It is
the default route because `product-owner` declares no GitHub Projects MCP
tools (their names change between GitHub MCP server versions); use MCP
Projects tools only when the destination adds them to the agent's `tools:`.

Requirements: Python 3.9 or newer; GitHub CLI (`gh`) authenticated with the
token named in `integrations.github_cli.token_env_var` and the scopes in
`integrations.github_cli.required_scopes`.

Behavior:

- It resolves and validates every field and option before changing anything;
  if one is missing, nothing is mutated (not even adding the item).
- Options must match the configured value exactly (spelling, accents, case).
  `--priority` is validated against `github_projects.fields.Priority.options`.
- Without `--status`, it applies `github_projects.fields.Status.default` only
  to items it adds to the Project now; an item already in the Project keeps
  its Status.
- It rejects aliases with `enabled: false` and unresolved values (see the
  canonical rule in `project-workflow.instructions.md`).
- It checks the scopes reported by `gh auth status` against
  `required_scopes` and fails with the `gh auth refresh` command when one is
  missing.

```console
python .github/skills/configure-project/scripts/set-project-fields.py --issue-number 58 --repo "<configured-alias>" --status "<Status option>" --priority "<Priority option>" --size "<Size option>" --estimate 5 --epic "<epic ID>"
```

Parameters:

- `--issue-number` (required): issue number.
- `--repo` (required): alias declared in `repositories`.
- `--status`, `--priority`, `--size` (optional): configured option values.
- `--estimate` (optional): configured estimate value.
- `--epic` (optional): epic ID matching `fields.Epic.pattern`.

The script validates authentication, adds the issue to the Project when
needed, sets the given fields, and prints the Project and issue links. Run it
only after the user approved the issue and its field values.

## Adding a repository

1. Add an entry to `repositories[]` in `.project.yml` with alias, slug,
   local path, responsibility, stack, and `enabled`.
2. Optionally add `labels.by_repository.<alias>`.
3. Run the template validator.

## References

- [Project configuration](../../../.project.yml)
- [Field script](scripts/set-project-fields.py)
- [GitHub MCP server](https://github.com/github/github-mcp-server)
