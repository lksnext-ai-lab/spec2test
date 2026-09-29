# EPIC-4: Project Provisioning for Docker Compose

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Medium

## Overview

Validates the host's `projects.json` and generates the Docker Compose
override that mounts each configured project's `inputs`, `preprocessed`, and
`cache` folders into the `input-processor` and `filesystem-mcp` services,
creating the output folders on the host as needed. Its own docstring states
that its container-side counterpart is `input-processor/src/projects/model.py`
(see EPIC-1): the two must agree on the project name rule and folder layout.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-scripts-2026-09-29`; it is not new work.

## Feature Index

- [FEAT-4-1: Validate project configuration](#feat-4-1-validate-project-configuration)
- [FEAT-4-2: Generate the Compose override](#feat-4-2-generate-the-compose-override)

## Dependencies

- EPIC-1: the project name rule and `inputs`/`preprocessed`/`cache` layout must stay compatible with `input-processor/src/projects/model.py`.

## References

- Code: spec2test: [scripts/sync_projects.py](../../../scripts/sync_projects.py)
- Audit: [audit-scripts-2026-09-29](../../tasks/audits/audit-scripts-2026-09-29.md)
- Domain model: [domain-model.md](../domain-model.md)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result.

---

## FEAT-4-1: Validate project configuration

**Source:** spec2test: [scripts/sync_projects.py#L71-L149](../../../scripts/sync_projects.py) load_config/check_paths

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Reads `projects.json`, resolving each project's `inputs`, `preprocessed`, and `cache` host paths, and rejects invalid or duplicate project names, malformed configuration, and missing input folders (reporting every missing folder together).

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-4-1-1 | Project paths are read from the configuration, with sensible defaults | Each project's inputs, preprocessed, and cache paths are resolved from `projects.json`, defaulting preprocessed/cache to a hidden data directory | Completed | spec2test: [sync_projects.py#L71-L126](../../../scripts/sync_projects.py) load_config/_project/_resolve; spec2test: input-processor/tests/test_sync_projects.py test_paths_are_read_from_the_configuration_file |
| ESC-4-1-2 | A missing, invalid, or malformed configuration file is reported | A missing file, invalid JSON, a non-object root, a non-object entry, or an empty projects list is reported as a configuration error | Completed | spec2test: [sync_projects.py#L71-L118](../../../scripts/sync_projects.py) load_config/_project; spec2test: input-processor/tests/test_sync_projects.py test_a_missing_configuration_file_is_reported |
| ESC-4-1-3 | An invalid or duplicate project name is refused | A project name that does not match the slug pattern, or that duplicates another project's name, is rejected | Completed | spec2test: [sync_projects.py#L41](../../../scripts/sync_projects.py), [#L101-L134](../../../scripts/sync_projects.py); spec2test: input-processor/tests/test_sync_projects.py test_invalid_names_are_refused |
| ESC-4-1-4 | Missing input folders are reported together | Every project with a missing `inputs` folder is listed in a single error, not just the first one found | Completed | spec2test: [sync_projects.py#L137-L149](../../../scripts/sync_projects.py) check_paths; spec2test: input-processor/tests/test_sync_projects.py test_missing_inputs_are_reported_together |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a valid `projects.json`, when it is loaded, then each project's paths are resolved with the documented defaults.
- [x] Given a missing or malformed `projects.json`, when it is loaded, then a configuration error is reported.
- [x] Given an invalid or duplicate project name, when the configuration is loaded, then it is rejected.
- [x] Given several projects with missing `inputs` folders, when paths are checked, then all of them are reported together.

### Technical Notes

The project name rule and folder layout must stay compatible with `input-processor/src/projects/model.py` (RULE-12); see EPIC-1.

### Testing Notes

Covered by `input-processor/tests/test_sync_projects.py`.

## FEAT-4-2: Generate the Compose override

**Source:** spec2test: [scripts/sync_projects.py#L159-L254](../../../scripts/sync_projects.py) configured_services/render_override/main

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Creates the host-side output folders and writes `docker-compose.override.yaml`, mounting every configured project into only the services that both need project folders and are already declared in the base compose file, with a `--check` mode that validates and previews without writing.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-4-2-1 | The override only lists services declared in the base compose file | Services that need project folders but are not defined in the base compose file are excluded; a base file with neither service is reported as an error | Completed | spec2test: [sync_projects.py#L159-L185](../../../scripts/sync_projects.py) configured_services; spec2test: input-processor/tests/test_sync_projects.py test_services_are_read_from_the_base_compose_file |
| ESC-4-2-2 | The generated override mounts every project into both services | Each project's inputs, preprocessed, and cache paths are mounted into every service the override targets | Completed | spec2test: [sync_projects.py#L188-L205](../../../scripts/sync_projects.py) render_override; spec2test: input-processor/tests/test_sync_projects.py test_the_override_mounts_every_project_into_both_services |
| ESC-4-2-3 | Output folders are created on the host | The preprocessed and cache folders for every project are created if they do not exist | Completed | spec2test: [sync_projects.py#L152-L156](../../../scripts/sync_projects.py) create_output_folders; spec2test: input-processor/tests/test_sync_projects.py test_output_folders_are_created |
| ESC-4-2-4 | `--check` validates and previews without writing | Running with `--check` reports what would be written without creating folders or writing the override file | Completed | spec2test: [sync_projects.py#L226-L254](../../../scripts/sync_projects.py) main; spec2test: input-processor/tests/test_sync_projects.py test_check_validates_without_writing |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a base compose file missing one of the services that need project folders, when the override is generated, then only the services actually present are targeted.
- [x] Given valid, checked configuration, when the override is written, then every project is mounted into every targeted service.
- [x] Given projects whose output folders do not exist, when the override is generated (without `--check`), then those folders are created on the host.
- [x] Given `--check` is passed, when `sync_projects.py` runs, then nothing is written and the intended result is only reported.

### Technical Notes

The override never introduces a service the base compose file does not already define (RULE-13).

### Testing Notes

Covered by `input-processor/tests/test_sync_projects.py`, including `test_main_writes_the_override_and_the_folders`, `test_main_quiet_only_writes`, `test_the_committed_example_is_valid`, and `test_the_override_is_header_commentated`.

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-4-1 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-4-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| **Total** | **8** | 0 | 0 | 0 | 0 | 0 | **8** | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `scripts` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |
