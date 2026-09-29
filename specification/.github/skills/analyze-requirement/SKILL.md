---
name: analyze-requirement
description: Converts a feature into dependency-ordered technical tasks grouped by configured repository alias and completes the analysis at <paths.tasks>/<feat-id>/analysis-<feat-id>.md for review and later planning. Use when an audited and impact-assessed feature needs a technical task breakdown.
---

# Analyze Requirement

Produces the technical breakdown of one feature from the domain audit and the
impact analysis.

## Inputs

- The feature and its scenarios (epic under `paths.epics`).
- The domain audit:
  `<paths.tasks>/<integrations.codebase_memory.evidence_path>/audit-<domain>-<YYYY-MM-DD>.md`
  (use the most recent date for the domain).
- The impact analysis from `analyze-impact`: its section of
  `<paths.tasks>/<feat-id>/analysis-<feat-id>.md`.

If the audit or impact analysis is missing, run `audit-domain` and
`analyze-impact` first.

## Workflow

1. Read the feature, the audit, the impact analysis, and `repositories[]` in
   `.project.yml`.
2. Group each detected change under the enabled alias whose `responsibility`
   and `stack` match. Change types (model, schema, service, endpoint, screen,
   component, integration, test) describe work, not mandatory repository roles.
3. Add testing tasks per changed module using the repository's test tooling.
4. Order by real dependencies from the impact analysis. Do not impose a fixed
   layer or repository order; run independent tasks in parallel.
5. Estimate each task with a value from `github_projects.fields.Size.options`
   and `github_projects.fields.Estimate.values`.

## Output

**File:** `<paths.tasks>/<feat-id>/analysis-<feat-id>.md`, where `<feat-id>` is
the feature ID in the configured pattern (default `FEAT-N-M`). Write in
`project.language`. `analyze-impact` creates this file with its impact section;
this skill completes the remaining sections around it, keeps the impact section
unchanged (the impact reference links to it), and never creates a second
analysis file.

```markdown
# Technical analysis: <feat-id> - <title>

## Summary
<feature and scope in 1-2 paragraphs>

## Audit reference
<relative link to the audit file>

## Impact reference
<link to the impact section>

## Technical tasks

### <alias>
| # | Task | Type (New/Modify/Reuse) | Area | Size | Estimate | Scenarios |
|---|------|-------------------------|------|------|----------|-----------|
| 1 | <task> | New | <area> | <configured size> | <configured estimate> | <scenario IDs> |

### Testing
| # | Task | Alias | Scope | Size |
|---|------|-------|-------|------|

## Dependencies
<ordered list or Mermaid diagram>

## Notes for review
- <prioritization suggestions, risks>
```

Each task based on a code finding references the audit and keeps alias, path
or symbol, commit or generation, and coverage. Absences under partial coverage
are risks or pending confirmations, not facts.

## Checklist

- [ ] Every task has type, area, size, estimate, and scenario IDs.
- [ ] Every alias is enabled in `.project.yml`.
- [ ] Order respects dependencies.
- [ ] Testing tasks are included.
- [ ] The document is saved at `<paths.tasks>/<feat-id>/analysis-<feat-id>.md`.
- [ ] Technical evidence provenance is preserved.
- [ ] No issue was created; issues are created later with `create-task` after
      approval.
