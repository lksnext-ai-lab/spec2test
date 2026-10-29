# Domain Audit: web-crawler

**Date:** 2026-09-29
**Audit ID:** audit-web-crawler-2026-09-29

## Scope and Tools

| Alias | Modules | CBM state | Fallback | Limitations |
|---|---|---|---|---|
| spec2test | web-crawler/src, web-crawler/capture_auth.py | project `C-VSCode-WS-spec2Test`, generation `2026-09-29T10:49:01Z`, 1,349 nodes / 5,758 edges | none | No specialist agent is configured for this alias; local read-only inspection by `analyst-requirements`. No test files exist for this module within the analyzed scope. |

## Entry-Point Inventory

| Module | Entry point | Kind | Qualified symbol and file | Coverage |
|---|---|---|---|---|
| web-crawler | `web_crawl` | MCP tool | [main.py#L10-L38](../../../web-crawler/src/main.py) `C-VSCode-WS-spec2Test.web-crawler.src.main.web_crawl` | ok |
| web-crawler | `capture_auth.py` (CLI) | Standalone script (not exposed as an MCP tool) | [capture_auth.py#L339-L351](../../../web-crawler/capture_auth.py) `...capture_auth.main` | ok |

The MCP server runs as `uvicorn.run(mcp.streamable_http_app, host="0.0.0.0", port=8000)` ([main.py#L41-L42](../../../web-crawler/src/main.py)), exposed to the workspace as `web-crawler` in [.vscode/mcp.json](../../../.vscode/mcp.json).

## Q1. Behaviors Pinned by Tests

Not available. No test files were found under `web-crawler/` within the analyzed scope (`search_graph` with a `test` name pattern returned zero matching functions). This is a coverage limitation for functional confirmation, not evidence that the code is incorrect.

## Q2. Exposed Capabilities

| Capability | Source (specification operation or route, link) | Handler | Confidence |
|---|---|---|---|
| Crawl a web page or site, extracting links, interactive elements (buttons, inputs) with XPath selectors, and page content as Markdown, using BFS or DFS strategy up to a configurable depth and page limit | MCP tool `web_crawl`, docstring at [main.py#L11-L30](../../../web-crawler/src/main.py) | `web_crawler` ([web_crawler.py#L293-L545](../../../web-crawler/src/crawler/web_crawler.py)) | High |
| Optionally authenticate before crawling by replaying a previously recorded login action sequence | `web_crawl(use_auth=True)` (default), [main.py#L15-L23](../../../web-crawler/src/main.py) | `load_auth_actions_file` + stage replay in `web_crawler` | High |
| Interactively record a login's clicks, typing, and submissions in a real browser and save them as a replayable JSON action sequence | CLI `capture_auth.py <url> [--output FILE]`, module docstring at [capture_auth.py#L1-L16](../../../web-crawler/capture_auth.py) | `capture_auth_actions` ([capture_auth.py#L177-L336](../../../web-crawler/capture_auth.py)) | High |

## Q3. Entities, States, and Rules

| Entity or rule | Source (migration, entity, enum, constraint, link) | Values | Confidence |
|---|---|---|---|
| `LOCAL_HOSTS` | [web_crawler.py#L19](../../../web-crawler/src/crawler/web_crawler.py) | `localhost`, `127.0.0.1`, `0.0.0.0`, `host.docker.internal` | High |
| Recorded auth action | `capture_auth.py` `RECORDER_JS` / `capture_auth_actions` | Kinds: `fill`, `click`, `submit`; a `fill` records a masked value when the input type is `password` | High |
| Auth actions file schema | [capture_auth.py#L297-L308](../../../web-crawler/capture_auth.py) | `_meta` (captured_at, target_url, final_url, tool, description), `actions`, `navigations` | High |
| Replay stage | [web_crawler.py#L52-L85](../../../web-crawler/src/crawler/web_crawler.py) `split_actions_by_navigation` | A stage groups recorded actions between two recorded navigation timestamps, so a multi-page login flow replays across page transitions | High |

## Q4. Actors and Permissions

Not found within the analyzed scope. `web_crawl` and `capture_auth.py` are unauthenticated local tools; the "authentication" they implement is aimed at the *target* site being crawled (replaying a recorded login), not access control on the tool itself.

## Q5. User Vocabulary

| Term | Where it appears (i18n key, screen, message, link) | Candidate glossary entry |
|---|---|---|
| Auth actions | `capture_auth.py` output file and `CRAWLER_AUTH_ACTIONS_FILE` environment variable | A recorded, replayable sequence of browser interactions used to log in before crawling |
| Stage | `split_actions_by_navigation` ([web_crawler.py#L49-L85](../../../web-crawler/src/crawler/web_crawler.py)) | A group of recorded actions bounded by a page navigation, replayed in order |

## Q6. Intent

Not available. Only three commits touch `web-crawler` (`fbeebd6`, `c24cccd`, `5b9980f`); none of their messages explain a design rationale beyond "align configuration/documentation" and "initial commit". No `gh` issues were queried for this alias in this pass.

## Q7. Call Paths

| Entry point | Path to persistence or integrations | Tool | Confidence |
|---|---|---|---|
| `web_crawl` | `main.web_crawl` → `convert_localhost_url` → `web_crawler` → (if `use_auth`) `load_auth_actions_file` → `split_actions_by_navigation` → `build_replay_js` (in-page JS replay via `crawl4ai.AsyncWebCrawler`) → `BFSDeepCrawlStrategy`/`DFSDeepCrawlStrategy` (`crawl_pages`) → `extract_internal_links`/`get_xpath` → `DefaultMarkdownGenerator` | Direct source read (large function; `trace_path` not used due to size) | High |
| `capture_auth.py` | `main` → `capture_auth_actions` → Playwright browser (`chromium.launch`) → records DOM events via `RECORDER_JS` → writes the auth actions JSON file | Direct source read | High |

## Contradictions

Not applicable. No conflicting sources were found within the analyzed scope.

## Technical Evidence

| Alias | CBM project | Commit/generation | Tool/query | Symbol or path | Coverage | Confirmation | Limitations |
|---|---|---|---|---|---|---|---|
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `search_graph` (file_pattern=web-crawler/**) | 42 symbols across `main.py`, `web_crawler.py`, `capture_auth.py`, `pyproject.toml`, `Dockerfile` | complete | listing confirmed | none |
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `search_graph` (qn_pattern=`.*test.*`, file_pattern=web-crawler/**) | 0 matches | complete | listing confirmed | Confirms the absence of test functions within the analyzed scope, not the absence of manual testing |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | Direct file read | `web_crawler.py`, `capture_auth.py`, `main.py` | complete | local reading | none |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | `git log --oneline -n 20 -- web-crawler` | 3 commits touching `web-crawler` | complete for this path | local reading | No `gh` issue query performed for this alias in this pass |

## Requirement Gaps

Not applicable (code-first mode: no documented scenarios exist yet for this domain).
