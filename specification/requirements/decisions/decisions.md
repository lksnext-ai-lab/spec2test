# Requirements Decisions

Permanent register of decisions on requirements that come from documentary
sources (`REQ-N`). Only `analyst-source-traceability` writes it, through
`decide-requirement`: each requirement adds a row to the index and, while it is
pending or approved, a section following `template-decision.md` in the
configured templates path; a rejected requirement keeps only its index and
summary rows.

Code audit findings are not recorded here: they go through human validation,
`create-domain-model`, and `refine-epic`.

## Decision Values

| Value | Meaning |
|-------|---------|
| Unreviewed | Initial value only; the requirement has not been analyzed yet |
| Pending | Analyzed and awaiting the user's decision |
| Approved | Accepted for incorporation into the target epic |
| Rejected | Not incorporated; only its index and summary rows are kept |

## Requirements Index

| ID | Name | Source | Target epic | Target | Decision | Priority |
|----|--------|--------|---------------|---------|----------|-----------|

## Decision Summary

| ID | Name | Epic | Decision | Impact | Priority | Date | Rationale |
|----|--------|-------|----------|---------|-----------|-------|--------|

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
