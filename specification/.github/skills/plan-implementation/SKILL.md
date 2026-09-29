---
name: plan-implementation
description: Used by orchestrator-implementation to consolidate the approved analysis and per-repository technical input into <paths.tasks>/<FEAT-id>/implementation-plan.md from the configured implementation plan template, ready for human approval. Use when an approved analysis must become an implementation plan.
---

# Plan Implementation

Consolidates the technical plan for one feature across the enabled repositories
into a single document that `orchestrator-implementation` presents for human
approval before any task is created or implemented.

## Inputs

| Input | Required | Source |
|-------|----------|--------|
| Analysis | Yes | `<paths.tasks>/<feat-id>/analysis-<feat-id>.md` (from `analyze-requirement`) |
| Feature and scenarios | Yes | Epic under `paths.epics` |
| Repository configuration | Yes | `repositories[]` in `.project.yml` (alias, slug, responsibility, stack, default_branch, specialist_agent) |
| Per-repository technical input | When available | The alias `specialist_agent`, or a local read-only inspection recorded as a limitation when none is configured |

Use only enabled aliases. If a required value is unresolved (see the
unresolved-value rule in `project-workflow.instructions.md`), record it as a
blocking dependency in the plan.

## Output

- **File:** `<paths.tasks>/<FEAT-id>/implementation-plan.md`. One file per
  feature, alongside its `analysis-<FEAT-id>.md`; the installer does not seed
  it, since the feature ID is not known until planning happens.
- **Template:** `<paths.templates>/template-implementation-plan.md`. Keep its
  sections, order, and headings; write in `project.language`.
- If the file already exists for this feature (a previous planning pass), ask
  the user whether to replace it or increase the plan version before writing.

## Workflow

1. Read the analysis, the feature, the template, and `.project.yml`.
2. Fill the template:
   - Feature ID, configured status value, date, plan version, and an approval
     requirement of pending.
   - Objective and scope: included scenario IDs and out-of-scope items.
   - Technical contract: shared interfaces between aliases (operations,
     events, data). Reference the provider alias; do not duplicate its detail.
   - Tasks by repository: one row per implementable task with the configured
     alias, dependencies, and status. Tasks here are planned, not created.
   - Order and dependencies: providers of a contract before its consumers;
     independent tasks may run in parallel. Do not impose a fixed layer order.
   - Validation: test commands and checks per alias stack.
   - Risks and decisions consolidated from the analysis and technical input.
3. Present the plan in chat and ask for approval. Record the approver and date
   in the approval section only after the user confirms.
4. When `workflow.approval_required_before_issues` or
   `workflow.approval_required_before_implementation` is `true`, the
   orchestrator must not create tasks or start implementation until approval
   is recorded.

## Consolidation checklist

- [ ] Every scenario from the analysis is covered by at least one task.
- [ ] Every alias in the plan is enabled in `.project.yml`.
- [ ] The technical contract is consistent between provider and consumers.
- [ ] Cross-repository dependencies are explicit.
- [ ] Risks from all inputs are consolidated.
- [ ] The approval section is pending until the user approves.

## Anti-patterns

- Duplicating layer-by-layer detail that belongs to each repository.
- Marking work as parallel when a new contract dependency exists.
- Creating issues or code from this skill.
- Omitting the human approval checkpoint.
