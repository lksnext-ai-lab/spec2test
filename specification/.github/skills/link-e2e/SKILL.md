---
name: link-e2e
description: Links requirement scenarios to E2E tests in the configured E2E repository by inspecting Gherkin features, scenario tags, step definitions, and capabilities of the configured framework, and proposes changes to the E2E section of epics when E2E is enabled; analyst-requirements applies them. Use when scenarios must be traced to automated E2E verification.
---

# Link E2E Verification

Answers: *"Is there E2E automation for this scenario, and what was its last
result?"*

It does not determine implementation state or query issues; that belongs to
`link-issues`.

## Preconditions

Read `.project.yml`. Run only when both `modules.e2e` and
`features.e2e.enabled` are `true`. Otherwise stop and report that E2E is
disabled; epics must not contain the E2E section in that case.

Resolve `features.e2e.local_path`, `feature_path`, `framework`, `command`,
and `tag_pattern` (default `@ESC-N-M-K`). If any needed value is unresolved
(see the unresolved-value rule in `project-workflow.instructions.md`), stop and
ask the user to configure it.

## Verification states

Use literally the values of `specification.verification_states`, by role:
not defined, declared (Gherkin exists, glue code unconfirmed), in
implementation (partial glue code), implemented (scenario, glue code, and the
required capabilities of the configured framework `features.e2e.framework`
exist), not applicable (with justification). Never add emoji to the
file; emoji are allowed in chat reports only.

## E2E table

The E2E section of each feature (heading from the template for
`project.language`: es `### Verificación E2E`, en `### E2E Verification`)
has the six template columns:

| Scenario ID | E2E Feature | E2E Scenario | Automation | Last result | Evidence |
|-------------|-------------|--------------|------------|-------------|----------|

- **Automation:** a configured verification state.
- **Last result:** only a result that was actually observed (run output or CI
  record); otherwise `-`.
- **Evidence:** link or command that proves the result; otherwise `-`.

## Workflow

1. **Scope:** read the template in `paths.templates` and the requested epic,
   feature, or scenario. Do not modify files yet.
2. **Inspect the E2E repository:** features under `feature_path`, tags matching
   `tag_pattern`, step definitions, framework capabilities, and runner
   configuration. A `.feature` file alone does not prove executable glue code.
   Without tags, match by name and Gherkin text and mark the match as
   provisional. Inventory every Gherkin scenario in candidate features.
3. **Classify:** for each scenario, record correspondence, automation state,
   gaps in glue code or framework capabilities, and assumptions from
   provisional matches. Never classify incomplete work as implemented.
4. **Coverage:** report separately functional IDs with at least one E2E match,
   matching Gherkin rows (each counted once), functional IDs without a match,
   and Gherkin scenarios without a requirement.
5. **Report before editing:** confident, probable, and missing matches;
   automation found; coverage; warnings; the full list of unmatched Gherkin
   scenarios. Reconcile both directions (Gherkin to scenario and scenario to
   Gherkin); if any inventoried scenario is missing from both the table and
   the gap list, the report is invalid.
6. **Propose the traceability matrix updates:** for each affected scenario,
   propose the values of the `E2E feature / tag` and `E2E status` columns of
   its row in `paths.traceability_matrix` (column names as in the matrix
   template for `project.language`; one row per scenario), using the exact
   tag and the configured verification state literally. Never propose values
   for the `Issue / task` or `Implementation status` columns.
7. **Return the proposal; `analyst-requirements` applies it:** after explicit
   confirmation it modifies only the E2E section of the affected features, the
   E2E counts of the progress summary, the E2E columns of the matrix rows, and
   the template's change history section (Author and Agent per
   `.github/instructions/references/change-history.md`). Never modify
   Tasks tables, implementation states, or acceptance criteria.

## Quality rules

- A scenario may map to several Gherkin scenarios: one row each, repeating the
  scenario ID.
- Every inventoried Gherkin scenario ends in a row or in the explicit unmatched
  list.
- Every scenario without Gherkin keeps a row with `-` in E2E Feature and E2E
  Scenario and the configured not-defined or not-applicable state.
- Functional-ID counts and Gherkin-row counts are different metrics.
- Content uses `project.language`, except technical names and tags.

## Output example

Defaults shown; use configured values.

```markdown
| Scenario ID | E2E Feature | E2E Scenario | Automation | Last result | Evidence |
|-------------|-------------|--------------|------------|-------------|----------|
| ESC-2-1-1 | `orders.feature` | List orders of a customer | Implementada | - | `<features.e2e.command>` filtered by `@ESC-2-1-1` |
| ESC-2-1-2 | - | - | No definida | - | - |
```
