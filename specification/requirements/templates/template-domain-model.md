# Domain Model

**Owner:** @[user]

**Last updated:** DD/MM/YYYY

**Sources:** [Domain audit, documentation, or validated requirements]

Create and maintain this document with `create-domain-model`. Include only
concepts supported by evidence, and mark each one `Implemented`, `Documented`,
or `Proposed`. Mark unproven cardinalities or meanings `To confirm`. These
values are fixed literals: keep them as written. Every entity, value object,
state, enumeration, or rule name must match a `Preferred term` in
`glossary.md`; if it does not exist yet, add it there as `Pending` in the
same pass.

## 1. Purpose and scope

[Functional capability the model describes, what it covers, and known
exclusions]

### Quick visual (optional)

[For domains with multiple contexts, optionally show 2-4 central concepts here.
See section 8 for the complete, evidence-backed concept map.]

```mermaid
classDiagram
    [CentralConcept] --> [RelatedConcept] : [relationship]
```

## 2. Contexts or subdomains

| Context | Responsibility | Main concepts |
|---------|----------------|---------------|
| [Context] | [Responsibility] | [Concepts] |

## 3. Entities and relevant attributes

| Entity | Attribute | Type | Required | Constraints | State |
|--------|-----------|------|----------|-------------|-------|
| [Entity] | [Attribute] | [Type] | yes / no | [Rules or valid range] | Implemented / Documented / Proposed |

## 4. Value objects, states, and enumerations

| Name | Kind | Values or rules | State |
|------|------|-----------------|-------|
| [Name] | value object / state / enumeration | [Values] | Implemented / Documented / Proposed |

## 5. Known relationships and cardinalities

| Source | Relationship | Target | Multiplicity | Ownership | State |
|--------|--------------|--------|--------------|-----------|-------|
| [Entity] | [Relationship] | [Entity] | [1 / 0..1 / 1..* / 0..* / To confirm] | source / target / none / To confirm | Implemented / Documented / Proposed |

## 6. Processes and business rules

| ID | Process or rule | Description | Related concepts | State |
|----|-----------------|-------------|------------------|-------|
| [RULE-N] | [Name] | [Description] | [Concepts] | Implemented / Documented / Proposed |

## 7. Actors and external integrations

| Actor or system | Kind | Interaction | State |
|-----------------|------|-------------|-------|
| [Name] | actor / external system | [Inputs, outputs, or services] | Implemented / Documented / Proposed |

## 8. Concept map

[Show every entity in section 3 and every relationship in section 5, or justify
any omissions. This is the complete, evidence-backed map; the quick visual in
section 1 is only a preview. For domains with only a few entities, the diagram
may be omitted with a short explanation.]

```mermaid
classDiagram
    [SourceConcept] --> [TargetConcept] : [relationship]
```

### Diagram legend

- `-->` relationship or reference
- `*--` composition or ownership
- `o--` aggregation
- `1`, `0..1`, `1..*`, `0..*` multiplicity
- Dashed lines indicate inferred or unconfirmed relationships

## 9. Evidence matrix

| Concept | File | Symbol or reference | State |
|---------|------|---------------------|-------|
| [Concept] | [Path or link] | [Qualified symbol, section, or commit] | Implemented / Documented / Proposed |

Also use this table to cite `glossary.md` as the reference when a concept's
only support is terminological, not code.

## 10. Gaps, ambiguities, and pending decisions

| Topic | Description | Pending action |
|-------|-------------|----------------|
| [Topic] | [Gap, ambiguity, or contradiction] | [Decision or confirmation needed] |

## 11. Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| DD/MM/YYYY | @[user] | [Change description] | [Agent and visible model, or - if manual] |
