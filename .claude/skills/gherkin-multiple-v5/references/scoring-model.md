# scoring model

## feature maintainability

Per feature compute these normalized metrics:

- `SPC_s = min(100, 100 * SPC / 0.80)`
- `OAR_s = min(100, 100 * OAR / 0.80)`
- `BDI_s`, the Background Design Index score described below
- `ASL_s = 100` if `ASL <= 5`, linear decay to `0` at `ASL = 7`

Then compute:

`FMI = (SPC_s + OAR_s + BDI_s + ASL_s) / 4`

## background design index

`Background Design Index (BDI)` is the single Background metric. It combines Background overuse and repeated setup debt.

### background overuse component

- If no `Background` exists, `background_overuse_score = 100` because there is no existing Background to overuse.
- Otherwise compute `avg_background_steps = total Background steps / number of Background sections`.
- Set `background_overused = true` when `avg_background_steps > 4` or a heavy Background hint exists.
- Heavy Background hints include setup verbs such as create, insert, seed, load, import, call, post, put, delete, upload, and generate.
- `background_overuse_score = 0` when `background_overused = true`, otherwise `100`.

### repeated setup debt component

Detect candidate Background steps by reviewing scenario bodies inside a feature and finding shared initial blocks.

Recommended implementation:

- Group scenarios by their first step, then recurse step-by-step while the grouped scenarios still share the same next literal step text.
- Every shared literal step inside a shared prefix counts as a background-candidate occurrence.
- `background_candidate_distinct_lines` = number of distinct literal steps that were part of at least one shared initial block.
- `background_candidate_occurrences` = sum of all shared-prefix step occurrences across those blocks.
- `total_scenario_steps` = total step lines from scenario bodies in the feature, excluding `Background` steps.
- `MBO = background_candidate_occurrences / total_scenario_steps`
- `background_debt_raw = background_candidate_distinct_lines * MBO`
- `background_debt_score = max(0, 100 * (1 - background_debt_raw / 6.0))`

### final BDI score

Use the worse of the two Background signals:

`BDI_s = min(background_overuse_score, background_debt_score)`

Interpretation:

- low `BDI_s` means the feature either overuses Background or repeats setup that should likely move to Background
- high `BDI_s` means Background usage is balanced and repeated setup debt is low

## scenario outline for data-driven rules

- Build duplicated families by normalized step sequence.
- `OAR = duplicated scenario families modeled as outlines / all duplicated scenario families`.
- If there are no duplicated scenario families, `OAR = 1.0`.
- `OAR_s = min(100, 100 * OAR / 0.80)`.

## suite totals

For the totals table:

- `SPC_suite = sum(feature SPC_s) / total features`
- `OAR_suite = sum(feature OAR_s) / total features`
- `BDI_suite = sum(feature BDI_s) / total features`
- `ASL_suite = sum(feature ASL_s) / total features`

Also report raw suite diagnostics for the Background metric:

- `suite_background_candidate_distinct_lines` = sum(feature background_candidate_distinct_lines)
- `suite_background_candidate_occurrences` = sum(feature background_candidate_occurrences)
- `suite_total_scenario_steps` = sum(feature total_scenario_steps)
- `suite_background_debt_raw = suite_background_candidate_distinct_lines * (suite_background_candidate_occurrences / suite_total_scenario_steps)` when `suite_total_scenario_steps > 0`, else `0`

Indexes:

- `SSI = sum(feature FMI values) / total features`

Report `SSI` as the final suite-level metric. Do not compute or display `SMI`.

## incremental state model

Incremental mode changes persistence only, not the formulas.

Store enough per-feature detail in the JSON state to recompute the suite exactly after each batch, including at least:

- feature identity used for replacement
- feature report payload
- normalized step set used for step comparison
- step occurrences
- per-feature normalized scores
- background counts and average Background step counts
- background-candidate counters and blocks
- final FMI

When a repeated feature arrives in a later batch, replace the old stored feature and recalculate suite totals from the full updated state.

## output table clarity

Feature tables use English labels and separate fixed explanatory content from dynamic results:

- Fixed by metric: `Metric / Concept`, `Scope (step, scenario, feature, suite)`, `What it measures for maintainability`, `How to measure it`, `Practical formula / rule`, and `Example / interpretation`.
- Dynamic by feature: `Calculated Data`, `Raw value`, `Normalized score (0-100)`, and `Raw Data`.

Excel output must use the LKS Next working palette: navy `#003B5C` for table headers with white text, cyan `#00A3E0` for final index rows, charcoal `#2E3135` for body text, light gray `#F3F5F7` for secondary structure, and mid gray `#B7C1CA` for borders. Do not freeze panes in any worksheet.
