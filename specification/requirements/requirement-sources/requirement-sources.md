# Requirement Source Register

Permanent register of the authorized documentary sources (`RSRC-N`) whose
original documents are stored in the requirements `sources/` folder. Only
`analyst-source-traceability` writes it, through step 0 of
`decide-requirement` and after user confirmation: each new source adds a row to
the table and a section following `template-requirement-source.md` in the
configured templates path. The register does not replace the original
documents.

Code audit findings are not recorded here: they go through human validation,
`create-domain-model`, and `refine-epic`.

## Authorized requirement sources

| ID | Name | Type | Location | Date | Author | Status | Related requirements |
|----|--------|------|-----------|-------|-------|--------|-------------------------|

## Change history

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
