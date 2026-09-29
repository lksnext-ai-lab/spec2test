# Domain Audit: filesystem-mcp

**Date:** 2026-09-29
**Audit ID:** audit-filesystem-mcp-2026-09-29

## Scope and Tools

| Alias | Modules | CBM state | Fallback | Limitations |
|---|---|---|---|---|
| spec2test | filesystem-mcp/index.ts | project `C-VSCode-WS-spec2Test`, generation `2026-09-29T10:49:01Z`, 1,349 nodes / 5,758 edges | none | No specialist agent is configured for this alias; local read-only inspection by `analyst-requirements`. No test files exist for this module within the analyzed scope. |

## Entry-Point Inventory

| Module | Entry point | Kind | Qualified symbol and file | Coverage |
|---|---|---|---|---|
| filesystem-mcp | `read_file` | MCP tool | [index.ts#L459-L467](../../../filesystem-mcp/index.ts) | ok |
| filesystem-mcp | `read_multiple_files` | MCP tool | [index.ts#L469-L487](../../../filesystem-mcp/index.ts) | ok |
| filesystem-mcp | `write_file` | MCP tool | [index.ts#L489-L498](../../../filesystem-mcp/index.ts) | ok |
| filesystem-mcp | `edit_file` | MCP tool | [index.ts#L500-L510](../../../filesystem-mcp/index.ts) | ok |
| filesystem-mcp | `create_directory` | MCP tool | [index.ts#L512-L521](../../../filesystem-mcp/index.ts) | ok |
| filesystem-mcp | `list_directory` | MCP tool | [index.ts#L523-L536](../../../filesystem-mcp/index.ts) | ok |
| filesystem-mcp | `directory_tree` | MCP tool | [index.ts#L538-L573](../../../filesystem-mcp/index.ts) `buildTree` | ok |
| filesystem-mcp | `move_file` | MCP tool | [index.ts#L575-L586](../../../filesystem-mcp/index.ts) | ok |
| filesystem-mcp | `search_files` | MCP tool | [index.ts#L588-L597](../../../filesystem-mcp/index.ts) `searchFiles` | ok |
| filesystem-mcp | `get_file_info` | MCP tool | [index.ts#L599-L610](../../../filesystem-mcp/index.ts) `getFileStats` | ok |
| filesystem-mcp | `list_allowed_directories` | MCP tool | [index.ts#L612-L618](../../../filesystem-mcp/index.ts) | ok |

The server runs as a plain Node HTTP server on `/mcp` ([index.ts#L706-L730](../../../filesystem-mcp/index.ts)), started with `mcp-server-filesystem <port> <allowed-directory> [additional-directories...]`, exposed as `filesystem-mcp` in the destination's own MCP configuration (referenced by [.github/agents/Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md)).

## Q1. Behaviors Pinned by Tests

Not available. No test files were found under `filesystem-mcp/` within the analyzed scope. This is a coverage limitation for functional confirmation, not evidence that the code is incorrect.

## Q2. Exposed Capabilities

| Capability | Source (specification operation or route, link) | Handler | Confidence |
|---|---|---|---|
| Read one file, or many files in one call (partial failures do not stop the batch) | Tool descriptions at [index.ts#L336-L353](../../../filesystem-mcp/index.ts) | `read_file`/`read_multiple_files` cases | High |
| Create or fully overwrite a file | Tool description at [index.ts#L355-L360](../../../filesystem-mcp/index.ts) | `write_file` case | High |
| Apply exact-text line edits to a file, returning a git-style diff, with a dry-run preview mode | Tool description at [index.ts#L362-L367](../../../filesystem-mcp/index.ts) | `applyFileEdits` ([index.ts#L254-L330](../../../filesystem-mcp/index.ts)) | High |
| Create a directory (including nested directories), succeeding silently if it already exists | Tool description at [index.ts#L369-L376](../../../filesystem-mcp/index.ts) | `create_directory` case | High |
| List a directory's immediate entries, marked `[FILE]`/`[DIR]` | Tool description at [index.ts#L378-L385](../../../filesystem-mcp/index.ts) | `list_directory` case | High |
| Return a recursive JSON tree of a directory | Tool description at [index.ts#L387-L394](../../../filesystem-mcp/index.ts) | `buildTree` ([index.ts#L544-L564](../../../filesystem-mcp/index.ts)) | High |
| Move or rename a file or directory | Tool description at [index.ts#L396-L403](../../../filesystem-mcp/index.ts) | `move_file` case | High |
| Recursively search for files/directories by a case-insensitive partial-name pattern, with excludable subpatterns | Tool description at [index.ts#L405-L412](../../../filesystem-mcp/index.ts) | `searchFiles` ([index.ts#L188-L232](../../../filesystem-mcp/index.ts)) | High |
| Retrieve file/directory metadata (size, timestamps, permissions, type) | Tool description at [index.ts#L414-L421](../../../filesystem-mcp/index.ts) | `getFileStats` ([index.ts#L175-L186](../../../filesystem-mcp/index.ts)) | High |
| List the directories the server is allowed to access | Tool description at [index.ts#L423-L429](../../../filesystem-mcp/index.ts) | `list_allowed_directories` case | High |

## Q3. Entities, States, and Rules

| Entity or rule | Source (migration, entity, enum, constraint, link) | Values | Confidence |
|---|---|---|---|
| `FileInfo` | [index.ts#L151-L159](../../../filesystem-mcp/index.ts) | size, created, modified, accessed, isDirectory, isFile, permissions | High |
| `TreeEntry` | [index.ts#L538-L542](../../../filesystem-mcp/index.ts) | name, type (`file`/`directory`), children (directories only) | High |
| Tool argument schemas | [index.ts#L97-L146](../../../filesystem-mcp/index.ts) | `ReadFileArgsSchema`, `ReadMultipleFilesArgsSchema`, `WriteFileArgsSchema`, `EditFileArgsSchema` (path, edits[], dryRun), `CreateDirectoryArgsSchema`, `ListDirectoryArgsSchema`, `DirectoryTreeArgsSchema`, `MoveFileArgsSchema`, `SearchFilesArgsSchema` (path, pattern, excludePatterns), `GetFileInfoArgsSchema` | High |
| Allowed directories | [index.ts#L20-L50](../../../filesystem-mcp/index.ts) | Resolved from CLI arguments at startup; every request is validated against this set | High |

## Q4. Actors and Permissions

| Actor | Capability | Source (guard, policy, role, link) | Confidence |
|---|---|---|---|
| Any MCP client of this server | Every file-system operation, but only within the configured allowed directories | `validatePath` ([index.ts#L53-L94](../../../filesystem-mcp/index.ts)): rejects paths outside `allowedDirectories`, resolves symlink targets and re-checks them, and checks the parent directory for paths that do not yet exist | High |

This is the only real access-control boundary confirmed across the audited modules so far (`input-processor` and `web-crawler` had none within their analyzed scope).

## Q5. User Vocabulary

| Term | Where it appears (i18n key, screen, message, link) | Candidate glossary entry |
|---|---|---|
| Allowed directories | `list_allowed_directories` tool, `validatePath` errors ([index.ts#L20-L94](../../../filesystem-mcp/index.ts)) | The set of directories this server is permitted to read, write, or list, configured at startup |

## Q6. Intent

Not available. The same four commits touch this repository as the other modules (`f4fcc48`, `fbeebd6`, `c24cccd`, `5b9980f`); none explain a design rationale specific to `filesystem-mcp`. No `gh` issues were queried for this alias in this pass.

## Q7. Call Paths

| Entry point | Path to persistence or integrations | Tool | Confidence |
|---|---|---|---|
| Every tool | `main` → `runServer` → HTTP `/mcp` endpoint → `CallToolRequestSchema` handler → `switch(name)` → `validatePath` → the corresponding `fs/promises` call (or `applyFileEdits`/`searchFiles`/`buildTree`/`getFileStats` helper) | Direct source read | High |

## Contradictions

| # | Sources in conflict (links) | Question for the owner |
|---|---|---|
| 1 | `move_file` tool description ("If the destination exists, the operation will fail", [index.ts#L396-L403](../../../filesystem-mcp/index.ts)) vs. its handler, which calls `fs.rename` directly with no existence check ([index.ts#L575-L586](../../../filesystem-mcp/index.ts)) | `fs.rename`'s overwrite behavior when the destination exists is platform-dependent and not guarded in code. Is the documented "fails if destination exists" the intended behavior (requiring an explicit check to be added), or should the description be corrected to match the current, platform-dependent behavior? (audit audit-filesystem-mcp-2026-09-29) |

## Technical Evidence

| Alias | CBM project | Commit/generation | Tool/query | Symbol or path | Coverage | Confirmation | Limitations |
|---|---|---|---|---|---|---|---|
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `search_graph` (file_pattern=filesystem-mcp/**, label=Function) | 12 functions in `index.ts` | complete | listing confirmed | none |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | Direct file read | `index.ts` (lines 1-160, 330-732) | complete for the read ranges | local reading | none |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | `git log --oneline -n 20 -- filesystem-mcp` | 4 commits touching `filesystem-mcp` | complete for this path | local reading | No `gh` issue query performed for this alias in this pass |

## Requirement Gaps

Not applicable (code-first mode: no documented scenarios exist yet for this domain).
