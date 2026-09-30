---
name: reconcile-requirements
description: Reconciles the domain model, glossary, and traceability matrix after a requirement epic, feature, or scenario is created or changed, then regenerates the index and runs validation. Use when analyst-requirements creates or changes requirement content, with or without a domain audit.
---

# Reconcile Requirements

Run by `analyst-requirements` for every creation or change of a requirement
epic, feature, or scenario, including changes applied from documentary
decisions, issue or E2E proposals, and code audits. This reconciliation is
required even when the work does not include a domain audit.

Before writing, read the current epic template under `paths.templates`: it is
the source of truth for section names, columns, and allowed values; do not add
historical structures. Content rules for code links, sources, contradictions,
and matrix rows are in
[refine-epic/references/content-rules.md](../refine-epic/references/content-rules.md).

## Steps

1. **Resolve.** Resolve the destination requirements repository,
   `paths.domain_model`, `paths.glossary`, `paths.traceability_matrix`, and `project.language`
   (from the caller's resolved values or the destination's `.project.yml`).
   If the language or paths cannot be resolved, request clarification before
   writing.
2. **Compare before editing.** Read `<paths.domain_model>` and
   `<paths.glossary>`. If either is missing, create it from
   its template under `paths.templates` (`template-domain-model.md` or
   `template-glossary.md`). Compare the affected concepts, definitions,
   relationships, and business rules with the proposed change and its
   sources. For code-derived behavior, apply *Code-derived content* of the
   content rules (navigable code links with alias, symbol, file, commit or
   generation, and coverage). Never set the completed value of
   `specification.states` from code or a closed issue: record human
   validation when `workflow.human_validation_required_for_completion` is
   `true`, and keep E2E results separate.
3. **Model and glossary.** After editing, reconcile both documents in
   `project.language`. If the model document only contains the seed
   placeholder (it lacks the sections of `template-domain-model.md`), create
   it from the template with the concepts that have support; "update only if
   needed" does not apply in that case. Otherwise update each document where
   the change introduces or revises supported concepts; if no update is
   needed, explicitly report that both were reviewed and why they remain
   unchanged. Distinguish documented requirements from implemented behavior
   and mark unconfirmed concepts as proposed or pending; do not invent domain
   facts.
   Every entity, value object, state, enumeration, or rule name written into
   the model must match a `Preferred term` in the glossary; add a missing
   term there as `Pending` in the same pass instead of leaving it orphaned.
   In the other direction, when the glossary already carries a term that a
   previous pass left `Pending` and this change now confirms it with
   evidence, update the state of the corresponding model row accordingly.
   When entities or relationships in sections 3-5 change, update the section
   8 concept map in the same pass and keep the optional section 1 quick visual
   consistent with it; justify any omitted entities or relationships.
4. **Matrix.** Review `paths.traceability_matrix` after each requirement
   change. Add one row for every new scenario, even without an issue or E2E
   test; update affected rows when scenario IDs, sources, epic/feature links,
   tasks, or supported implementation or E2E evidence change. Do not add a
   row for an epic or feature without scenarios or infer issues, coverage, or
   test results. Retain independent implementation and E2E states, using
   only configured values. If no relationship changed, report that the matrix
   was reviewed and remains unchanged.
5. **Validate and regenerate.** Check terminology and links across the
   affected requirements, model, glossary, and matrix, then run the
   configured validation. Always regenerate the index at
   `paths.requirements_index` with `python scripts/idx.py build` after
   editing epics; it is a generated file and is never edited by hand. When
   `modules.consolidate_epics` and `features.consolidate_epics.enabled` are
   both `true`, also run `python scripts/consolidate-epics.py` (output in
   `<paths.epics>/epics-consolidated.md`). The generated files are committed
   together with the epic changes.
6. **Identifiers.** Never renumber existing identifiers; report gaps and ask
   before any renumbering.
7. **Change history.** Fill the epic's change-history section per
   `.github/instructions/references/change-history.md`, and do the same in
   the domain model's and glossary's own `## Change History` sections for
   every row touched in step 3.

`create-domain-model` is mandatory after every validated audit; for changes
without an audit it stays optional and is used when a deeper evidence-backed
model update is needed, without treating the absence of an audit as
permission to skip this review.

## Output

Report the files changed, the files reviewed without changes, the generated
files, and any evidence limitations.
