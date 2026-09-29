# CBM Status: spec2test

- Date: 2026-09-29
- Repository alias: `spec2test`
- Repository path: `C:\VSCode\WS\spec2Test`
- MCP server: `codebase-memory-mcp`, registered in the user MCP configuration at `%APPDATA%\Code\User\mcp.json`. `CBM_ALLOWED_ROOT` is `C:\VSCode\WS\spec2Test`; `CBM_CACHE_DIR` is `C:\Users\b.perez\.cache\codebase-memory-mcp\spec2test`.
- CBM project: `C-VSCode-WS-spec2Test`, returned by `list_projects` with root `C:/VSCode/WS/spec2Test` and branch `epics-spec2test`.
- Association status: the project name and root match the configured repository. Updating `repositories[].codebase_memory_project` and setting `repositories[].codebase_memory_project_status` to `confirmed` in `specification/.project.yml` still requires explicit authorization.
- Index generation: `2026-09-29T10:49:01Z`; mode `full`; commit was not returned by the available MCP output.
- Graph size: 1,349 nodes and 5,758 edges. Indexed languages were not returned by the available MCP output.
- Index status: `ready`; parse-unusable files: 0; skipped files: 0.

## Graph Schema

The schema reports 15 node labels and 18 edge types. Relevant labels include `Function` (476), `Method` (241), `Class` (83), `File` (98), and `Section` (79). Relevant edges include `CALLS` (1,470), `TESTS` (365), `WRITES` (236), `IMPORTS` (342), and `CONFIGURES` (3). No route- or endpoint-specific label/relationship, or persistence-specific label, was present in the returned schema.

## Coverage And Limitations

`check_index_coverage` was run over the top-level scopes `input-processor`, `web-crawler`, `filesystem-mcp`, `scripts`, and `specification`, and specifically over `.claude`, `.github`, `specification/.github`, and `specification/.claude`. A root-directory path was rejected by the MCP, so coverage is reported by project-relative scopes. The result is best-effort, not proof of completeness.

- The root `.github` scope had no recorded gaps. `specification/.github` was reported as an excluded subtree; `specification/.claude` had no recorded files or gaps.
- The root `.claude` scope is indexed except for `.claude/skills/gherkin-multiple-v5/assets/icon.svg`, which is marked `ignored-suffix`.
- The index recorded 30 not-indexed files. Examples returned by the MCP include `README.md`, `Spec2Test.png`, `filesystem-mcp/README.md`, and `input-processor/README.md`.
- Excluded directories reported by `index_status`: `.codebase-memory`, `.git`, `.vscode`, and `specification/.github`.
- Two files were indexed with partial parsing: `input-processor/Dockerfile` lines 7-21 and `web-crawler/Dockerfile` lines 12-45. Constructs in those ranges may be absent from the graph.
- Coverage metadata reports 72 ignored-file records, complete hash records, and `generation_matches: true`.

## Freshness

The coverage generation matches the indexed generation at `2026-09-29T10:49:01Z`; the hash-record set is complete. This is a best-effort freshness signal only; the earlier `spec2test` generation was superseded by this reindex.

## Readiness

The index is ready for structural queries. The project association update in `.project.yml` remains pending authorization. `specification/.github` is excluded as requested. `.claude`'s SVG and the two partially parsed Dockerfiles remain limitations and must not be treated as evidence that their behavior is absent.
