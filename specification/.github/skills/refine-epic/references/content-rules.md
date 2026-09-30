# Epic Content Rules

Rules for content written into an epic by `refine-epic` Mode 1 (Write) and
Mode 3 (Improve), and by `analyst-requirements` when it applies approved or
code-derived changes. Mode 2 (Review) checks them through
[checks.md](checks.md).

## Code-derived content

Claims about current code must come from a normalized audit
(`<paths.tasks>/<integrations.codebase_memory.evidence_path>/audit-<domain>-<YYYY-MM-DD>.md`).
Findings the user confirms go from the audit to the epic after
`create-domain-model` has updated `<paths.domain_model>` and
`<paths.glossary>`; they are not registered in `requirement-sources` or as decisions.
Code evidence shows structure, not functional compliance, business value, or
test results.

For code-derived behavior, carry the audit's alias, qualified symbol, file,
commit or generation, and coverage into navigable code links in the epic
references, the feature source, and each affected scenario source; verify
that each link destination exists.

## Source types

The **Source** of features and scenarios accepts these types, without adding
columns. Every source must be a verifiable link; several sources in one cell
are separated by `;`.

| Type | Format |
|---|---|
| Document | document + section |
| Code | alias + qualified symbol + link |
| Test | alias + test path + case name + link |
| Contract | alias + specification file + operation + link |
| Data | alias + migration or entity + link |
| History | `alias#N` of the pull request or issue + link |

Use a relative link within the same repository or a commit permalink across
repositories, and repeat the most specific source in the epic references.
Example cell:

```text
backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214
```

No source type, alone or combined, establishes the configured completed
state: that requires the human validation of
`workflow.human_validation_required_for_completion`.

## Confidence and contradictions

The audit's confidence level stays in the audit; never add it to epic tables.
Copy each audit contradiction that affects a scenario into the feature's
comments table as an open question, citing both sources and the audit ID:

```text
| ESC-3-2-1 | Open question: test_cancel.py#L42 forbids cancelling after shipping, but service.py#L130 allows it for pickup orders. Which behavior is intended? (audit audit-orders-2026-09-27) |
```

Write the question in `project.language`. Do not resolve it yourself. When
the owner answers, adjust the scenario and record the change in the
change-history section, or open a defect; then replace the question with the
answer and its date.

## Traceability matrix

After every requirement change, reconcile `paths.traceability_matrix`
independently of the epic:

- Scenarios discovered in code have no `requirement-sources` entry: set the
  requirement-source column to the audit ID (for example
  `audit-orders-2026-09-27`).
- Behavior that already existed before the kit and never had an issue: the
  scenario takes the configured completed state in the epic only after human
  validation, recorded in the change history. The matrix keeps the configured
  "no issue" task state and states in the evidence/notes column
  `Already implemented; validated by @user on DD/MM/YYYY` (in
  `project.language`). No new state is created for this case.
- Keep the implementation and E2E states independent and use only configured
  values.
