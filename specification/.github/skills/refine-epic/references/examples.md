# Example: Review and Improve

Values below use the template defaults (`EPIC`/`FEAT`/`ESC` prefixes, Spanish
`project.language`, `zero_padding: false`). Always use the configured values.

**User:** "Review epic 4."

The agent reads `epic-4-orders.md`, the template, the glossary, and
`.project.yml`, then reports in chat:

```markdown
## Review of EPIC-4: Order management

### Errors (1)
1. ESC-4-2-3: scenario state "En Desarrollo" is not a configured value
   (configured: "En desarrollo").

### Warnings (2)
1. FEAT-4-2: empty acceptance criteria.
2. Progress summary outdated (counts do not match scenario states).

### Info (2)
1. FEAT-4-1: scenario numbering gap (ESC-4-1-3 missing). Reported only; IDs
   are not renumbered.
2. Term "basket" is not in the glossary.

### Summary
- Errors: 1 | Warnings: 2 | Info: 2
- Features: 3 total, 1 with gaps
- Scenarios: 11 total, 0 not following the acceptance criteria format

Do you want me to switch to Improve mode for the errors and warnings?
```

**User:** "Yes."

The agent proposes the state fix and the progress summary recount as one
mechanical change, and a draft of the FEAT-4-2 acceptance criteria written in
`specification.acceptance_criteria_format`. After confirmation it applies them,
updates the last-updated date, and adds a change history row. The numbering gap
stays untouched.
