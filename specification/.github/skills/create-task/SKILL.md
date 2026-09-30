---
name: create-task
description: Creates a structured task issue for a repository alias configured in .project.yml, choosing the task profile from the alias responsibility and stack, and links it to the epic after approval. Use when an approved breakdown task must become a GitHub issue.
---

# Create Task

Creates one traceable task issue in a configured repository and links it to the
requirement scenarios it implements.

> Epic-level issues belong to `manage-epic`. Requirement files belong to
> `refine-epic`.

## Preconditions

1. Read `.project.yml`. Resolve the target alias in `repositories[]`; it must
   be `enabled`. Owner and repository come from its `slug` (`owner/name`).
2. When `workflow.approval_required_before_issues` is `true`, confirm that the
   implementation plan (`<paths.tasks>/<FEAT-id>/implementation-plan.md`) or
   the requirement is approved. Otherwise stop and report.
3. Apply the unresolved-value rule of `project-workflow.instructions.md`. Do
   not create issues or Project items when the slug, organization, or Project
   number is unresolved.
4. When `github_projects.required` is `false`, document the task locally and
   skip Project operations.

## Choose the task profile

Read `responsibility` and `stack` of the target alias. Do not assume
technologies; use only `repositories[].stack`.

| Target | Reference |
|--------|-----------|
| Alias whose responsibility is services, APIs, data, or business logic | [references/backend.md](references/backend.md) |
| Alias whose responsibility is user interface or presentation | [references/frontend.md](references/frontend.md) |
| Cross-cutting or non-code work (documentation, specification, ADR, CI/CD, infrastructure, coordination) | [references/management.md](references/management.md) |

If the responsibility is ambiguous or covers several types, ask the user.

## Task structure

Every task, whatever its profile, contains:

1. **Title:** `[Verb] [object] [context]`, short and action-oriented, in
   `project.language`.
2. **Objective:** what the task achieves and why.
3. **Traceability:** epic, feature, and scenario IDs using the configured
   patterns (`identifiers.*.pattern`), plus a link to the epic file.
4. **Acceptance criteria:** at least three verifiable items, written in
   `specification.acceptance_criteria_format` when they describe behavior.
5. **Type-specific details:** from the selected reference.
6. **Dependencies:** `#N` for the same repository, `<alias>#N` for other
   configured aliases only.
7. **Project metadata:**
   - Status: `github_projects.fields.Status.default`.
   - Priority: one of `github_projects.fields.Priority.options`.
   - Size: one of `github_projects.fields.Size.options`.
   - Estimate: one of `github_projects.fields.Estimate.values`.
   - Epic: the epic ID matching `github_projects.fields.Epic.pattern`.
   - Labels: `labels.default` plus `labels.by_repository.<alias>`. Add other
     labels only if they already exist in the repository and the user agrees.

Copy option values literally (spelling, accents, casing). Never translate them.

## Workflow

1. **Analyze:** confirm scenarios, target alias, dependencies, and epic.
2. **Draft:** present the complete task in chat for review. Do not call any
   write tool yet.
3. **Create after explicit approval:** create the issue with `github/issue_write`
   (method `create`) in the alias repository. Report the link.
4. **Project fields:** add the issue to the configured Project and set its
   fields with the script described in `configure-project` (the default
   route), or with GitHub MCP Projects tools when the agent declares them.
5. **Link to the epic after confirmation:** add a row to the feature's Tasks
   table: scenario ID, issue link, the configured open value of
   `specification.task_states`, alias, and description. One row per scenario.
   Add a change history row and record Author and Agent per
   `.github/instructions/references/change-history.md`.

## Validation checklist

- [ ] Target alias is enabled and fully configured.
- [ ] Title is action-oriented; objective and traceability are present.
- [ ] At least three verifiable acceptance criteria.
- [ ] Type-specific details come from the selected reference and the alias stack.
- [ ] Dependencies use configured aliases only.
- [ ] Every metadata value exists in `.project.yml`.
- [ ] Content uses `project.language`.
- [ ] No issue was created before explicit approval.

## References

- [configure-project](../configure-project/SKILL.md) for Project fields.
- `.project.yml` for aliases, labels, and field options.
