---
name: create-domain-model
description: Consolidates a code audit into the domain model and project glossary while preserving traceability and separating implementation evidence from inference. Use when a validated domain audit must be formalized before epics are written.
---

# Skill: Create Domain Model

Functional consolidation skill that transforms a domain audit into a formal
model reusable by epics, impact analyses, and implementation plans.

## Responsibility

This skill creates or updates the model document `<paths.domain_model>`
and the glossary `<paths.glossary>` from `.project.yml`. It does
not implement code, create issues, or write epics. `analyst-requirements` runs
it after every validated audit, before `refine-epic`.

## Required inputs

- `.project.yml` as the source of truth for paths, language, and repositories.
- An `audit-domain` audit or equivalent codebase evidence.
- `<paths.domain_model>` and `<paths.glossary>`, when
  they exist.
- The templates `<paths.templates>/template-domain-model.md` and
  `<paths.templates>/template-glossary.md`.
- Related epics and sources to avoid duplicating or contradicting concepts.

If no audit exists, request or generate one before continuing.

## Workflow

### 1. Collect evidence

- Read the audit and its code references.
- Confirm each entity, value, relationship, process, and rule in a verifiable
  source.
- Mark each item `Implemented`, `Documented`, or `Proposed`; never present an
  inference as existing behavior. These evidence states, and the `To confirm`
  marker below, are fixed literals shared with `audit-domain`: they are not
  translated, whatever `project.language` is.
- Preserve CBM provenance when available: alias, project, commit or generation,
  query, symbol/path, and coverage.
- Distinguish graph findings, confirmed source code, documentation, and
  inference.

### 2. Define the domain boundary

- Group concepts by functional capability, not filename.
- Identify external actors, inputs, outputs, services, and system boundaries.
- Separate domain concepts from infrastructure details.
- Record gaps and documentary contradictions as observations, not domain facts.

### 3. Formalize the model

The model document is always `<paths.domain_model>`. If it is
missing, or only contains the seed placeholder (it lacks the sections of
`template-domain-model.md`), create it from
`<paths.templates>/template-domain-model.md`; otherwise update it in place.
Write it in `project.language`, keeping the template's sections:

1. Purpose and scope.
2. Contexts or subdomains.
3. Entities and relevant attributes.
4. Value objects, states, and enumerations.
5. Known relationships and cardinalities.
6. Processes and business rules.
7. Actors and external integrations.
8. Concept map covering every entity in section 3 and relationship in section
  5, or explaining omissions. Use one diagram per context if section 2 lists
  multiple contexts. An optional quick visual under section 1 may summarize
  central concepts but never replaces the complete map in section 8.
9. Evidence matrix with file, symbol or reference, and state (`Implemented`,
   `Documented`, or `Proposed`).
10. Gaps, ambiguities, and pending decisions.
11. Change history: one row per modification, with Author and Agent per
    `.github/instructions/references/change-history.md`.

Include only attributes, relationships, and rules supported by evidence. When
cardinality or meaning is unproven, mark it `To confirm`. A CBM index without
gaps does not prove functional completeness; always record scope and known
exclusions.

### 4. Synchronize terminology

Update `<paths.glossary>` (created from
`<paths.templates>/template-glossary.md` when missing) with preferred model
terms. Keep one definition per concept and preserve the template's configured
state. Do not introduce ambiguous synonyms without recording them.

Every entity, value object, state, enumeration, or rule name written into the
model must match a `Preferred term` in the glossary. Add a missing term there
as `Pending` in the same pass instead of leaving it orphaned. In the other
direction, when the glossary already carries a term that a previous pass left
`Pending` and this audit now confirms it with code evidence, update the state
of the corresponding model row accordingly (never past `Proposed` or
`Documented` without that evidence). Record every glossary addition or state
change in its `## Change History` section, following
`.github/instructions/references/change-history.md`, the same way as for the
model document.

### 5. Verify dependencies

- Check that links and paths exist.
- Check that epics use preferred terms.
- Cross-check every entity and relationship in sections 3 and 5 against the
  section 8 map; explain omissions and keep any section 1 preview consistent.
- Detect concepts used in requirements but missing from the model.
- Do not change epics automatically without recording the impact.

## Output

- Created or updated `<paths.domain_model>`.
- Synchronized `<paths.glossary>`.
- Summary of new, modified, and pending concepts.
- References to the audit and code sources.

## Quality rules

- The model describes the real system, not a future architecture.
- Every concept needs evidence or an explicit `Proposed` marker.
- Do not create entities merely because technical names appear.
- Do not turn every service, endpoint, or file into a domain entity.
- Keep business documents in `project.language`.
- Run configured validation after modifying documents.

## Checklist

- [ ] `.project.yml` and `template-domain-model.md` were read.
- [ ] The model is `<paths.domain_model>` with every template section.
- [ ] An audit or equivalent evidence exists.
- [ ] The model distinguishes implemented, documented, and proposed.
- [ ] Entities, relationships, and rules are traceable.
- [ ] The section 8 map reflects every entity and relationship in sections 3
  and 5, or omissions are justified; any section 1 preview agrees with it.
- [ ] The glossary uses model terms; new ones were added as `Pending`.
- [ ] Gaps and pending decisions are documented.
- [ ] Repository validation was run.