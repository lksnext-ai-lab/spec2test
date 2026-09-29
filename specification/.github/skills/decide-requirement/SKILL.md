---
name: decide-requirement
description: Presents each requirement extracted from documentary sources with traceability, source, and impact context, records the user's decision in the configured decision file following the decision template, and delegates analysis and execution to other skills. Use when documentary sources must be compared with the epics or a REQ-N needs a decision.
---

# Decide Requirement

Answers: *"Review the sources and decide which changes belong in the epics."*

Guides the user through each requirement found in the documentary sources,
presents progressive context (problem, source, destination, impact), and
records the decision. Deeper analysis and execution are delegated.

## Related skills

These skills run in `analyst-requirements`, never inside this workflow; record
the request in the result returned to it.

| Skill | Request when |
|-------|---------------|
| `analyze-impact` | The user wants detailed impact on existing code |
| `audit-domain` | The user wants to know what exists in the codebase |
| `refine-epic` | An approved requirement must be added to an epic |
| `analyze-requirement` | An approved requirement needs a technical breakdown |

## Configuration

Resolve paths from `.project.yml`; do not ask the user for paths that are
configured:

| Parameter | Source |
|-----------|--------|
| Decision file | a file under `paths.decisions` (ask only which file when several exist or none exists yet) |
| Decision template | `<paths.templates>/template-decision.md` |
| Requirement source register | `<paths.requirement_sources>/requirement-sources.md` |
| Requirement source template | `<paths.templates>/template-requirement-source.md` |
| Original documents | `<requirements root>/sources/` |
| Epics | `paths.epics` |
| Analysis plan (temporary) | a file under `paths.plans`; ask for its name only when creating it |

Ask the user only for values that are not configured or are unresolved (see
the unresolved-value rule in `project-workflow.instructions.md`).

## Files

- **Analysis plan (temporary):** lists the gaps between sources and epics
  (GAP-FNN mapped to REQ-N). It exists only during the decision process.
- **Decision file (permanent):** follows the decision template.
- **Requirement source register (permanent):** receives one `RSRC-N` entry,
  from the requirement source template, for each new original document (see
  step 0).

These are the only files this skill creates or modifies.

Epics, the domain model, and other documents are never modified here.

## Decision values

Use literally the decision values defined in the decision-values table of the
decision template (en: `Unreviewed`, `Pending`, `Approved`, `Rejected`; es:
`Sin revisar`, `Pendiente`, `Aprobado`, `Rechazado`), in `project.language`.
Never add emoji to the file; emoji are allowed in chat only. Unreviewed is only
the initial value; a requirement never goes back to it.

## Workflow

### 0. Analysis plan

First register new sources: for each original document under
`<requirements root>/sources/` that no `RSRC-N` entry of
`<paths.requirement_sources>/requirement-sources.md` references, propose a new
entry created from `template-requirement-source.md` (next free `RSRC-N`,
identification, and summary, without replacing the original) and add it to the
register's index and sections only after the user confirms it. Never renumber
existing `RSRC-N` entries.

If the plan exists, read it. Otherwise create it: read every source record in
the register (and the original documents when ambiguous), every epic under
`paths.epics`, and the domain model `<paths.domain_model>`;
cross-reference them and list the gaps. Tell the user the plan is temporary.

### 1. Decision file

If it exists, read it and resume from the recorded decisions. The installed
`decisions.md` starts as an empty register (headings and tables without rows):
add every REQ-N of the plan to its requirements index as unreviewed (source and
destination `-`, no REQ section). If no decision file exists, create it from
the decision template with that same index.

The decision file only records decisions on documentary sources. Code audit
findings are validated by `analyst-requirements` and never recorded here.

### 2. Present the requirement

For each unreviewed or pending REQ-N, present in chat:

```markdown
## REQ-N: <name>

**Traceability problem:** <what the epics are missing>

**What the source says:**
> <quote or faithful summary, with file reference>

**Proposed destination:** <epic ID> -> <feature ID> -> new or modified scenario

**Impact:** traceability, functional, domain model, cascade, implementation
(none/low/medium/high with a short detail). Ask whether to request a detailed
`analyze-impact` from `analyst-requirements`; if so, leave the REQ-N pending.

Approve, reject, or leave pending?
```

### 3. Prepare the REQ section

Prepare the REQ-N section as a preview with exactly the subsections, order,
and tables of the decision template for `project.language` (traceability
problem, source, proposed destination, impact analysis with the template's
dimensions). Do not write it before the user's decision.

When the requirement has been analyzed, fill the source and destination
columns of its index row and move it from unreviewed to pending.

### 4. Record the decision

After the user's explicit decision:

1. Write or update the REQ-N section, filling its decision subsection with
   the decision value, date, author, and comments.
2. Update the requirements index row.
3. Update the decision summary table.
4. Add a change history row; record Author and Agent per
   `.github/instructions/references/change-history.md`.
5. If rejected, remove the REQ-N section and keep only its index and summary
   rows (with date and rationale).

### 5. Approved requirements

The REQ-N section keeps everything needed for execution. Return it to
`analyst-requirements`, which applies epic changes with `refine-epic`, the
technical breakdown with `analyze-requirement`, and code impact with
`analyze-impact`.

### 6. Next and completion

Offer the next pending REQ. When none remain, show a summary (approved,
rejected, pending, unreviewed) and ask whether to delete the temporary plan.

## Rules

- Never modify epics, the domain model, or other documents.
- Never assume the plan exists; check first.
- Always include date and author in each decision.
- Always update the index, the summary, and the change history together.

## Checklist

- [ ] Paths resolved from `.project.yml`.
- [ ] New original documents registered as `RSRC-N` after confirmation.
- [ ] Plan verified or created.
- [ ] Decision file verified or created from the template.
- [ ] REQ-N presented with progressive context.
- [ ] REQ-N section follows the template exactly.
- [ ] Decision recorded in the section, index, summary, and change history.
- [ ] Rejected sections removed.
- [ ] User asked whether to delete the plan at the end.
