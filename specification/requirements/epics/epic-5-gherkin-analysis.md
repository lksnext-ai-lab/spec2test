# EPIC-5: Gherkin Suite Maintainability Analysis

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Low

## Overview

Computes maintainability metrics for one or more Gherkin features — per-feature
scores (SPC, OAR, BDI, ASL, combined into FMI) and a suite-level Structural
Suite Index (SSI) — exports a consolidated Excel workbook, and persists a JSON
state file so results can be accumulated incrementally across upload batches
that would otherwise exceed a single request. Implemented as a Claude Code
skill (`SKILL.md` plus `analyze_gherkin.py`), not an MCP server.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-gherkin-multiple-v5-2026-09-29`; it is not new work. No
automated tests exist for this module within the analyzed scope, and its
metric-scoring internals were confirmed through their function outline and
`SKILL.md`'s formula descriptions rather than a full line-by-line read; this
limitation is recorded in the domain model's gaps section.

## Feature Index

- [FEAT-5-1: Compute Gherkin feature and suite maintainability metrics](#feat-5-1-compute-gherkin-feature-and-suite-maintainability-metrics)
- [FEAT-5-2: Consolidate results incrementally across upload batches](#feat-5-2-consolidate-results-incrementally-across-upload-batches)

## Dependencies

None known.

## References

- Code: spec2test: [.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py)
- Document: spec2test: [.claude/skills/gherkin-multiple-v5/SKILL.md](../../../.claude/skills/gherkin-multiple-v5/SKILL.md)
- Audit: [audit-gherkin-multiple-v5-2026-09-29](../../tasks/audits/audit-gherkin-multiple-v5-2026-09-29.md)
- Domain model: [domain-model.md](../domain-model.md)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result.

---

## FEAT-5-1: Compute Gherkin feature and suite maintainability metrics

**Source:** spec2test: [SKILL.md "Feature metrics" and "Suite metrics and totals sheet"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L288-L682](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py)

**Priority:** Low

**Status:** Completed

**Owner:** @bperez

**Description:** Parses one or more Gherkin inputs (files, directories, raw text, or a zip treated as one aggregated feature) and computes each feature's SPC, OAR, BDI, and ASL scores combined into an FMI, then combines every feature into a suite-level SSI, exporting a consolidated Excel workbook with one sheet per feature plus Totals and Repeated Steps.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-5-1-1 | Compute the four per-feature metrics and the combined FMI | Each analyzed feature gets SPC, OAR, BDI, and ASL scores, averaged into `FMI` | Completed | spec2test: [SKILL.md "Feature metrics"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L288-L572](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) summarize_feature/build_feature_report |
| ESC-5-1-2 | Compute the suite-level Structural Suite Index | The accumulated suite gets an `SSI`, the average of every feature's `FMI` | Completed | spec2test: [SKILL.md "Suite metrics and totals sheet"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L621-L682](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) build_suite_report |
| ESC-5-1-3 | Export a consolidated Excel workbook | The workbook has one sheet per feature plus Totals and Repeated Steps sheets | Completed | spec2test: [SKILL.md "Output contract"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L1006-L1016](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) export_xlsx |
| ESC-5-1-4 | A zip file is treated as one aggregated logical feature | Every supported file inside an uploaded zip is aggregated into a single feature keyed by the zip's filename | Completed | spec2test: [SKILL.md workflow steps 5-6](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L989-L1003](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) load_zip_as_single_feature |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a Gherkin feature, when it is analyzed, then it gets SPC, OAR, BDI, ASL, and a combined FMI.
- [x] Given an accumulated set of analyzed features, when the suite report is built, then it includes an SSI averaged from every feature's FMI.
- [x] Given the analysis completes, when an Excel output path is provided, then a workbook with one sheet per feature plus Totals and Repeated Steps is written.
- [x] Given a `.zip` file is uploaded, when it is analyzed, then all of its supported files are aggregated into one feature keyed by the zip's name.

### Technical Notes

No automated tests exist for this feature within the analyzed scope; the metric-scoring internals were confirmed through their function outline and `SKILL.md`'s formulas rather than a full line-by-line read (see `audit-gherkin-multiple-v5-2026-09-29` Q1 and Technical Evidence).

### Testing Notes

Not available: no test files were found for this module (`audit-gherkin-multiple-v5-2026-09-29` Q1).

## FEAT-5-2: Consolidate results incrementally across upload batches

**Source:** spec2test: [SKILL.md "Incremental batch mode"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L1040-L1159](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py)

**Priority:** Low

**Status:** Completed

**Owner:** @bperez

**Description:** Persists analyzed features in a JSON state file so a suite that cannot be uploaded all at once can be analyzed in batches, replacing a feature already present in the state by its normalized title rather than duplicating it, and rejecting a state file from an incompatible schema version.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-5-2-1 | A feature already in the state is replaced, not duplicated | Re-analyzing a feature whose normalized title (or source filename) already exists in the state replaces the older entry | Completed | spec2test: [SKILL.md "Incremental batch mode"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L1078-L1159](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) main |
| ESC-5-2-2 | Suite totals are recomputed from the full accumulated state | Totals and Repeated Steps are recalculated from every feature in the state, not only the latest batch | Completed | spec2test: [analyze_gherkin.py#L1078-L1159](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) main |
| ESC-5-2-3 | An incompatible state file version is rejected | A JSON state file whose `version` does not match the script's expected version is rejected instead of being silently reinterpreted | Completed | spec2test: [analyze_gherkin.py#L1040-L1054](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) load_state |
| ESC-5-2-4 | A JSON state file is always produced, even for a single batch | Every run writes an updated JSON state file, so it can be reused for a later batch even when the current run is not incremental | Completed | spec2test: [SKILL.md "Incremental batch mode"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L1057-L1060](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) save_state |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a feature already present in the state (by normalized title or filename), when it is re-analyzed, then it replaces the older entry rather than duplicating it.
- [x] Given an accumulated state with multiple batches, when totals are computed, then they reflect every feature in the state, not only the latest batch.
- [x] Given a state file with an unsupported version, when it is loaded, then it is rejected with an explanatory error.
- [x] Given `--state-out` is provided, when the run completes, then the updated JSON state file is written regardless of batch mode.

### Technical Notes

No automated tests exist for this feature within the analyzed scope.

### Testing Notes

Not available: no test files were found for this module (`audit-gherkin-multiple-v5-2026-09-29` Q1).

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-5-1 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-5-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| **Total** | **8** | 0 | 0 | 0 | 0 | 0 | **8** | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `gherkin-multiple-v5` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |
