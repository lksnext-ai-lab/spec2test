---
name: audit-domain
description: "Extracts what already exists in the code for a functional domain by answering a fixed set of questions with the best available tool, and consolidates evidence, confidence, and contradictions in an audit document. Use when analyst-requirements must discover what the code already implements for a domain before modeling or writing requirements."
---

# Skill: Audit Domain

Information-gathering skill that answers: *"What already exists in the codebase
for this domain?"* It owns the whole extraction, including the entry-point
inventory. It never installs or indexes CBM: that is infrastructure owned by
`operator-codebase-memory`, which the calling agent invokes beforehand when
needed.

It runs inside `analyst-requirements`, whose `execute` tool runs the read-only
`git` and `gh` commands this skill needs (for example for Q6).

## Expected input

- Functional domain name, for example `orders` or `invoices`
- Optionally, the CBM state returned by `operator-codebase-memory`: project,
  generation, and coverage, or "CBM not available"

Run this skill only after explicit audit authorization. Installing or indexing
CBM does not authorize an audit. If the user requested only setup, do not run
this skill.

## Code-discovery flow in analyst-requirements

The calling agent drives these steps around the audit:

1. **Before:** read `integrations.codebase_memory`. CBM is optional: when
   `enabled` is `false` or the user declines it, go straight to the audit,
   which uses the configured `fallback` and records the reduced coverage.
   When CBM is enabled and not ready (executable missing, index absent or
   stale, project association pending), ask whether to prepare it; if the
   user accepts, delegate to `operator-codebase-memory` with the configured
   alias and repository path. The operator requests its own authorizations
   and returns only the index state; it never inventories, audits, or
   delegates back. Pass that state to this skill.
2. **During:** pause with the user at each module this skill proposes.
3. **After:** validate the findings with the user. A finding the user rejects
   as intended behavior becomes a defect; an unresolved contradiction stays as
   an open question in the scenario comments. Then run `create-domain-model`
   (mandatory after every validated audit) and turn each confirmed finding
   into a requirement with `refine-epic` (the direct audit → model → epic
   path: no `requirement-sources` or decision entry is created, because the
   decision file under `paths.decisions` only records decisions on documentary
   sources).

Never install binaries, caches, or indexes inside the destination.

## Workflow

### 1. Resolve scope and tools

Read `.project.yml` (or use the resolved values the caller passes) and
resolve enabled aliases from `repositories`.

CBM is one tool among others, not the axis of the audit. Use it through MCP
only when `integrations.codebase_memory.enabled` is `true` and the project
association is `confirmed`; only then read the *Query order* and *Mapping to
the audit questions* sections of
[references/codebase-memory-mcp.md](references/codebase-memory-mcp.md).
Otherwise use local search (the configured `fallback`, see
[Fallback](#fallback)) and record the limitation. Without CBM only the
structural questions degrade; every other question keeps its best tool.

### 2. Inventory entry points

This is always the first extraction step. List entry points by module
(routes, jobs, listeners, commands, screens) with CBM when ready, or with
local search when not. Label requirements tooling embedded in an
implementation root separately from product behavior. Present the inventory
grouped by module and pause for the user's module selection.

### 3. Read epics and features

Read relevant domain scenarios from the configured epic path in `.project.yml`.
If no requirements exist for this domain, record their absence as the starting
condition and skip scenario comparison until formalization.

### 4. Answer the audit questions

For each selected module, answer the questions below in order. For each
question use the best available tool, falling back down the list. If a question
does not apply or no tool is available, write `Not applicable` or
`Not available` with the reason; never leave a section silently empty.

| # | Question | Tools, best to worst | Output |
|---|---|---|---|
| Q1 | Which behaviors do the tests pin down? | Read the tests; CBM to relate test to code | Behaviors asserted by tests; tests are the starting point |
| Q2 | Which capabilities are exposed? | Specification file (OpenAPI, GraphQL, proto) → routes in code (CBM or local search) → framework route listing (runs code: requires separate authorization) | Capability inventory |
| Q3 | Which entities, states, and rules exist? | Migrations, entities, enums, constraints | Entities, states, and rules; feeds `create-domain-model` |
| Q4 | Who can do what? | Guards, policies, roles (CBM or local search) | Actor × capability summary |
| Q5 | How does the user name it? | i18n texts, screens, validation messages | Vocabulary for the glossary |
| Q6 | Why does it exist? | Commits, pull requests, issues (`gh`, read-only) | Intent; the only source of why |
| Q7 | What calls what? | CBM → local search and LSP | Call paths to persistence and integrations |

For each selected entry point keep the raw observation: trigger, inputs,
validations, decisions and values, reads/writes, integrations, permissions,
errors, supporting tests, qualified symbol, linked file, and coverage. Do not
infer requirements, implementation completeness, or test success from these
observations. Pause after each module; the analyst formalizes only
user-confirmed findings.

CBM and contracts: CBM may see routes declared in code when its schema exposes
routes for that framework (check with `get_graph_schema`). Do not rely on it
for specification files (YAML, GraphQL, proto) and it never sees contracts
generated at runtime; read those files directly.

For each repository alias, delegate questions to `repositories[].specialist_agent`
in consultation mode when it is set. When it is empty, inspect the repository
locally in read-only mode and record "no specialist configured; local
read-only inspection" as a limitation.

### 5. Assign evidence and confidence

Every finding carries at least one verifiable link and a confidence level:

- **High:** several independent sources agree (for example a test and the code).
- **Medium:** only clear code supports it.
- **Low:** inferred (naming, comments, partial reads).

Confidence lives only in the audit. Never add it as a column to epic tables.

Each finding also carries an evidence state, a fixed literal never translated
whatever `project.language` is: `Implemented` (confirmed in code),
`Documented` (only in existing documentation), or `Proposed` (inferred or not
yet supported), with the `To confirm` marker for open points.
`create-domain-model` uses these same literals.

### 6. List contradictions

When sources disagree (the test says X and the code does Y, the specification
declares an operation the code does not implement, a message contradicts a
rule), list the case in the contradictions section as a question for the owner.
Do not decide which side is right. When the finding is formalized, `refine-epic`
copies the question into the scenario's comments table.

### 7. Consolidate

Generate the current-state document.

## Output

**File:** `<paths.tasks>/<integrations.codebase_memory.evidence_path>/audit-<domain>-<YYYY-MM-DD>.md`
(`evidence_path` is relative to `paths.tasks`; installer default `auditorias`
for `es` and `audits` for `en`). Resolve both values from `.project.yml`; do
not invent another audit directory or file name. The audit identifier is the
file name without extension, for example `audit-orders-2026-09-27`; epics and
the traceability matrix cite it.

```markdown
# Domain Audit: <domain>
**Date:** <YYYY-MM-DD>
**Audit ID:** audit-<domain>-<YYYY-MM-DD>

## Scope and Tools
| Alias | Modules | CBM state | Fallback | Limitations |
|---|---|---|---|---|
| [alias] | [selected modules] | [project, generation, coverage / not available] | [local search / none] | [detail] |

## Entry-Point Inventory
| Module | Entry point | Kind | Qualified symbol and file | Coverage |
|---|---|---|---|---|
| [module] | [route/job/listener/command/screen] | [kind] | [link] | [ok/gaps/unknown] |

## Q1. Behaviors Pinned by Tests
| Behavior | Test (file, case, link) | Code (symbol, link) | Confidence |
|---|---|---|---|

## Q2. Exposed Capabilities
| Capability | Source (specification operation or route, link) | Handler | Confidence |
|---|---|---|---|

## Q3. Entities, States, and Rules
| Entity or rule | Source (migration, entity, enum, constraint, link) | Values | Confidence |
|---|---|---|---|

## Q4. Actors and Permissions
| Actor | Capability | Source (guard, policy, role, link) | Confidence |
|---|---|---|---|

## Q5. User Vocabulary
| Term | Where it appears (i18n key, screen, message, link) | Candidate glossary entry |
|---|---|---|

## Q6. Intent
| Capability | Reference (`alias#N` or commit, link) | Stated reason |
|---|---|---|

## Q7. Call Paths
| Entry point | Path to persistence or integrations | Tool | Confidence |
|---|---|---|---|

## Contradictions
| # | Sources in conflict (links) | Question for the owner |
|---|---|---|

## Technical Evidence
| Alias | CBM project | Commit/generation | Tool/query | Symbol or path | Coverage | Confirmation | Limitations |
|---|---|---|---|---|---|---|---|

## Requirement Gaps
- [What documented scenarios require that does not yet exist]
```

Write `Not applicable` or `Not available` with the reason under any question
section that has no rows. In code-first mode (no documented scenarios), omit
`Requirement Gaps`: without scenarios no gap can be established. Keep alias,
commit or generation, and coverage beside every link.

## Evidence record

Record in the Technical Evidence table, for each relevant finding: alias (from
`repositories`), CBM project (name returned by `list_projects`), analyzed
commit if available and index generation or date, tool and query, qualified
symbol or path with lines if available, observed result, coverage (complete,
partial, or unknown), confirmation (snippet, local reading, documentation, or
unconfirmed), and limitations (exclusions, pagination, unindexed files, or
fallback). Raw findings keep the step 4 observation fields plus supporting
tests, index coverage (ok or gaps), observations, and confidence. This skill
does not draft requirements; the analyst formalizes only user-confirmed
findings later.

## Interpretation rules

- A graph finding is evidence of structure, not of correct functional behavior.
- An absence is conclusive only with complete coverage and an adequate query.
- With partial coverage, write `Not found within the analyzed scope`, never
  `Does not exist`.
- Separate `Implemented`, `Documented`, and `Proposed` (inferred or not yet
  confirmed), the evidence states that `create-domain-model` uses.
- Do not automatically turn a class, endpoint, or module into a business
  requirement.
- Do not cite personal absolute paths in requirements-repository documents.
- Do not analyze the requirements repository as an implementation repository
  unless it is explicitly declared as one.

## Fallback

When CBM is disabled or unavailable:

1. use `ripgrep` or an equivalent search;
2. read only small files or targeted ranges;
3. record `local fallback` and the examined scope;
4. lower confidence and avoid exhaustive claims.

## Checklist

- [ ] Resolve `.project.yml`, configured aliases, and the CBM state
- [ ] Inventory entry points first and pause for module selection
- [ ] Answer Q1–Q7 with the best available tool, or mark them not applicable or
      not available with a reason
- [ ] Give every finding a verifiable link and a confidence level
- [ ] List contradictions as questions without resolving them
- [ ] Check coverage before claiming absence
- [ ] Consult `repositories[].specialist_agent` or record a local inspection
- [ ] Separate facts, inferences, and pending confirmations
- [ ] Do not modify code; use read-only operations (running framework route
      listings requires separate authorization)
