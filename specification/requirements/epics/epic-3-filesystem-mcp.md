# EPIC-3: Scoped Filesystem Access via MCP

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Medium

## Overview

Exposes read, write, search, and metadata operations over a filesystem as MCP
tools, with every operation confined to a set of allowed directories
configured at server startup. This is the only audited module with a real
access-control boundary: paths outside the allowed directories, including
resolved symlink targets, are rejected.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-filesystem-mcp-2026-09-29`; it is not new work. No automated
tests exist for this module within the analyzed scope, so scenario
confirmation relies on direct code reading rather than test evidence; this
limitation is recorded in the domain model's gaps section.

## Feature Index

- [FEAT-3-1: Confine every operation to allowed directories](#feat-3-1-confine-every-operation-to-allowed-directories)
- [FEAT-3-2: Read, write, and edit files](#feat-3-2-read-write-and-edit-files)
- [FEAT-3-3: Browse, search, and inspect the filesystem](#feat-3-3-browse-search-and-inspect-the-filesystem)

## Dependencies

None known.

## References

- Code: spec2test: [filesystem-mcp/index.ts](../../../filesystem-mcp/index.ts)
- Audit: [audit-filesystem-mcp-2026-09-29](../../tasks/audits/audit-filesystem-mcp-2026-09-29.md)
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

## FEAT-3-1: Confine every operation to allowed directories

**Source:** spec2test: [filesystem-mcp/index.ts#L53-L94](../../../filesystem-mcp/index.ts) validatePath

**Priority:** High

**Status:** Completed

**Owner:** @bperez

**Description:** Rejects any requested path that resolves outside the directories configured at server startup, including resolved symlink targets, and checks the parent directory for paths that do not yet exist (for example, a new file to be created).

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-3-1-1 | A path outside the allowed directories is rejected | Any tool call with a resolved path outside the configured allowed directories fails with an access-denied error | Completed | spec2test: [index.ts#L53-L66](../../../filesystem-mcp/index.ts) validatePath |
| ESC-3-1-2 | A symlink pointing outside the allowed directories is rejected | When a path resolves to a symlink, its real target is also checked against the allowed directories | Completed | spec2test: [index.ts#L68-L77](../../../filesystem-mcp/index.ts) validatePath |
| ESC-3-1-3 | The allowed directories can be listed | A client can retrieve the list of directories this server instance is permitted to access | Completed | spec2test: [index.ts#L423-L429](../../../filesystem-mcp/index.ts) list_allowed_directories |

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

- [x] Given a path outside every allowed directory, when any tool is called with it, then the call fails with an access-denied error.
- [x] Given a path that resolves to a symlink whose target is outside the allowed directories, when it is used, then the call fails.
- [x] Given a client calls `list_allowed_directories`, when the call completes, then the configured allowed directories are returned.

### Technical Notes

No automated tests exist for this feature within the analyzed scope; see `audit-filesystem-mcp-2026-09-29` Q1.

### Testing Notes

Not available: no test files were found for this module (`audit-filesystem-mcp-2026-09-29` Q1).

## FEAT-3-2: Read, write, and edit files

**Source:** spec2test: [filesystem-mcp/index.ts#L254-L330](../../../filesystem-mcp/index.ts) applyFileEdits

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Reads one or many files, creates or overwrites a file, and applies exact-text line edits to a file with an optional dry-run preview returned as a git-style diff.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-3-2-1 | Read a single file's complete contents | A file's contents are returned given its path | Completed | spec2test: [index.ts#L459-L467](../../../filesystem-mcp/index.ts) read_file |
| ESC-3-2-2 | Read multiple files in one call without one failure stopping the batch | Every requested file is read; a failed individual read is reported without aborting the others | Completed | spec2test: [index.ts#L469-L487](../../../filesystem-mcp/index.ts) read_multiple_files |
| ESC-3-2-3 | Create or overwrite a file | A file is created, or fully overwritten if it already exists | Completed | spec2test: [index.ts#L489-L498](../../../filesystem-mcp/index.ts) write_file |
| ESC-3-2-4 | Preview an edit as a diff without writing it | When `dryRun` is set, the edit is not applied and a git-style diff of the would-be change is returned instead | Completed | spec2test: [index.ts#L254-L330](../../../filesystem-mcp/index.ts) applyFileEdits |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a valid path, when `read_file` is called, then the file's complete contents are returned.
- [x] Given several paths where one is unreadable, when `read_multiple_files` is called, then the readable files are still returned and the failure is reported per path.
- [x] Given `write_file` is called on an existing file, when it completes, then the file is fully overwritten with the new content.
- [x] Given `edit_file` is called with `dryRun` true, when it completes, then no write occurs and a diff of the intended change is returned.

### Technical Notes

No automated tests exist for this feature within the analyzed scope; see `audit-filesystem-mcp-2026-09-29` Q1.

### Testing Notes

Not available: no test files were found for this module (`audit-filesystem-mcp-2026-09-29` Q1).

## FEAT-3-3: Browse, search, and inspect the filesystem

**Source:** spec2test: [filesystem-mcp/index.ts#L544-L564](../../../filesystem-mcp/index.ts) buildTree; spec2test: [filesystem-mcp/index.ts#L188-L232](../../../filesystem-mcp/index.ts) searchFiles

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Lists a directory's entries, returns a recursive JSON tree, searches recursively for files or directories by a case-insensitive partial-name pattern, retrieves file/directory metadata, moves or renames files and directories, and creates directories (including nested ones).

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-3-3-1 | List a directory's immediate entries | Entries are returned marked `[FILE]` or `[DIR]` | Completed | spec2test: [index.ts#L523-L536](../../../filesystem-mcp/index.ts) list_directory |
| ESC-3-3-2 | Return a recursive directory tree | A JSON tree of the directory is returned, with `children` present only for directories | Completed | spec2test: [index.ts#L544-L564](../../../filesystem-mcp/index.ts) buildTree |
| ESC-3-3-3 | Recursively search for files or directories by name | Items whose name partially matches a case-insensitive pattern are found under the given path, excluding any configured subpatterns | Completed | spec2test: [index.ts#L188-L232](../../../filesystem-mcp/index.ts) searchFiles |
| ESC-3-3-4 | Retrieve file or directory metadata | Size, timestamps, type, and permissions are returned for a given path | Completed | spec2test: [index.ts#L175-L186](../../../filesystem-mcp/index.ts) getFileStats |
| ESC-3-3-5 | Move or rename a file or directory | A file or directory is moved to a new path, or renamed within the same directory | Completed | spec2test: [index.ts#L575-L586](../../../filesystem-mcp/index.ts) move_file |
| ESC-3-3-6 | Create a directory, including nested ones | A directory (and any missing parent directories) is created; it succeeds silently if the directory already exists | Completed | spec2test: [index.ts#L512-L521](../../../filesystem-mcp/index.ts) create_directory |

### Comments

| Scenario ID | Comments |
|--------------|-------------|
| ESC-3-3-5 | Open question: the `move_file` tool description states the operation fails if the destination exists ([index.ts#L396-L403](../../../filesystem-mcp/index.ts)), but the handler calls `fs.rename` with no existence check ([index.ts#L575-L586](../../../filesystem-mcp/index.ts)), so actual overwrite behavior is platform-dependent. Is the documented failure-on-overwrite the intended behavior (requiring an explicit check), or should the description be corrected? (audit audit-filesystem-mcp-2026-09-29) |

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a directory path, when `list_directory` is called, then its immediate entries are returned marked `[FILE]` or `[DIR]`.
- [x] Given a directory path, when `directory_tree` is called, then a recursive JSON tree is returned with `children` only on directories.
- [x] Given a search pattern and a starting path, when `search_files` is called, then matching items are found recursively, excluding any configured subpatterns.
- [x] Given a path, when `get_file_info` is called, then its size, timestamps, type, and permissions are returned.
- [x] Given a source and destination path, when `move_file` is called, then the item is moved or renamed accordingly.
- [x] Given a path with missing parent directories, when `create_directory` is called, then the full path is created.

### Technical Notes

See the open question in the Comments table above regarding `move_file` overwrite behavior. No automated tests exist for this feature within the analyzed scope.

### Testing Notes

Not available: no test files were found for this module (`audit-filesystem-mcp-2026-09-29` Q1).

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-3-1 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| FEAT-3-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-3-3 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| **Total** | **13** | 0 | 0 | 0 | 0 | 0 | **13** | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `filesystem-mcp` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |
