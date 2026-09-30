# EPIC-[N]: [Descriptive title]

**Status:** [status configured in specification.states]

**Owner:** @[user]

**Created:** DD/MM/YYYY

**Last updated:** DD/MM/YYYY

**Priority:** [configured priority]

## Overview

[Epic purpose and business value]

## Feature Index

- [FEAT-N-M: Feature name](#feat-n-m-feature-name)

## Dependencies

- [EPIC-N or external dependency]

## References

- [Source document](path or URL)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result.

---

## FEAT-N-M: [Feature name]

Features use an action verb. Scenarios describe concrete states or situations.

**Source:** [one or more sources separated by `;`: document, code, test, contract, data, or history, each with a verifiable link]

**Priority:** [configured priority]

**Status:** [configured status]

**Owner:** @[user]

**Description:** [What it must do and why it matters]

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-N-M-K | [Name] | [Description] | [configured status] | [sources separated by `;`, each with a verifiable link] |

### Comments

| Scenario ID | Comments |
|--------------|-------------|
| ESC-N-M-K | [Review comment, or open question from an audit contradiction citing both sources and the audit ID] |

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|
| ESC-N-M-K | [<alias>#N](<issue URL>) | [task status] | [repository alias] | [Description] |

### Acceptance Criteria

- [ ] Given [precondition], when [action], then [result]

### Technical Notes

[Development considerations]

### Testing Notes

[Testing considerations]

## Progress Summary

[Summary generated or updated according to the configured workflow]

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| DD/MM/YYYY | @[user] | [Change description] | [Agent and visible model, or - if manual] |
