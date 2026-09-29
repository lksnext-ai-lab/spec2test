# Backend Task Details

Use for aliases responsible for services, APIs, data, or business logic. Adapt
every item to the alias `stack` in `.project.yml`; name frameworks, tools, and
file locations only as they exist in that repository.

## Technical details

Include the items that apply:

- **Interface:** operation, method and path (or message/event), request and
  response contract, error responses.
- **Data:** entities or tables affected, fields, constraints, indexes, and the
  schema migration mechanism the stack uses.
- **Business rules:** validations, calculations, and state transitions tied to
  scenario IDs.
- **Security:** authentication and authorization requirements, input
  sanitization, rate limiting.
- **Performance:** query cost, pagination, caching.
- **Location:** modules or layers to create or modify, discovered from the
  repository or a domain audit, never assumed.

## Minimum acceptance criteria

- Behavior matches the linked scenarios.
- Input validation and error handling for the documented error cases.
- Automated tests for new or changed logic, using the repository's test
  tooling and any coverage threshold the repository defines.
- Public interface documentation updated when the repository publishes one.

## Testing section

State the test levels the task requires:

- **Unit tests:** business rules and validations listed above.
- **Integration tests:** interface and persistence behavior for the linked
  scenarios.

## Example

Values are illustrative; aliases, labels, and field options come from
`.project.yml` (defaults shown).

- **Title:** Expose the order list operation
- **Objective:** Return paginated orders so consumers can display them.
- **Traceability:** EPIC-2 / FEAT-2-1 / ESC-2-1-1, ESC-2-1-2
- **Acceptance criteria** (behavioral items use
  `specification.acceptance_criteria_format`; shown in English here):
  - [ ] Given a customer with orders, when they request the list, then they
        receive their orders paginated
  - [ ] Invalid pagination parameters return a documented validation error
  - [ ] Automated tests cover the listed scenarios
- **Technical details:** read operation with page and page size parameters;
  response contains id, date, total, and status.
- **Dependencies:** `#12` (order entity)
- **Metadata:** Status `<fields.Status.default>`, Priority `<Priority option>`
  and Size `<Size option>` (values of `github_projects.fields.Priority.options`
  and `github_projects.fields.Size.options`, copied literally),
  Estimate `3`, Epic `EPIC-2`, labels from `labels.default` and
  `labels.by_repository.<alias>`.
