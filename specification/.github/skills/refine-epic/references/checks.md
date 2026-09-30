# Epic Review Checks

Checks used by `refine-epic` Mode 2 and Mode 3. Severity: Error blocks
acceptance, Warning should be fixed, Info is advisory. Section names refer to
the roles defined in the configured epic template.

## A. Section completeness

| Check | Severity |
|-------|----------|
| Feature listed in the feature index but missing from the body (or vice versa) | Error |
| Empty overview | Error |
| Feature without description | Error |
| Scenarios table without rows | Error |
| Empty acceptance criteria | Warning |
| Empty technical notes or testing notes | Warning |
| Empty Tasks table while the feature is in a development or later state | Warning |
| Empty Tasks table in a new epic | Info |
| Empty comments table | Info |
| Missing change history section | Warning |

## B. IDs

Report only; never renumber without explicit confirmation.

| Check | Severity |
|-------|----------|
| Duplicate epic, feature, or scenario ID | Error |
| ID that does not match the configured pattern | Error |
| Epic number in the title differs from the file name | Error |
| Gap in feature or scenario numbering | Info (report only) |
| Feature without scenarios | Warning |
| File name that does not follow `identifiers.epic.file_pattern` | Info (never rename existing files) |

## C. Format

| Check | Severity |
|-------|----------|
| Table missing a template column (scenarios, tasks, E2E when enabled) | Error |
| State value not literally present in `specification.states`, `task_states`, or `verification_states` (including emoji or different spelling) | Error |
| Priority not present in `specification.priorities` | Error |
| Scenario or acceptance criterion not following `specification.acceptance_criteria_format` | Warning |
| Heading that differs from the template for `project.language` | Warning |
| Outdated feature index or progress summary | Warning |

## D. E2E section

| Condition | Expected |
|-----------|----------|
| `modules.e2e` and `features.e2e.enabled` both `true` | Each feature has the E2E section with the six template columns: Scenario ID, E2E Feature, E2E Scenario, Automation, Last result, Evidence. Missing section or columns: Warning |
| Either flag `false` | E2E section and the E2E counts of the progress summary absent. Presence: Warning (propose removal) |

## E. Content and evidence

| Check | Severity |
|-------|----------|
| Dependency on a non-existent epic | Error |
| Feature or epic in the completed state while a child is not completed | Error |
| Completed state without recorded human validation when `workflow.human_validation_required_for_completion` is `true` | Error |
| Completed state justified only by closed issues | Error |
| Source that does not follow a type of the source table (document, code, test, contract, data, history) or lacks a verifiable link | Warning |
| Several sources in one cell not separated by `;` | Info |
| Completed state justified only by sources (code, test, contract, data, history) | Error |
| Audit contradiction affecting a scenario not copied to its comments as an open question | Warning |
| Confidence column added to an epic table | Warning |
| Scenario discovered in code whose matrix row lacks the audit ID as requirement source | Warning |
| Term not in the glossary | Info |

Implementation state, E2E automation state, and test results are recorded
separately. A located `.feature` file is not proof of automation.

## Progress summary

Recompute from the actual scenario states:

- One count per value of `specification.states`, in configured order, written
  literally (no emoji).
- A per-feature table with a Total column plus one column per configured state.
- Only when E2E is enabled: per-feature E2E coverage (scenarios with an E2E
  match, automated, without E2E), counted from the E2E section.

## Chat report format

```markdown
## Review of <epic ID>: <title>

### Errors (N)
1. <ID>: <finding>

### Warnings (N)
1. <ID>: <finding>

### Info (N)
1. <finding>

### Summary
- Errors: N | Warnings: N | Info: N
- Features: N total, N with gaps
- Scenarios: N total, N not following the acceptance criteria format
```

Emoji may be used in this chat report; never write them into the epic.
