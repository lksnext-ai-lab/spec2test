# Management Task Details

Use for cross-cutting or non-code work: documentation, specifications,
architecture decision records (ADR), guides, procedures, CI/CD,
infrastructure, and cross-repository coordination. Create the issue in the
alias whose responsibility covers that work; if none exists, ask the user which
configured alias to use.

Epic-level issues are not management tasks; use `manage-epic`.

## Technical details

- **Deliverable type:** documentation, specification, ADR, guide, procedure,
  pipeline or infrastructure change, or coordination.
- **Location:** target path in the repository, discovered from its structure.
- **Audience:** who uses the deliverable.
- **Format:** Markdown; diagrams when useful.
- **Related work:** tasks being documented or coordinated, as `<alias>#N`.

## Minimum acceptance criteria

- Deliverable created at the agreed location.
- Links and diagrams work.
- Reviewed by the stakeholders named in the task.
- Linked from the relevant index.

## Deliverable skeletons

ADR:

```markdown
# ADR-N: <Decision title>

## Status
<Proposed | Accepted | Rejected | Deprecated>

## Context
## Decision
## Consequences
## Alternatives Considered
## References
```

Guide:

```markdown
# Guide: <Title>

## Introduction
## Prerequisites
## Steps
## Troubleshooting
## Additional Resources
```

Write headings in `project.language` when the deliverable is project
documentation.

## Coordination tasks

List the related tasks per configured alias, their order, and the contracts
that block consumers. Estimate is the value the team agrees on from
`github_projects.fields.Estimate.values`.

## Example

Values are illustrative; aliases, labels, and field options come from
`.project.yml` (defaults shown).

- **Title:** Document the invoice numbering decision as an ADR
- **Objective:** Record why invoice numbers are generated per fiscal year.
- **Traceability:** EPIC-3 / FEAT-3-1
- **Acceptance criteria:**
  - [ ] ADR created with context, decision, and alternatives
  - [ ] Reviewed by the technical lead
  - [ ] Linked from the architecture index
- **Metadata:** Status `<fields.Status.default>`, Priority `<Priority option>`
  and Size `<Size option>` (values of `github_projects.fields.Priority.options`
  and `github_projects.fields.Size.options`, copied literally),
  Estimate `2`, Epic `EPIC-3`.
