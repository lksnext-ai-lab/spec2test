# Implementation Plan: [Feature Name]

**Feature:** FEAT-N-M

**Status:** [configured status]

**Date:** DD/MM/YYYY

**Approval requirement:** [Pending / Approved / Rejected]

**Plan version:** [N]

## Input and Output

- **Input:** approved analysis
  (`<paths.tasks>/<feat-id>/analysis-<feat-id>.md`), feature scenarios, and
  repository configuration from `.project.yml`.
- **Output:** implementable tasks by repository, identified dependencies,
  validation criteria, and a recorded approval decision.
- **Rule:** this document does not create requirements, scenarios, or GitHub tasks;
  it plans them for later approval.

## Objective

[Expected technical result]

## Scope

[Included scenario IDs and out-of-scope items]

## Technical Contract

[API contract, events, or shared interfaces. Freeze before assigning tasks.]

## Workflow

1. **Analyze:** confirm impact, reuse, modifications, and new elements.
2. **Plan:** complete scope, contract, tasks, dependencies, risks, and validation.
3. **Approve:** obtain human validation before creating tasks or implementing.
4. **Create tasks:** record traceable units in the configured repositories and Project.
5. **Implement:** execute tasks according to their order and dependencies.
6. **Test and trace:** validate the result and update traceability.

## Tasks by Repository

| ID | Repository Alias | Task | Dependencies | Status |
|----|------------------|------|--------------|--------|
| <alias>-N | [configured alias] | [Description] | [TASK/issue] | [configured status] |

Each task must be an implementable and traceable unit. The repository alias must
exist and be enabled in `.project.yml`.

## Order and Dependencies

[Execution order and dependencies between tasks]

## Validation

- [ ] Automated tests
- [ ] Functional validation
- [ ] Traceability updated
- [ ] UTF-8 encoding validated
- [ ] No unresolved dependencies remain

## Approval

- **Approved by:** @[user]
- **Approval date:** DD/MM/YYYY
- **Decision:** [Approved / Rejected / Pending]
- **Notes:** [Review comments]

## Risks and Decisions

- [Risk, impact, and mitigation]
- [Relevant decision]

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| DD/MM/YYYY | @[user] | [Change description] | [Agent and visible model, or - if manual] |
