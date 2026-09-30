# Traceability Matrix

This matrix is maintained according to `paths.traceability_matrix`.
It links each scenario to its requirement source, specification, implementation,
and, when E2E is enabled, automated verification. It does not replace epics or
`requirement-sources` registers.

## Rules

- One row represents an `ESC-N-M-K` scenario.
- `Requirement source` references the corresponding entry in
  `paths.requirement_sources` or the documentary source identifier. For
  scenarios discovered in code, which have no `requirement-sources` entry, it
  states the originating audit ID (for example `audit-orders-2026-09-27`).
- `Implementation status` only uses the states defined in
  `specification.task_states`.
- `E2E status` is independent and only uses values from
  `specification.verification_states`.
- Issue references use `<alias>#<number>` and E2E tests use the exact
  `@ESC-N-M-K` tag when available.
- A row without an issue or test must remain and explicitly state `No issue` or
  `Not defined`; coverage must not be inferred from implementation status.
- Behavior implemented before the kit was adopted and without an issue keeps
  `No issue` in `Implementation status`, even when the scenario is `Completed`
  in the epic after human validation; `Evidence / notes` states
  `Already implemented; validated by @user on DD/MM/YYYY`. No new status is
  created for this case.
- Aliases, statuses, and paths are resolved from `.project.yml`; they are not
  replaced with project-specific names.

## Matrix

| Scenario | Requirement source | Epic / feature | Repository | Issue / task | Implementation status | E2E feature / tag | E2E status | Evidence / notes |
|-----------|------------------|-----------------|-------------|---------------|----------------------|-------------------|------------|-------------------|
| ESC-1-1-1 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-1-2 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-1-3 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-1-4 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-1-5 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-2-1 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-2-2 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-2-3 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-2-4 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-3-1 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-3-2 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-3-3 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-3-4 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-4-1 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-4 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-4-2 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-4 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-4-3 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-4 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-4-4 | audit-input-processor-2026-09-29 | EPIC-1 / FEAT-1-4 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-5-1 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-5 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-5-2 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-5 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-5-3 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-5 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-5-4 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-5 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-5-5 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-5 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-5-6 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-5 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-6-1 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-6 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-6-2 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-6 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-6-3 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-6 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-1-6-4 | audit-input-processor-2026-09-29 (Addendum) | EPIC-1 / FEAT-1-6 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-2-1-1 | audit-web-crawler-2026-09-29 | EPIC-2 / FEAT-2-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-2-1-2 | audit-web-crawler-2026-09-29 | EPIC-2 / FEAT-2-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-2-1-3 | audit-web-crawler-2026-09-29 | EPIC-2 / FEAT-2-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-2-1-4 | audit-web-crawler-2026-09-29 | EPIC-2 / FEAT-2-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-2-2-1 | audit-web-crawler-2026-09-29 | EPIC-2 / FEAT-2-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-2-2-2 | audit-web-crawler-2026-09-29 | EPIC-2 / FEAT-2-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-2-2-3 | audit-web-crawler-2026-09-29 | EPIC-2 / FEAT-2-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-2-2-4 | audit-web-crawler-2026-09-29 | EPIC-2 / FEAT-2-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-1-1 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-1-2 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-1-3 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-2-1 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-2-2 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-2-3 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-2-4 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-3-1 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-3-2 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-3-3 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-3-4 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-3-3-5 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026; open question on overwrite behavior recorded in EPIC-3 comments |
| ESC-3-3-6 | audit-filesystem-mcp-2026-09-29 | EPIC-3 / FEAT-3-3 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-4-1-1 | audit-scripts-2026-09-29 | EPIC-4 / FEAT-4-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-4-1-2 | audit-scripts-2026-09-29 | EPIC-4 / FEAT-4-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-4-1-3 | audit-scripts-2026-09-29 | EPIC-4 / FEAT-4-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-4-1-4 | audit-scripts-2026-09-29 | EPIC-4 / FEAT-4-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-4-2-1 | audit-scripts-2026-09-29 | EPIC-4 / FEAT-4-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-4-2-2 | audit-scripts-2026-09-29 | EPIC-4 / FEAT-4-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-4-2-3 | audit-scripts-2026-09-29 | EPIC-4 / FEAT-4-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-4-2-4 | audit-scripts-2026-09-29 | EPIC-4 / FEAT-4-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-5-1-1 | audit-gherkin-multiple-v5-2026-09-29 | EPIC-5 / FEAT-5-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-5-1-2 | audit-gherkin-multiple-v5-2026-09-29 | EPIC-5 / FEAT-5-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-5-1-3 | audit-gherkin-multiple-v5-2026-09-29 | EPIC-5 / FEAT-5-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-5-1-4 | audit-gherkin-multiple-v5-2026-09-29 | EPIC-5 / FEAT-5-1 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-5-2-1 | audit-gherkin-multiple-v5-2026-09-29 | EPIC-5 / FEAT-5-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-5-2-2 | audit-gherkin-multiple-v5-2026-09-29 | EPIC-5 / FEAT-5-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-5-2-3 | audit-gherkin-multiple-v5-2026-09-29 | EPIC-5 / FEAT-5-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-5-2-4 | audit-gherkin-multiple-v5-2026-09-29 | EPIC-5 / FEAT-5-2 | spec2test | — | No issue | — | Not applicable | Already implemented; validated by @bperez on 29/09/2026 |
| ESC-6-1-1 | audit-github-agents-2026-09-29 | EPIC-6 / FEAT-6-1 | spec2test | — | No issue | — | Not applicable | Documented agent behavior; reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests |
| ESC-6-1-2 | audit-github-agents-2026-09-29 | EPIC-6 / FEAT-6-1 | spec2test | — | No issue | — | Not applicable | Documented agent behavior; reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests |
| ESC-6-1-3 | audit-github-agents-2026-09-29 | EPIC-6 / FEAT-6-1 | spec2test | — | No issue | — | Not applicable | Documented agent behavior; reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests |
| ESC-6-1-4 | audit-github-agents-2026-09-29 | EPIC-6 / FEAT-6-1 | spec2test | — | No issue | — | Not applicable | Documented agent behavior; reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests |
| ESC-6-2-1 | audit-github-agents-2026-09-29 | EPIC-6 / FEAT-6-2 | spec2test | — | No issue | — | Not applicable | Documented agent behavior; reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests |
| ESC-6-2-2 | audit-github-agents-2026-09-29 | EPIC-6 / FEAT-6-2 | spec2test | — | No issue | — | Not applicable | Documented agent behavior; reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests |
| ESC-6-2-3 | audit-github-agents-2026-09-29 | EPIC-6 / FEAT-6-2 | spec2test | — | No issue | — | Not applicable | Documented agent behavior; reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests |
| ESC-6-2-4 | audit-github-agents-2026-09-29 | EPIC-6 / FEAT-6-2 | spec2test | — | No issue | — | Not applicable | Documented agent behavior; reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests |

## Maintenance

Update this table when an issue status changes, an E2E test is created or removed,
or the relationship between a scenario, source, and task changes. The functional
decision history remains in the epic, and a test result does not by itself change
implementation status.

The matrix is maintained manually unless a configured tool states otherwise.
Before closing an implementation task, update the affected row and preserve the
evidence. `scripts/idx.py` generates the identifier index but does not invent or
complete traceability relationships.

## Contract Validation

- Each documented scenario must have a row, even if it has no issue or E2E test.
- Each repository alias and issue reference must be resolvable according to
  `.project.yml`.
- Implementation and E2E statuses must not be mixed.
- The matrix is retained in the target project when the requirements module is
  enabled.
