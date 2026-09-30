---
name: analyze-impact
description: Evaluates the impact of implementing a feature on existing code, classifies changes as New, Modify, or Reuse, assesses migration, breaking-change, cascade, and external-integration risks, and produces an impact matrix. Use when a feature must be assessed against existing code before its technical breakdown.
---

# Analyze Impact

Answers: *"What impact would implementing this feature have on existing
code?"*

## Inputs

- The feature to implement (configured feature pattern, default `FEAT-N-M`).
- The domain audit from `audit-domain`
  (`<paths.tasks>/<integrations.codebase_memory.evidence_path>/audit-<domain>-<YYYY-MM-DD>.md`).

## Workflow

1. **Compare** the feature scenarios with the audit. Before classifying an
   artifact as New, check audit coverage, freshness, and limitations. With
   partial CBM coverage or a local fallback, use `To confirm`; an empty search
   is never proof of absence.
2. **Classify** each change: New (does not exist), Modify (exists, needs
   changes), Reuse (exists, usable as-is).
3. **Assess risks** per change:
   - Data or schema migration (high impact).
   - Breaking change in a published interface.
   - Cascade effect on other domains.
   - Changes in external systems or integrations (identity providers,
     third-party services) that need coordination.
4. **Validate when uncertain:** delegate the question to the
   `specialist_agent` of the alias whose `responsibility` and `stack` match
   the affected area. When the alias has no specialist, perform a local
   read-only inspection and record it as a limitation.
5. **Produce** the impact matrix.

## Output

This skill owns the impact section of the analysis document
`<paths.tasks>/<feat-id>/analysis-<feat-id>.md`, written in
`project.language`:

- When the file does not exist, create it (and its `<feat-id>` directory) with
  the document title of `analyze-requirement` and this section only;
  `analyze-requirement` completes the rest.
- When the file exists, add this section if it is missing or update it in
  place; do not modify the sections owned by `analyze-requirement`.

```markdown
## Impact analysis: <feat-id>

### Necessary changes
| Alias | Area | Artifact | Type | Risk | Detail |
|-------|------|----------|------|------|--------|
| <alias> | Model | Invoice | New | Low | Simple migration |
| <alias> | Service | OrderService | Modify | Medium | New total calculation |
| <alias> | Screen | OrderDetail | Modify | Medium | Show invoice link |

### Identified risks
- Data migration: new invoice entity referenced from orders.

### Ordering dependencies
1. Providers of a new contract before its consumers.
2. Cross-alias integrations documented as real dependencies.
3. Tests after each relevant change, using the repository's commands.
```

## Checklist

- [ ] Every change classified as New, Modify, or Reuse.
- [ ] Audit coverage, freshness, and limitations reviewed.
- [ ] Migration, breaking-change, cascade, and external risks assessed.
- [ ] Uncertain points delegated or recorded as limitations.
- [ ] Ordering dependencies documented.
- [ ] The impact section is saved in
      `<paths.tasks>/<feat-id>/analysis-<feat-id>.md`.
