---
name: gherkin-multiple-v5
description: analyze gherkin specifications and compute maintainability reports with a feature maintainability index per feature, suite totals, repeated steps, excel export, mandatory json state output, incremental consolidation across upload batches using a json state file, zip-as-single-feature aggregation, and feature-level background and scenario-outline diagnostics. use when chatgpt needs to assess one or more .feature files, compare features, generate totals, keep accumulating results across turns, replace a previously analyzed feature, explain formulas, export a consolidated xlsx workbook, ask for the excel output filename before any analysis or export when it is not provided, detect repeated setup that should move to background, detect repeated scenarios that should become scenario outlines, or treat each uploaded zip as one logical feature.
---

Analyze one or more `.feature`, `.md`, or `.txt` files and produce maintainability outputs for the current scope or for an accumulated suite persisted in JSON state.

## Workflow

1. Determine whether the user has already provided an Excel workbook filename for the current analysis/export request.
   - A filename is considered provided only when the user explicitly names the desired `.xlsx` output in the current request or in the immediately preceding answer to the filename question.
   - Do not infer a filename from project names, feature names, zip names, or prior default output paths.
2. If no Excel workbook filename has been provided, stop before inspecting inputs, running scripts, computing metrics, or exporting files, and ask exactly this one question: `What would you like to call the Excel workbook?`
   - Do not continue the analysis in the same turn after asking this question.
   - Resume only after the user answers with the workbook name or explicitly says to use the default.
3. Use the user's answer as the Excel filename, sanitized for filesystem safety.
   - Append `.xlsx` if the user did not include the extension.
   - Save it under `/mnt/data/`.
   - If the user says to use the default name, use `/mnt/data/gherkin-maintainability-report.xlsx`.
   - Do not ask for the JSON state filename unless the user explicitly wants to rename it.
4. Accept one or more Gherkin files.
5. If the user provides one or more `.zip` files and asks to treat each zip as a single feature, aggregate every supported file inside each zip into one logical feature keyed by the zip filename.
6. When aggregating a zip into one logical feature, count all internal `Background`, `Scenario`, and `Scenario Outline` step bodies together as belonging to that one feature, and use the zip stem as the feature identity for replacement and reporting unless the user explicitly asks for a different label.
7. If the user is working in batches because of upload limits, also accept a prior JSON state file.
8. Run `scripts/analyze_gherkin.py` and ALWAYS pass both:
   - `--excel-output <chosen-xlsx-output-path>`
   - `--state-out /mnt/data/gherkin-state.json`
9. If the user supplied a previous JSON state file, also pass `--state-in <state-file>`.
10. Return markdown in the chat when useful or requested.
11. ALWAYS return downloadable links to both artifacts at the end of the run:
   - the Excel workbook
   - the JSON state file

## Output contract

The skill must always finish with both artifact files, even when the user only asked for metrics, a summary, or the Excel workbook.

Mandatory deliverables for every run:

- updated JSON state file
- consolidated Excel workbook

Optional deliverable:

- markdown summary in chat

Interpret the JSON file as both:

- the persistence layer for later incremental batches
- a required deliverable for the current run

## Incremental batch mode

Use incremental mode whenever the user cannot upload the whole suite at once.

Rules:

- Treat the JSON state file as the source of truth for the accumulated suite.
- Add new features from the current batch into the accumulated state.
- If a feature already exists in the state, replace the older version with the new one.
- Recompute `Totals` and `Repeated Steps` from the full accumulated suite, not only from the latest batch.
- Persist enough per-feature detail in the JSON state to recalculate suite metrics exactly.
- Use the normalized feature title as the primary replacement key. If the feature has no title, fall back to the source filename.
- Even for a single non-incremental batch, still create and return the JSON state file for reuse in later batches.

## Feature metrics

Per feature, compute exactly these normalized metrics:

- Parameterization of Steps (SPC)
- Scenario Outline for Data-Driven Rules (OAR)
- Background Design Index (BDI)
- Average Scenario Length (ASL)

Then compute:

`FMI = (SPC_s + OAR_s + BDI_s + ASL_s) / 4`

`Background Design Index (BDI)` is the single Background metric. It replaces the previous split between Background overuse and repeated setup debt.

BDI combines two Background failure modes:

- Background overuse: existing Background sections are too long or contain heavy setup verbs.
- Background debt: scenarios repeat the same initial setup blocks that should likely move to Background.

For each feature table, append a final column named `Raw Data`.

- In the `Parameterization of Steps (SPC)` row, list the step families considered candidate reusable families.
- In the `Scenario Outline for Data-Driven Rules (OAR)` row, list the duplicated scenarios that are not modeled as `Scenario Outline`.
- In the `Background Design Index (BDI)` row, list repeated initial blocks and candidate Background lines.

See `references/scoring-model.md` for the scoring formulas.

## Suite metrics and totals sheet

In `Totals`, show a final suite table with these rows:

- Parameterization of Steps (SPC)
- Scenario Outline for Data-Driven Rules (OAR)
- Background Design Index (BDI)
- Average Scenario Length (ASL)
- Structural Suite Index (SSI)

For suite rows:

- SPC, OAR, BDI, and ASL must report the average normalized feature score for that metric.
- For BDI, also report raw suite background diagnostic totals in the calculated-data cell.
- Compute `SSI = sum(feature FMI values) / total features`.

Treat `SSI` as the final suite-level metric. Do not compute or display `SMI`.

State compatibility note:

- This revision removes step-level signals and the suite step reuse metric, fuses Background overuse and Background debt into one Background Design Index, clarifies fixed vs dynamic table columns, and applies LKS Next Excel styling without frozen panes. JSON state files produced by earlier revisions should not be reused with this version.

## Table columns and fixed content

Use clear English column labels in the feature and totals tables. Most explanatory columns are fixed by metric; only calculated values and evidence change per analyzed feature.

Feature table columns:

| Column | Type | Rule |
|---|---|---|
| `Metric / Concept` | fixed | One row for each feature metric plus the final `Feature Maintainability Index (FMI)`. |
| `Scope (step, scenario, feature, suite)` | fixed | The conceptual scope of the metric: `step`, `scenario`, `feature`, or `suite`. |
| `What it measures for maintainability` | fixed | Stable explanation of the maintainability concern measured by the metric. |
| `How to measure it` | fixed | Stable measurement method for the metric. |
| `Practical formula / rule` | fixed | Stable formula, target, threshold, or scoring rule. |
| `Calculated Data` | dynamic | Feature-specific calculation trace with actual counts and intermediate values. |
| `Raw value` | dynamic | Raw metric value before normalization, or a compact raw diagnostic for composite metrics. |
| `Normalized score (0-100)` | dynamic | Final normalized score for the metric. |
| `Example / interpretation` | fixed | Stable interpretation guide that explains what high or low values mean. |
| `Raw Data` | dynamic | Feature-specific evidence such as candidate step families, duplicated scenario families, or repeated setup blocks. |

Typical feature worksheet layout:

| Area | Rows / position | Content | Notes |
|---|---|---|---|
| Title | Row 1 | `Gherkin Maintainability Report` | Styled with LKS Navy text. |
| Feature summary | Rows 3-11 | Feature name, source file, scenario count, scenario outline count, Background sections, Background steps, average Background steps, total steps, unique normalized steps. | Summary values are dynamic per feature. |
| Metrics table header | After one blank row below the summary | The 10 feature metric columns listed above. | Header uses LKS Navy fill and white text. |
| Metric rows | One row each for `SPC`, `OAR`, `BDI`, `ASL`, and final `FMI`. | Fixed explanatory columns plus dynamic calculated data, raw value, normalized score, and raw evidence. | `FMI` is highlighted with LKS Cyan. |
| Summary scores | Below the metrics table after one blank row | `Step Quality`, `Scenario Design`, `Background Design`, `Feature Maintainability Index`, `Weighted Total Before Caps`, and final `Feature Maintainability Index`. | Used as a compact score recap. |

A typical feature sheet therefore has five metric rows:

| Metric / Concept | Scope | Dynamic columns populated per feature |
|---|---|---|
| `Parameterization of Steps (SPC)` | `step` | candidate reusable families, parameterized families, raw SPC, normalized SPC_s, candidate step-family evidence. |
| `Scenario Outline for Data-Driven Rules (OAR)` | `scenario` | duplicated scenario families, duplicated families modeled as outlines, raw OAR, normalized OAR_s, duplicated non-outline scenario evidence. |
| `Background Design Index (BDI)` | `feature` | Background overuse indicators, repeated setup debt, raw Background debt, normalized BDI_s, repeated initial-block evidence. |
| `Average Scenario Length (ASL)` | `feature` | scenario lengths, total scenario steps, scenario count, raw ASL, normalized ASL_s. |
| `Feature Maintainability Index (FMI)` | `feature` | SPC_s, OAR_s, BDI_s, ASL_s, raw average, guardrails, final FMI. |

Totals table columns use the same English labels, except totals do not include `Raw value` or `Raw Data` as separate columns when the raw suite diagnostics already appear in `Calculated Data`.

Fixed feature-row content:

| Metric / Concept | Scope (step, scenario, feature, suite) | What it measures for maintainability | How to measure it | Practical formula / rule | Example / interpretation |
|---|---|---|---|---|---|
| `Parameterization of Steps (SPC)` | `step` | Checks whether repeated step families with data variations are properly parameterized. | Normalize step text, group equivalent step families, and count how many candidate reusable families are already parameterized. | `SPC = parameterized reusable families / candidate reusable families`; target `>= 0.80`; `SPC_s = min(100, 100 * SPC / 0.80)`. | `100` means candidate step families are sufficiently parameterized; low values indicate duplicated steps with embedded literals. |
| `Scenario Outline for Data-Driven Rules (OAR)` | `scenario` | Checks whether repeated scenarios that only differ by data are modeled as `Scenario Outline` with `Examples`. | Group scenarios by normalized step sequence and verify which duplicated scenario families are represented by `Scenario Outline`. | `OAR = duplicated families modeled as Scenario Outline / total duplicated families`; target `>= 0.80`; `OAR_s = min(100, 100 * OAR / 0.80)`. | `100` means data-driven duplication is well consolidated; low values point to copied scenarios that should probably become `Scenario Outline`. |
| `Background Design Index (BDI)` | `feature` | Evaluates Background design: it penalizes Background sections that are too long or heavy and repeated setup that should likely be extracted. | Compute a Background overuse score and a repeated setup debt score; use the worse signal as the final score. | `BDI_s = min(overuse_score, debt_score)`. `overuse_score = 0` if Background is overused, otherwise `100`. `debt_score = max(0, 100 * (1 - background_debt_raw / 6.0))`. | `100` means balanced Background usage and little setup debt; low values indicate heavy Background sections or repeated setup still embedded in scenarios. |
| `Average Scenario Length (ASL)` | `feature` | Measures average scenario length as a proxy for cognitive load, readability, and maintainability. | Count executable steps in each `Scenario` and `Scenario Outline`, excluding `Background`, and average them across scenarios. | `ASL = total scenario steps / total scenarios`; score is `100` when `ASL <= 5` and decays linearly to `0` when `ASL >= 7`. | Scenarios with 3 to 5 steps are usually easy to maintain; above 7 steps, consider splitting or simplifying them. |
| `Feature Maintainability Index (FMI)` | `feature` | Final structural maintainability index for the feature. | Average `SPC_s`, `OAR_s`, `BDI_s`, and `ASL_s`, then apply guardrails when applicable. | `FMI = (SPC_s + OAR_s + BDI_s + ASL_s) / 4`. | `100` means the feature is structurally maintainable; low values point to debt across steps, scenarios, Background design, or scenario length. |

Excel styling:

- Use the LKS Next working palette from `lks-next-palette`: navy `#003B5C`, cyan `#00A3E0`, charcoal `#2E3135`, light gray `#F3F5F7`, mid gray `#B7C1CA`, and white `#FFFFFF`.
- Use navy fills with white text for table headers.
- Use cyan for the final KPI/index rows such as `FMI` and `SSI`.
- Use light gray and mid gray for secondary structure, borders, and readability.
- Do not freeze or immobilize rows or columns in any generated worksheet.

Highlight this totals row with a distinct LKS accent color:

- `Structural Suite Index (SSI)`

## Repeated steps sheet

After `Totals`, create a sheet named `Repeated Steps` with columns:

- `feature`
- `scenario`
- `step`
- `used in`
- `amount`

Include only non-unique steps detected across the analyzed scope.

## Commands

Single batch, always returning Excel and JSON:

```bash
python scripts/analyze_gherkin.py batch/*.feature --format markdown --state-out /mnt/data/gherkin-state.json --excel-output /mnt/data/gherkin-maintainability-report.xlsx
```

First incremental batch:

```bash
python scripts/analyze_gherkin.py batch1/*.feature --format markdown --state-out /mnt/data/gherkin-state.json --excel-output /mnt/data/gherkin-maintainability-report.xlsx
```

Later incremental batch that replaces repeated features and keeps totals consolidated:

```bash
python scripts/analyze_gherkin.py batch2/*.feature --format markdown --state-in /mnt/data/gherkin-state.json --state-out /mnt/data/gherkin-state.json --excel-output /mnt/data/gherkin-maintainability-report.xlsx
```

Final consolidation from state only:

```bash
python scripts/analyze_gherkin.py --format markdown --state-in /mnt/data/gherkin-state.json --state-out /mnt/data/gherkin-state.json --excel-output /mnt/data/gherkin-maintainability-report.xlsx
```
