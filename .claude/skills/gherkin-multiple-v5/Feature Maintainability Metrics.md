# Feature Maintainability Metrics

*This document is the reference for the four automated maintainability metrics reported throughout this replication package: how each one is defined, why its threshold was set where it was, and exactly how it is computed by `Gherkin-Multiple-v5` Claude Skill, the tool used to produce every score, Excel workbook, and JSON state file in the package. Use it to interpret any per-feature or suite-level report, or to reimplement the scoring logic independently.*

## 1. Origin and scope of the metrics

The good and bad BDD practices used in this work are inherently qualitative. To complement them with a quantitative assessment, the authors compiled — in collaboration with the QA team at LKS NEXT — a catalog of BDD good and bad practices derived from the literature (`Wynne_2017`, `Binamungu_2018`, `Binamungu_2020`, `Sears_2026`, `Oliveira_2019`) and refined against the QA team's own test suite. The full catalog is injected into the Gherkin-Generator agent as a quality baseline and includes both structural dimensions and qualitative ones, such as business-language adherence and intention-revealing naming.

From that catalog, the QA team selected the subset of dimensions they considered:

1. **critical** for maintenance cost in their test suite, and
2. **objectively measurable** from the abstract syntax tree (AST) of a feature file.

These four dimensions are operationalized as automated metrics and combined into the **Feature Maintainability Index (FMI)**. The remaining qualitative dimensions, which require human judgment, are assessed by expert reviewers during the human-in-the-loop validation stage of the pipeline — they are **not** part of the automated index described here.

Each metric produces a normalized score in `[0, 100]`. Target thresholds were set by the LKS Next QA team from their experience with the test suite, not derived theoretically. Equal weighting was used in the FMI because, in the QA team's experience, no single dimension dominates maintainability a priori.

## 2. Metrics at a glance

| ID | Scope | Raw definition | Target | Score `s ∈ [0,100]` |
|---|---|---|---|---|
| **SPC** | step | `SPC = parameterized families / candidate families` | `SPC ≥ 0.80` | `s_p = min(100, 100·SPC/0.80)` |
| **OAR** | scenario | `OAR = outline families / duplicated families` | `OAR ≥ 0.80` | `s_o = min(100, 100·OAR/0.80)` |
| **BDI** | feature | `B_o = 100` if not overused, `0` otherwise; `B_d = max(0, 100(1 − debt/6))` | `100` | `s_b = min(B_o, B_d)` |
| **ASL** | feature | `ASL = scenario steps / scenarios` | `ASL ≤ 5` | `100` if `ASL ≤ 5`; `50(7 − ASL)` if `5 < ASL < 7`; `0` otherwise |
| **FMI** | feature | — | — | `FMI = ¼(s_p + s_o + s_b + s_ℓ)`, subject to the guardrail in §8 |

All scores are computed automatically from the AST produced by parsing the `.feature` (or `.md` / `.txt`) file; nothing here is estimated or eyeballed.

## 3. Common preprocessing

Two normalization routines are applied before any metric is computed. Both are deterministic and used consistently across single-batch and incremental runs.

### 3.1 Step-text normalization

Every step's free text (the part after `Given`/`When`/`Then`/`And`/`But`/`*`) is normalized as follows, in order:

1. Any content inside double or single quotes is replaced with the token `"{string}"`.
2. Any `<placeholder>` token (Scenario Outline example-column syntax) is replaced with `{param}`.
3. Any standalone number is replaced with `{int}`.
4. Whitespace is collapsed and the result is lower-cased.

Two steps are considered members of the same **normalized family** only when they produce an identical string after this transformation. Because normalization only touches quoted literals, bare numbers, and `<placeholder>` tokens, two steps can share a normalized form **only** if they differ specifically in one of those three kinds of content (or in case/whitespace alone — see the caveat in §12).

### 3.2 Feature identity normalization

For the purpose of replacing a feature across incremental batches, a feature's title (or, if untitled, its source filename) is lower-cased and has its whitespace collapsed to a single space. A `.zip` file treated as a single logical feature uses its filename stem as this identity instead.

### 3.3 What counts as a step

Only lines beginning with `Given`, `When`, `Then`, `And`, `But`, or `*` (followed by a space) are counted as steps. `Background:` steps are tracked separately from `Scenario:`/`Scenario Outline:` steps and are **excluded** from every scenario-level count (SPC's step pool, OAR's step sequences, and ASL). Data tables attached to an ordinary step are not parsed into structured form; only `Examples:` tables under a `Scenario Outline` are captured, and they feed only the descriptive summary (row/column counts), not the four scored metrics.

---

## 4. Step Parameterization Coverage (SPC)

**Scope:** step.

**What it measures.** The degree to which repeated step families that vary only by embedded data values are expressed with placeholders rather than hard-coded literals.

**How it is computed.**

1. All steps in the feature (excluding Background) are grouped by their normalized form (§3.1) into **step families**.
2. A family is **candidate reusable** when it contains more than one distinct literal step text — i.e., the same normalized signature is reached from at least two different original wordings. This is precisely the situation where a value that varies between occurrences (a quoted string, a number, or an outline placeholder) was masked away by normalization.
3. Among candidate families, a family counts as **parameterized** when its normalized signature still contains at least one of the tokens `{string}`, `{int}`, or `{param}` — i.e., the variation between its members came from quoted data, a number, or an explicit outline placeholder, rather than from something normalization does not touch (see §12 for the one edge case where this is not the case).

**Formula.**

```
SPC   = parameterized reusable families / candidate reusable families
        (defaults to 1.0 if there are no candidate families — there is
        nothing to fix)
SPC_s = min(100, 100 · SPC / 0.80)
```

**Threshold rationale.** The QA team set `SPC ≥ 0.80` because, in their experience, steps with hard-coded values are a frequent source of unnecessary edits whenever input data changes.

**Interpretation.** `100` means candidate step families are sufficiently parameterized; low values indicate duplicated steps with embedded literals that should be consolidated.

**Evidence (`Raw Data` column).** The list of candidate reusable families, each shown as its normalized signature together with the distinct literal variants observed (e.g. `the user logs in as {string} => the user logs in as "admin" || the user logs in as "guest"`).

---

## 5. Scenario Outline Adoption Rate (OAR)

**Scope:** scenario.

**What it measures.** The extent to which scenarios that are structurally identical but differ only by data have been consolidated into `Scenario Outline` constructs with `Examples`, rather than copied verbatim as separate `Scenario` blocks.

**How it is computed.**

1. Every scenario in the feature (both `Scenario` and `Scenario Outline` entries) is grouped by its **full normalized step sequence** — the ordered tuple of each step's normalized text.
2. A group is **duplicated** when it has more than one member.
3. A duplicated group counts as **modeled as an outline** when at least one of its members is a `Scenario Outline`.
4. Separately, for the evidence column only, plain `Scenario` entries (outlines excluded) are grouped again to surface the literal duplicated copies that are **not yet** consolidated — these are the concrete candidates a reviewer would turn into a `Scenario Outline`.

**Formula.**

```
OAR   = duplicated families modeled as Scenario Outline / total duplicated families
        (defaults to 1.0 if there are no duplicated families — no
        consolidation opportunity exists)
OAR_s = min(100, 100 · OAR / 0.80)
```

**Threshold rationale.** `OAR ≥ 0.80` was set by the QA team; scenario duplication was identified as a recurring maintenance liability in their codebase, where literal copies tend to drift apart over time.

**Interpretation.** `100` means data-driven duplication is well consolidated; low values point to copied scenarios that should probably become a `Scenario Outline`.

**Evidence (`Raw Data` column).** The duplicated plain-`Scenario` families that are not modeled as an outline, listed as their scenario titles alongside the shared normalized step sequence.

---

## 6. Background Design Index (BDI)

**Scope:** feature.

**What it measures.** Two complementary anti-patterns in the use of the `Background` block, both flagged by the QA team as problematic in their test suite. BDI reports the worse of the two sub-scores, so either deficiency alone is sufficient to lower it.

### 6.1 Overuse component (`B_o`)

- If the feature has no `Background` at all, `B_o = 100` — there is nothing to overuse.
- Otherwise, `avg_background_steps = total Background steps / number of Background sections`.
- The Background is flagged **overused** when `avg_background_steps > 4`, **or** when any Background step's text contains one of the following heavy setup verbs (case-insensitive substring match): `create`, `insert`, `seed`, `load`, `import`, `call`, `post`, `put`, `delete`, `upload`, `generate`. These verbs were flagged by the QA team as conflating infrastructure concerns with scenario intent.
- `B_o = 0` if overused, otherwise `100`.

### 6.2 Setup-debt component (`B_d`)

This component detects scenarios that repeat the same initial steps without having promoted them to `Background`.

- Scenarios are grouped by their first step's **literal** text (not the normalized form); groups of two or more scenarios are then recursively re-grouped step-by-step for as long as the group keeps sharing the same next literal step. This produces one or more **shared initial blocks**.
- `background_candidate_distinct_lines` = the number of distinct literal steps that appeared in at least one shared position across any such group of ≥2 scenarios.
- `background_candidate_occurrences` = the sum, over every step that appeared in a shared position, of how many scenarios shared it there.
- `total_scenario_steps` = total step lines across all scenario bodies in the feature (Background steps excluded).
- `MBO = background_candidate_occurrences / total_scenario_steps`
- `background_debt_raw = background_candidate_distinct_lines · MBO`
- `B_d = max(0, 100 · (1 − background_debt_raw / 6.0))`

**Final score.**

```
BDI_s = min(B_o, B_d)
```

**Interpretation.** `100` means balanced Background usage and little setup debt; low values indicate a heavy/verb-laden Background, or repeated setup that is still embedded inside every scenario instead of being extracted.

**Evidence (`Raw Data` column).** The detected shared initial blocks, each shown as the scenario titles that share it plus the shared step lines, in order.

> **Note.** A related but separate guardrail — capping the *feature-level FMI* (not BDI itself) when the average Background length exceeds six steps — is described in §8. It reuses the same Background statistics but acts on the final index rather than on BDI's own score.

---

## 7. Average Scenario Length (ASL)

**Scope:** feature.

**What it measures.** The mean number of executable steps per scenario, excluding Background steps, as a proxy for cognitive load, readability, and maintainability.

**How it is computed.** For every `Scenario` and `Scenario Outline`, the number of its own step lines is counted (a `Scenario Outline` is counted once, using its templated step count — its `Examples` rows are not multiplied in). These lengths are averaged across all scenarios in the feature.

**Formula.**

```
ASL = total scenario steps / total scenarios

s_ℓ = 100                    if ASL ≤ 5
    = 50 · (7 − ASL)         if 5 < ASL < 7
    = 0                      if ASL ≥ 7
```

**Threshold rationale.** The QA team considers three to five steps the appropriate granularity for their test suite; longer scenarios tend to mix setup concerns with assertion logic, or collapse multiple behaviors into a single case, in ways they find difficult to maintain. The upper bound of 7 reflects the QA team's tolerance for moderately longer scenarios rather than a theoretically motivated cutoff.

**Interpretation.** Scenarios with 3–5 steps are usually easy to maintain; above 7 steps, consider splitting or simplifying them.

**Evidence.** ASL does not populate a separate `Raw Data` column — the per-scenario step counts, total steps, and scenario count already appear in `Calculated Data`, so a further evidence column would be redundant.

---

## 8. Feature Maintainability Index (FMI)

**Scope:** feature.

```
FMI = ¼ (SPC_s + OAR_s + BDI_s + ASL_s)
```

**Guardrail.** If the feature's average Background length (across all its Background sections) exceeds six steps, the raw average above is capped at `60`, regardless of what the four-metric average would otherwise produce. This is an additional safeguard layered on top of the plain average — a feature can have decent scores on every individual metric and still be capped if its Background is unusually long. The report distinguishes the two values explicitly:

- **Weighted Total Before Caps** — the plain four-metric average, `FMI` as defined above.
- **Feature Maintainability Index (final)** — the same value after the Background guardrail (if triggered) is applied. This final, possibly-capped value is what is used everywhere downstream (suite aggregation, interpretation label, `Repeated Steps` cross-references).

**Interpretation label.** For reporting convenience, the final FMI (and, at suite level, the SSI — §9) is additionally labeled `strong` (`≥ 75`), `moderate` (`50–75`), or `weak` (`< 50`). This label is descriptive metadata generated alongside the score; it is not part of the scoring formula itself.

**Compact score recap.** Each feature sheet also reports four summary scores as a shorthand for the table above:

| Summary label | Value |
|---|---|
| Step Quality | `SPC_s` |
| Scenario Design | `(OAR_s + ASL_s) / 2` |
| Background Design | `BDI_s` |
| Feature Maintainability Index | final FMI (post-guardrail) |

---

## 9. Suite-level totals

Suite scores are **macro-averages of the per-feature normalized scores** — they average the already-normalized `s` values from every feature, they do **not** recompute a single ratio from pooled raw counts across the whole suite.

```
SPC_suite = Σ(feature SPC_s) / total features
OAR_suite = Σ(feature OAR_s) / total features
BDI_suite = Σ(feature BDI_s) / total features
ASL_suite = Σ(feature ASL_s) / total features

SSI       = Σ(feature final FMI) / total features
```

**`SSI` (Structural Suite Index)** is the sole suite-level headline metric. An earlier revision of the tooling also computed a step-level reuse metric and a combined `SMI`; both have been removed. `SSI` is reported instead, and `SMI` must not be computed or displayed.

**Raw suite Background diagnostics.** For transparency, the Background metric's row in the `Totals` sheet also reports pooled raw counts, computed the same way as the per-feature debt calculation but over the whole suite:

```
suite_background_candidate_distinct_lines  = Σ(feature background_candidate_distinct_lines)
suite_background_candidate_occurrences     = Σ(feature background_candidate_occurrences)
suite_total_scenario_steps                 = Σ(feature total_scenario_steps)
suite_background_debt_raw = suite_background_candidate_distinct_lines
                            · (suite_background_candidate_occurrences / suite_total_scenario_steps)
                            (0 if suite_total_scenario_steps = 0)
```

This raw suite figure is shown for diagnostic purposes only; it does **not** replace `BDI_suite`, which remains the average of the per-feature `BDI_s` scores as defined above.

---

## 10. Repeated Steps evidence sheet

Alongside the metrics, the tool produces a `Repeated Steps` sheet listing every normalized step text that occurs in **more than one (feature, scenario) location** across the whole analyzed scope (a `.feature` file, a batch of files, or the full incremental suite). Background occurrences are included, listed under the scenario label `Background`.

Columns:

| Column | Meaning |
|---|---|
| `feature` | The feature the occurrence belongs to. |
| `scenario` | The scenario (or `Background`) the occurrence belongs to. |
| `step` | The literal step text of that occurrence. |
| `used in` | The full set of `feature / scenario` locations where this normalized step text appears. |
| `amount` | The total number of occurrences of this normalized step text across the scope. |

This sheet groups purely by the normalized step text with **no** "candidate reusable / data variation" requirement — it is broader than SPC's family concept and will also flag exact, non-parameterizable duplicates (e.g., a literal setup line copy-pasted verbatim across scenarios) that SPC would not treat as a candidate family at all, since SPC only considers families where the literal wording differs.

---

## 11. Incremental consolidation and metric recomputation

Because uploads may arrive in batches, the tool persists a JSON state file that is treated as the source of truth for the accumulated suite:

- Each batch's features are added to the accumulated state.
- If a feature with the same identity (§3.2) already exists in the state, the **older version is fully replaced**, not merged, by the new one.
- After every batch, `Totals` and `Repeated Steps` are **recomputed from the complete accumulated state**, not just from the latest batch — so every suite-level score (`SPC_suite` … `SSI`) always reflects the current full set of features, never a running average carried over from prior batches.
- The state stores, per feature, everything needed to recompute suite metrics exactly without re-parsing the original file: the feature's replacement identity, its full report payload, its normalized step set and occurrences, its per-metric normalized scores, its Background counts and candidate-debt counters, and its final FMI.
- Even a single, non-incremental run still produces this state file, so it can be reused as the starting point for a later batch.
- The state format carries a version marker. A state file produced by an earlier revision of the tool — e.g., one that still computed a step-level reuse metric or kept Background overuse and Background debt as two separate metrics instead of the single BDI — is not compatible with the current version and should not be reused with it.

---

## 12. Implementation caveats worth noting for replication

These are precise, code-level details that affect exact reproducibility but do not change the conceptual definitions above:

- **Supported inputs.** Only `.feature`, `.md`, and `.txt` files are parsed directly. A `.zip` archive can be treated as a single logical feature: every supported file inside it is aggregated so that all its `Background`, `Scenario`, and `Scenario Outline` bodies count toward one feature, identified by the zip's filename stem.
- **Step recognition.** A line is treated as a step only if it starts with `Given `, `When `, `Then `, `And `, `But `, or `* `. Trailing `#` comments are stripped before this check.
- **`Rule:` blocks.** A `Rule:` header is recognized by the title-line pattern but is not otherwise handled by the parser: it does not close whatever scenario or Background is currently open, so steps continue to accumulate into the previously open block across a `Rule:` line.
- **Data tables vs. Examples tables.** Tables attached directly to an ordinary step are not parsed into structured data. Only `Examples:` tables under a `Scenario Outline` are captured (as header/row pairs), and they feed only descriptive summary fields (row/column counts), not any of the four scored metrics.
- **SPC's "candidate reusable" edge case.** Because step normalization only rewrites quoted strings, bare numbers, `<placeholder>` tokens, and case/whitespace, two literal step texts can in principle collapse into the same family purely because of a whitespace or case difference, with no actual data token in the shared signature. Such a family is still counted as *candidate reusable* (it has more than one distinct literal text) but will **not** be counted as *parameterized*, since its normalized signature contains none of `{string}`, `{int}`, or `{param}`. This is a rare, purely typographical edge case, but it is the one situation where "candidate reusable" and "varies by an actual data value" can diverge.

---

## 13. Excel and reporting conventions (for cross-reference)

The metrics above are the ones rendered in the accompanying Excel workbook, one worksheet per feature plus a `Totals` and a `Repeated Steps` sheet. Each feature worksheet's metrics table uses ten columns: `Metric / Concept`, `Scope`, `What it measures for maintainability`, `How to measure it`, `Practical formula / rule`, `Calculated Data`, `Raw value`, `Normalized score (0-100)`, `Example / interpretation`, and `Raw Data` — the first five and the `Example / interpretation` column are fixed text per metric; `Calculated Data`, `Raw value`, `Normalized score`, and `Raw Data` are computed per feature exactly as described in §§4–8. The `Totals` sheet reuses the same fixed columns but omits `Raw value` and `Raw Data`, since the equivalent raw suite diagnostics are already folded into `Calculated Data` (see §9). Workbook styling (LKS Next navy/cyan/charcoal/gray palette, no frozen panes) is a presentation concern only and does not affect any of the formulas above.