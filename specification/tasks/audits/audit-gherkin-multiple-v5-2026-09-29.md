# Domain Audit: gherkin-multiple-v5 (Gherkin maintainability analysis skill)

**Date:** 2026-09-29
**Audit ID:** audit-gherkin-multiple-v5-2026-09-29

## Scope and Tools

| Alias | Modules | CBM state | Fallback | Limitations |
|---|---|---|---|---|
| spec2test | .claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py, SKILL.md | project `C-VSCode-WS-spec2Test`, generation `2026-09-29T10:49:01Z`, 1,349 nodes / 5,758 edges | none | No specialist agent is configured for this alias; local read-only inspection by `analyst-requirements`. No test files exist for this module within the analyzed scope. `SKILL.md` is used here as a Document source describing the intended workflow of a Claude Code skill, not as executable code. |

## Entry-Point Inventory

| Module | Entry point | Kind | Qualified symbol and file | Coverage |
|---|---|---|---|---|
| gherkin-multiple-v5 | `analyze_gherkin.py` (CLI) | Standalone script invoked by the Claude Code skill workflow described in `SKILL.md` | [analyze_gherkin.py#L1078-L1159](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) `...analyze_gherkin.main` | ok |

This is not exposed as an MCP tool; it is a skill for the Claude Code agent platform, distinct from the `input-processor`/`web-crawler`/`filesystem-mcp` MCP servers audited previously.

## Q1. Behaviors Pinned by Tests

Not available. No test files were found for this module within the analyzed scope.

## Q2. Exposed Capabilities

| Capability | Source (specification operation or route, link) | Handler | Confidence |
|---|---|---|---|
| Analyze one or more `.feature`/`.md`/`.txt` files, directories, raw text, or a prior JSON state, computing per-feature maintainability metrics and suite totals | `SKILL.md` workflow steps 4-9; [analyze_gherkin.py#L1078-L1159](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) main | High |
| Export a consolidated Excel workbook with one sheet per feature plus Totals and Repeated Steps sheets | `SKILL.md` "Output contract"; [analyze_gherkin.py#L1006-L1016](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) export_xlsx | High |
| Persist and reload a JSON state file to consolidate features incrementally across upload batches, replacing a feature already present by its normalized title | `SKILL.md` "Incremental batch mode"; [analyze_gherkin.py#L1040-L1075](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) load_state/save_state/main | High |
| Treat a `.zip` file as one aggregated logical feature keyed by its filename | `SKILL.md` workflow steps 5-6; [analyze_gherkin.py#L989-L1003](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) load_zip_as_single_feature | High |

## Q3. Entities, States, and Rules

| Entity or rule | Source (migration, entity, enum, constraint, link) | Values | Confidence |
|---|---|---|---|
| Feature metrics | `SKILL.md` "Feature metrics"; [analyze_gherkin.py#L288-L572](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) | SPC (Parameterization of Steps), OAR (Scenario Outline for Data-Driven Rules), BDI (Background Design Index), ASL (Average Scenario Length); `FMI = (SPC_s + OAR_s + BDI_s + ASL_s) / 4` | High |
| Suite metrics | `SKILL.md` "Suite metrics and totals sheet"; [analyze_gherkin.py#L621-L682](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) build_suite_report | `SSI = sum(feature FMI values) / total features` | High |
| JSON state schema | [analyze_gherkin.py#L21](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py), [#L1040-L1075](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) | `version` (`STATE_VERSION`), `features` (keyed by normalized feature title, falling back to source filename), `meta` (feature_count, last_run_utc, added_features, replaced_features) | High |

## Q4. Actors and Permissions

Not applicable. This is a local, unauthenticated CLI script with no runtime request or actor model.

## Q5. User Vocabulary

| Term | Where it appears (i18n key, screen, message, link) | Candidate glossary entry |
|---|---|---|
| Feature Maintainability Index (FMI) | `SKILL.md` "Feature metrics" | The average of a feature's four normalized maintainability scores (SPC, OAR, BDI, ASL) |
| Structural Suite Index (SSI) | `SKILL.md` "Suite metrics and totals sheet" | The average FMI across every feature in the accumulated suite |
| Background Design Index (BDI) | `SKILL.md` "Feature metrics" | A single Background-quality score combining overuse of a Background section and repeated setup that should likely move into one |

## Q6. Intent

| Capability | Reference (`alias#N` or commit, link) | Stated reason |
|---|---|---|
| The skill itself | Commit `45bc194` "Added Gherkin maintainability quality analysis skill" | States the purpose directly: adding a quality-analysis capability for Gherkin suites |
| Fusing Background overuse and Background debt into one BDI metric | `SKILL.md` "State compatibility note" | States that this revision removes step-level signals and the suite step-reuse metric, and that JSON state files from earlier revisions should not be reused with this version |

## Q7. Call Paths

| Entry point | Path to persistence or integrations | Tool | Confidence |
|---|---|---|---|
| `main` | `main` → `resolve_inputs` (reads files/directories/zips from disk) → `parse_gherkin`/`summarize_feature`/`build_feature_report` → merges into `features_state` → `load_state`/`save_state` (reads/writes the JSON state file) → `combine_aggregates`/`build_suite_report`/`build_duplicate_steps` → `export_xlsx` (writes the `.xlsx` workbook via `openpyxl`) | Direct source read | High |

## Contradictions

Not applicable. The CLI arguments in `main` (`--excel-output`, `--state-in`, `--state-out`) match the ones `SKILL.md` instructs the calling agent to pass; no conflicting sources were found within the analyzed scope.

## Technical Evidence

| Alias | CBM project | Commit/generation | Tool/query | Symbol or path | Coverage | Confirmation | Limitations |
|---|---|---|---|---|---|---|---|
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `get_code_snippet` (outline, two pages) | `analyze_gherkin` (57 members) | complete | snippet read | none |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | Direct file read | `analyze_gherkin.py#L1006-L1164`, `SKILL.md#L1-L120` | complete for the read ranges | local reading | The remaining ~850 lines of `analyze_gherkin.py` (metric-scoring internals) were confirmed only through their function outline and `SKILL.md`'s formula descriptions, not a full line-by-line read |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | `git log --oneline -n 20 -- .claude` | 1 commit touching `.claude` | complete for this path | local reading | No `gh` issue query performed for this alias in this pass |

## Requirement Gaps

Not applicable (code-first mode: no documented scenarios exist yet for this domain).
