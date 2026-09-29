---
name: manage-epic
description: Creates and tracks the epic-level GitHub issue that groups the task issues of one requirement epic across configured repositories; task issues themselves are created with create-task. Use when a complete feature or multi-repository initiative needs an epic-level issue.
---

# Manage Epic Issue

Creates and maintains the **epic-level issue** in GitHub for an existing
requirement epic. It never creates task issues (use `create-task`) and never
edits requirement files beyond the change history (use `refine-epic`).

## Preconditions

1. Read `.project.yml`. The requirement epic must exist under `paths.epics`.
2. Create the epic issue in the repository whose alias responsibility covers
   coordination or requirements; when none is configured, use the main
   repository (`repository.organization`/`repository.name`). Ask the user when
   unclear.
3. When `workflow.approval_required_before_issues` is `true`, confirm the
   requirement epic is approved before creating any issue.
4. Apply the unresolved-value rule of `project-workflow.instructions.md`. Do
   not run remote operations that depend on an unresolved value.

## Epic issue structure

Write in `project.language`:

1. **Title:** `<epic ID>: <capability name>`, where the epic ID follows
   `identifiers.epic.pattern` (default `EPIC-N`).
2. **Summary:** what is built and why; link to the requirement epic file.
3. **Business objectives.**
4. **Scope:** included features (by configured feature ID) and out of scope.
5. **Tasks by repository:** one block per enabled alias that participates,
   listing its task issues as a checklist (`- [ ] <alias>#N - <title>`). Only
   aliases present in `repositories[]`; blocks are filled as `create-task`
   creates the issues.
6. **Dependencies:** order between aliases based on real contracts (a provider
   finishes a contract before its consumers).
7. **Epic acceptance criteria:** reference the requirement epic's criteria;
   completion requires recorded human validation when
   `workflow.human_validation_required_for_completion` is `true`.
8. **Risks and mitigations.**

## Project metadata

- Status: `github_projects.fields.Status.default`.
- Priority: one of `github_projects.fields.Priority.options`.
- Size: one of `github_projects.fields.Size.options`.
- Estimate: one of `github_projects.fields.Estimate.values` (or the value the
  team agrees on).
- Epic: the epic ID, matching `github_projects.fields.Epic.pattern`.
- Labels: `labels.default` plus `labels.by_repository.<alias>`; others only
  if they exist and the user agrees.

Copy option values literally.

## Workflow

1. **Analyze:** read the requirement epic; identify participating aliases and
   dependencies.
2. **Draft:** present the full epic issue in chat. Do not call write tools yet.
3. **Create after explicit approval:** `github/issue_write` (method `create`),
   then add it to the configured Project and set its fields (see
   `configure-project`). Report the link.
4. **Break down:** for each task, use `create-task`; each task gets the same
   Epic field value.
5. **Track:** keep the checklist in the epic issue current. A closed task issue
   is not a completed requirement; requirement states are updated through
   `link-issues` and human validation.
6. **Close:** only after the user confirms that the acceptance criteria are met
   and human validation is recorded. Record Author and Agent per
   `.github/instructions/references/change-history.md` in the
   requirement epic's change history.

## References

- [configure-project](../configure-project/SKILL.md)
- [create-task](../create-task/SKILL.md)
- [refine-epic](../refine-epic/SKILL.md)
