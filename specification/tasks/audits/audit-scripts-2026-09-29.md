# Domain Audit: scripts (sync_projects)

**Date:** 2026-09-29
**Audit ID:** audit-scripts-2026-09-29

## Scope and Tools

| Alias | Modules | CBM state | Fallback | Limitations |
|---|---|---|---|---|
| spec2test | scripts/sync_projects.py | project `C-VSCode-WS-spec2Test`, generation `2026-09-29T10:49:01Z`, 1,349 nodes / 5,758 edges | none | No specialist agent is configured for this alias; local read-only inspection by `analyst-requirements`. Its tests live under `input-processor/tests/test_sync_projects.py`, not next to the script itself — a placement noted as a limitation, not a functional gap. |

## Entry-Point Inventory

| Module | Entry point | Kind | Qualified symbol and file | Coverage |
|---|---|---|---|---|
| scripts | `sync_projects.py` | Host-side CLI command | [sync_projects.py#L226-L254](../../../scripts/sync_projects.py) `C-VSCode-WS-spec2Test.scripts.sync_projects.main` | ok |

Run as `python scripts/sync_projects.py [--config PATH] [--output PATH] [--compose PATH] [--check] [--quiet]` on the host, not inside a container ([sync_projects.py#L1-L18](../../../scripts/sync_projects.py)).

## Q1. Behaviors Pinned by Tests

| Behavior | Test (file, case, link) | Code (symbol, link) | Confidence |
|---|---|---|---|
| Project paths (inputs, preprocessed, cache) are read from the configuration file, with preprocessed/cache defaulting to a hidden data directory when not set | `input-processor/tests/test_sync_projects.py`: `test_paths_are_read_from_the_configuration_file`, `test_output_folders_default_to_a_hidden_data_directory` | `load_config`, `_project`, `_resolve` ([sync_projects.py#L71-L126](../../../scripts/sync_projects.py)) | High |
| A missing or invalid configuration file, a non-object entry, or an empty projects list is reported as a configuration error | `test_sync_projects.py`: `test_a_missing_configuration_file_is_reported`, `test_an_invalid_configuration_file_is_reported`, `test_the_configuration_must_be_an_object`, `test_each_entry_must_be_an_object`, `test_the_projects_list_must_not_be_empty` | `load_config`, `_project` ([sync_projects.py#L71-L118](../../../scripts/sync_projects.py)) | High |
| An invalid or duplicate project name is refused | `test_sync_projects.py`: `test_invalid_names_are_refused`, `test_duplicate_names_are_refused`, `test_the_name_rule_matches_the_container` | `_project`, `_reject_duplicates`, `SLUG_RE` ([sync_projects.py#L41](../../../scripts/sync_projects.py), [#L101-L134](../../../scripts/sync_projects.py)) | High |
| Missing input folders for every affected project are reported together in one error | `test_sync_projects.py`: `test_missing_inputs_are_reported_together` | `check_paths` ([sync_projects.py#L137-L149](../../../scripts/sync_projects.py)) | High |
| Preprocessed and cache output folders are created on the host if missing | `test_sync_projects.py`: `test_output_folders_are_created` | `create_output_folders` ([sync_projects.py#L152-L156](../../../scripts/sync_projects.py)) | High |
| The compose override only lists services declared in the base compose file, among the ones that need project folders; a base file without either service is reported as an error | `test_sync_projects.py`: `test_services_are_read_from_the_base_compose_file`, `test_a_compose_file_without_our_services_is_reported` | `configured_services` ([sync_projects.py#L159-L185](../../../scripts/sync_projects.py)) | High |
| The generated override mounts every project into both services and is header-commented as generated | `test_sync_projects.py`: `test_the_override_mounts_every_project_into_both_services`, `test_the_override_is_header_commentated` | `render_override` ([sync_projects.py#L188-L205](../../../scripts/sync_projects.py)) | High |
| `--check` validates and reports without writing anything; the normal run writes the override and creates folders; `--quiet` only writes without reporting | `test_sync_projects.py`: `test_check_validates_without_writing`, `test_main_writes_the_override_and_the_folders`, `test_main_quiet_only_writes`, `test_main_reports_missing_inputs_without_writing_anything` | `main` ([sync_projects.py#L226-L254](../../../scripts/sync_projects.py)) | High |
| The committed example configuration file is itself valid | `test_sync_projects.py`: `test_the_committed_example_is_valid` | `load_config` against `projects.example.json` | High |

## Q2. Exposed Capabilities

| Capability | Source (specification operation or route, link) | Handler | Confidence |
|---|---|---|---|
| Validate `projects.json`, create the host-side output folders it references, and write `docker-compose.override.yaml` mounting every project into the services that need it | Module docstring at [sync_projects.py#L1-L18](../../../scripts/sync_projects.py) | `main` | High |
| Validate configuration and preview what would be written, without writing | `--check` flag, [sync_projects.py#L216-L219](../../../scripts/sync_projects.py) | `main` (early return branch) | High |

## Q3. Entities, States, and Rules

| Entity or rule | Source (migration, entity, enum, constraint, link) | Values | Confidence |
|---|---|---|---|
| `Project` | [sync_projects.py#L54-L68](../../../scripts/sync_projects.py) | name, inputs, preprocessed, cache (resolved absolute host paths) | High |
| Project name pattern (`SLUG_RE`) | [sync_projects.py#L41](../../../scripts/sync_projects.py) | Lowercase letters, digits, dots, dashes, or underscores, starting with a letter or digit | High |
| `SERVICES` | [sync_projects.py#L42](../../../scripts/sync_projects.py) | `input-processor`, `filesystem-mcp` | High |
| `ConfigError` | [sync_projects.py#L49-L50](../../../scripts/sync_projects.py) | Raised when `projects.json` is missing, malformed, or inconsistent | High |

## Q4. Actors and Permissions

Not applicable. This is a host-side, offline configuration-generation script with no runtime request or authenticated actor.

## Q5. User Vocabulary

| Term | Where it appears (i18n key, screen, message, link) | Candidate glossary entry |
|---|---|---|
| Compose override | `docker-compose.override.yaml`, `OVERRIDE_HEADER` ([sync_projects.py#L36](../../../scripts/sync_projects.py)) | The generated Docker Compose file that mounts every configured project into the services that need it |

## Q6. Intent

| Capability | Reference (`alias#N` or commit, link) | Stated reason |
|---|---|---|
| Generating the compose override from `projects.json` | Module docstring, [sync_projects.py#L1-L18](../../../scripts/sync_projects.py) | States directly that the container only ever sees `/projects/<name>/{inputs,preprocessed,cache}`, so host paths in `projects.json` must be turned into volume mounts; also states that `input-processor/src/projects/model.py` is this script's container-side counterpart and the two must agree on the project name rule and layout |

This rationale comes from the module's own docstring, not from commit history or issues; the same four generic commits touch this repository as the other modules, with no `sync_projects`-specific message. No `gh` issues were queried for this alias in this pass.

## Q7. Call Paths

| Entry point | Path to persistence or integrations | Tool | Confidence |
|---|---|---|---|
| `main` | `main` → `load_config`/`_project`/`_reject_duplicates` (reads `projects.json`) → `check_paths` (reads the host filesystem) → `configured_services` (reads `docker-compose.yaml`) → `render_override` → (unless `--check`) `create_output_folders` + `write_override` (writes `docker-compose.override.yaml` and creates host directories) | Direct source read | High |

## Contradictions

Not applicable. No conflicting sources were found within the analyzed scope.

## Technical Evidence

| Alias | CBM project | Commit/generation | Tool/query | Symbol or path | Coverage | Confirmation | Limitations |
|---|---|---|---|---|---|---|---|
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `get_code_snippet` (outline) | `scripts.sync_projects` (29 members) | complete | snippet read | none |
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `search_graph` (file_pattern=`**/test_sync_projects.py`, qn_pattern=`.*test_.*`) | 22 test functions in `input-processor/tests/test_sync_projects.py` | complete | listing confirmed | none |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | Direct file read | `scripts/sync_projects.py` (full, 269 lines) | complete | local reading | none |

## Requirement Gaps

Not applicable (code-first mode: no documented scenarios exist yet for this domain).
