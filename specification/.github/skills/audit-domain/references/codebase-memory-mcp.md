# Codebase-memory-mcp Evidence Contract

This reference defines how to use CBM during a domain audit. CBM provides
structural code evidence; it does not determine business value or prove
functional compliance. CBM is one tool among others: without it only the
structural questions of the audit degrade.

## Responsibilities

| Part | Owner | Sections of this reference |
|---|---|---|
| Install, configure, prepare, index, freshness, coverage | `operator-codebase-memory` | Preconditions, Installation, Repository preparation, Query order steps 1–3 |
| Entry-point inventory and every audit question | `audit-domain` | Query order steps 4–7 and Mapping to the audit questions (evidence record, interpretation rules, and fallback live in `audit-domain/SKILL.md`) |
| Validation with the user | `analyst-requirements` | — |

The operator returns only the index state (project, generation, coverage) or
"CBM not available"; it never inventories or audits.

## Preconditions

1. Read `.project.yml` and `integrations.codebase_memory`.
2. Check `integrations.codebase_memory.enabled` **before any installation,
   client configuration, repository preparation, or indexing**. If it is
   `false`, do not install, configure, or index anything: use the configured
   `fallback` and record the limitation. Enabling CBM is a configuration
   change that requires the user's explicit decision.
3. Resolve each enabled `repositories` alias, its `local_path`, and
   `codebase_memory_project`. Apply the unresolved-value rule of
   `project-workflow.instructions.md`; a project name is usable
   only when `codebase_memory_project_status` is `confirmed`.
4. Do not analyze the requirements repository as an implementation repository
   unless it is explicitly declared as one.

If the MCP server is unavailable, use the configured fallback (see *Fallback*
in `audit-domain/SKILL.md`) and record the limitation.

## Installation outside the destination

Only when `integrations.codebase_memory.enabled` is `true`. Resolve the
active Python interpreter first. Check the package version with
that interpreter, install the version pinned by `.project.yml` only with explicit
consent when missing, then verify the version and entry point with the *same*
interpreter. A package-manager success message alone is not verification. For
the template's current `v0.11.0` pin, the package specifier omits the leading `v`:

```console
python -m pip install --upgrade "codebase-memory-mcp==0.11.0"
codebase-memory-mcp --version
```

In this example, `python` must resolve to the verified interpreter. If the
terminal resolves a different interpreter, invoke the verified executable
directly instead of relying on `PATH`.

Never copy packages, environments, credentials, logs, caches, or indexes
into the destination.

Package-manager installation does not configure agent clients. Register the
MCP server with the name `codebase-memory-mcp`: the agents' `tools:` reference
its tools as `codebase-memory-mcp/<tool>` (`operator-codebase-memory` the
index tools, `analyst-requirements` the read-only query tools, both limited to
`integrations.codebase_memory.allowed_tools`). Merge it into the existing MCP
client configuration: check the workspace (`.vscode/mcp.json`) and user MCP
configuration; if the server is missing, add it with that name; if it exists
under another name, report both names and, with explicit authorization,
rename the entry (never duplicate it, never touch other servers). Until the
name matches, report "CBM not available (MCP server not registered as
`codebase-memory-mcp`)". Validate the client configuration, restart VS Code
and the MCP client (or ask the user to) when needed, and afterwards confirm
with `list_projects` that the tool answers through that server name.
Preserve other configured MCP servers, set
`CBM_ALLOWED_ROOT` to the approved implementation root, and keep `CBM_CACHE_DIR`
outside every repository. Prefer typed MCP tools to one-shot CLI calls. When
MCP is unavailable, inspect the installed CLI help once and use documented
flags (`--repo-path` for indexing, `--project` for scoped queries, repeated
`--paths` for coverage); do not pass positional raw JSON through a shell or
require a platform-specific shell. The destination receives only declarative configuration
and this operational reference.

## Repository preparation

Only when CBM is enabled, and with separate authorization for repository
edits, merge these entries into the implementation repository's root
`.cbmignore` (keep existing entries). In the destination repository the
installed `.gitignore` already covers `.codebase-memory/` and
`.vscode/mcp.json`; when the implementation repository is a different one,
ensure `.codebase-memory/` is in its `.gitignore`:

```gitignore
# CI/CD and tooling
.github/
.gitlab-ci.yml
.vscode/
.idea/
# Generated or third-party code
**/generated/
**/gen/
**/vendor/
**/third_party/
**/*.min.js
**/*.pb.go
**/*_pb2.py
# Build outputs
**/target/
**/build/
**/dist/
**/bin/
**/obj/
# Static resources
**/*.svg
**/*.png
**/assets/
**/static/
# Repository documentation
docs/
*.md
```

Do not exclude tests, migrations, SQL scripts, or application/example
configuration (for example `application.yml`, `appsettings.json`,
`.properties`, or example `.env` files). Review existing ignore rules for
conflicts with this evidence before indexing. If `.cbmignore` changes after
an index, request authorization to reindex. Never treat ignored or poorly
parsed files as evidence of absence.

## Query order

1. For a new repository, obtain explicit index authorization and run
   `index_repository` with its resolved absolute root, then `list_projects` to
   match the exact project name and root to the alias. For an existing index,
   use `list_projects` first. Do not infer names or reuse an index from another
   repository. Recording the confirmed project in `.project.yml` requires
   explicit authorization for that update.
2. `index_status` to inspect state, generation, commit, and freshness.
   Report the actual node and edge counts, indexed languages, and coverage
   warnings returned by the MCP; if unavailable, say so rather than estimating.
3. `get_graph_schema` to confirm actual labels, relationships, and properties;
   then `get_architecture` as a map, not proof of complete behavior.
4. (`audit-domain`) After explicit audit authorization, inventory all entry points by module
   (routes, jobs, listeners, commands, screens). Label requirements tooling
   embedded in an implementation root separately from product behavior. Use
   `query_graph` with schema-verified labels and property names when exposed by
   the installed MCP; otherwise use supported structural search and state the
   inventory limitation. Page to the end of full inventories; stop and confirm
   modules before analysis.
5. (`audit-domain`) Use schema-supported `query_graph` inventories for route handlers, writes,
   outbound integrations, events, and test relationships when available. Use
   `search_graph` with qualified names, supported `name_pattern` regexes for
   validators, rules, policies, services, jobs, and listeners, and semantic
   search for domain concepts. Use `trace_path` outbound (depth 3-5 where
   supported) to persistence or integrations; trace shared rules inbound to
   all known triggers and record them once.
6. (`audit-domain`) Use `search_code` for constants, error text, configuration, roles, and
   embedded SQL missing from the graph; limit `get_code_snippet` to decision
   logic and only after locating the qualified symbol.
7. (`audit-domain`) For each entry point, record trigger, inputs, validations, decisions and
   calculations, state changes, reads/writes, integrations, permissions, errors,
   and supporting tests. Check tests and use `check_index_coverage` on all
   cited files in one batch.
   Report excluded or unparsed relevant files separately. A clean coverage
   report does not establish that the functional inventory is exhaustive.

### Mapping to the audit questions

| Audit question | What CBM contributes | What CBM does not cover |
|---|---|---|
| Q1 Tests | Test → code relationships when the schema exposes them | Reading the assertions: read the tests |
| Q2 Capabilities | Routes declared in code, when `get_graph_schema` shows route labels for the framework | Specification files (OpenAPI, GraphQL, proto) and contracts generated at runtime: read the files |
| Q3 Entities, states, rules | Classes, enums, and constants | Migrations and database constraints outside the graph: read them |
| Q4 Permissions | Guards, policies, and role checks as symbols | Permissions configured outside code |
| Q5 Vocabulary | — | i18n files and screen texts: local search |
| Q6 Intent | — | Commits, pull requests, and issues: `gh`, read-only |
| Q7 Call paths | `trace_path`, `query_graph` | Dynamic dispatch not in the graph: local search and LSP |

If coverage reports `metadata_changed`, read the affected source or compare
hashes before deciding whether the index is stale. Do not automatically
reindex: request separate authorization for each index operation. Compare
generation, status, and evidence afterward; if the generation is unchanged or
the warning persists, record freshness as unresolved. Do not interpret an
index result alone as complete functional coverage.

Use exploratory `limit`; paginate to completion for full inventories. Use
`max_output_tokens` for large calls and `source_max_lines` for decision
snippets only when the installed MCP exposes those parameters. Keep compact
output by default; request `detail`, `diagnostics`, or `source_mode` only when
needed. Reuse prior results instead of repeating queries. Stop after each module
for confirmation. Record uncalled code, flags, TODOs, similar implementations,
and contradictions separately from observed functional behavior.

Initial indexing or updates through `index_repository` require the authorization
specified in configuration. Do not use write, deletion, or trace-ingestion tools
during an audit.
