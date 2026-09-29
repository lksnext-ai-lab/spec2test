# Frontend Task Details

Use for aliases responsible for user interface or presentation. Adapt every
item to the alias `stack` in `.project.yml`; name frameworks, components, and
file locations only as they exist in that repository.

## Design reference

When the user or the requirement provides a design link (for example a design
file or frame), include it in a **Design** section and treat it as the visual
reference. When no design link is provided, omit the section; do not invent
one.

## Expected behavior

Describe the flow from the user's perspective:

1. What the user sees on entry.
2. Available actions.
3. Interaction feedback (validation, loading, navigation).
4. Empty, error, and success states.

## Technical details

Include the items that apply:

- **Screens and components:** to create, modify, or reuse, discovered from the
  repository or a domain audit.
- **Navigation:** route or entry point and access restrictions (roles or
  permissions as defined by the project).
- **State and data:** data sources, client-side state, and the backend
  operations consumed (reference the providing task as `<alias>#N`).
- **Validation:** fields, rules, and error display.
- **Responsive and accessibility:** breakpoints and semantic or ARIA needs.
- **Performance:** lazy loading, debouncing, or virtualization when relevant.

## Minimum acceptance criteria

- Behavior matches the linked scenarios.
- Empty, loading, error, and success states handled.
- Visual consistency with the design reference, when one is provided.
- Basic accessibility.
- Automated tests with the repository's test tooling; the repository's type or
  lint checks pass.

## Principles

1. Describe what should happen; technical details are guidance.
2. Each criterion is verifiable without ambiguity.
3. No code snippets unless the user requests them.

## Example

Values are illustrative; aliases, labels, and field options come from
`.project.yml` (defaults shown).

- **Title:** Show the invoice list with filters
- **Objective:** Let users find invoices by date and status.
- **Traceability:** EPIC-3 / FEAT-3-2 / ESC-3-2-1
- **Expected behavior:** the list loads with a loading indicator, shows an
  empty message when there are no invoices, and filters update the list.
- **Acceptance criteria** (behavioral items use
  `specification.acceptance_criteria_format`; shown in English here):
  - [ ] Given a user with invoices, when they filter by status, then they see
        only invoices in that status
  - [ ] Empty and error states are shown with clear messages
  - [ ] Automated tests cover filtering and empty state
- **Dependencies:** `<backend-alias>#21` (invoice list operation)
- **Metadata:** Status `<fields.Status.default>`, Priority `<Priority option>`
  and Size `<Size option>` (values of `github_projects.fields.Priority.options`
  and `github_projects.fields.Size.options`, copied literally),
  Estimate `5`, Epic `EPIC-3`.
