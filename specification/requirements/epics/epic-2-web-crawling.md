# EPIC-2: Automated Web Crawling and Login Capture

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Medium

## Overview

Crawls a target web application to extract structured page content — links,
interactive elements (buttons, inputs) with XPath selectors, and Markdown
content — for use in generating automated test scenarios, with an optional
authenticated crawl that replays a previously recorded login action sequence.
Exposed as the `web-crawler` MCP server (`web_crawl` tool) plus a standalone
CLI (`capture_auth.py`) that records a real login session for later replay.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-web-crawler-2026-09-29`; it is not new work. No automated
tests exist for this module within the analyzed scope, so scenario
confirmation relies on direct code reading rather than test evidence; this
limitation is recorded in the domain model's gaps section.

## Feature Index

- [FEAT-2-1: Crawl a web application and extract structured content](#feat-2-1-crawl-a-web-application-and-extract-structured-content)
- [FEAT-2-2: Authenticate before crawling using a recorded action sequence](#feat-2-2-authenticate-before-crawling-using-a-recorded-action-sequence)

## Dependencies

None known.

## References

- Code: spec2test: [web-crawler/src/main.py](../../../web-crawler/src/main.py)
- Audit: [audit-web-crawler-2026-09-29](../../tasks/audits/audit-web-crawler-2026-09-29.md)
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

## FEAT-2-1: Crawl a web application and extract structured content

**Source:** spec2test: [web-crawler/src/main.py#L10-L38](../../../web-crawler/src/main.py) web_crawl; spec2test: [web-crawler/src/crawler/web_crawler.py#L293-L545](../../../web-crawler/src/crawler/web_crawler.py) web_crawler

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Crawls a target URL breadth-first (default) or depth-first, up to a configurable depth and page limit, extracting links, interactive elements, and XPath selectors, and converting page content to Markdown; local host URLs are rewritten for Docker compatibility.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-2-1-1 | Crawl a site breadth-first up to a configured depth and page limit | By default, the crawl explores breadth-first up to `max_depth` levels and `max_pages` pages | Completed | spec2test: [main.py#L10-L23](../../../web-crawler/src/main.py) web_crawl; spec2test: [web_crawler.py#L239-L290](../../../web-crawler/src/crawler/web_crawler.py) crawl_pages |
| ESC-2-1-2 | Crawl a site depth-first when requested | When `use_dfs` is true, the crawl explores depth-first into the site hierarchy instead | Completed | spec2test: [main.py#L10-L23](../../../web-crawler/src/main.py) web_crawl; spec2test: [web_crawler.py#L239-L290](../../../web-crawler/src/crawler/web_crawler.py) crawl_pages |
| ESC-2-1-3 | Extract links, interactive elements, and Markdown content | The crawl result includes discovered links, buttons and inputs with XPath selectors, and the page content as Markdown | Completed | spec2test: [web_crawler.py#L220-L236](../../../web-crawler/src/crawler/web_crawler.py) extract_internal_links; spec2test: [web_crawler.py#L87-L120](../../../web-crawler/src/crawler/web_crawler.py) get_xpath |
| ESC-2-1-4 | Local host URLs are rewritten for Docker compatibility | A `localhost`, `127.0.0.1`, or `0.0.0.0` host in the crawl URL is rewritten to `host.docker.internal` when running inside a Docker container | Completed | spec2test: [web_crawler.py#L17-L39](../../../web-crawler/src/crawler/web_crawler.py) is_running_in_docker/canonicalize_url |

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

- [x] Given a target URL and default options, when `web_crawl` runs, then the site is explored breadth-first up to `max_depth` and `max_pages`.
- [x] Given `use_dfs` is set to true, when `web_crawl` runs, then the site is explored depth-first instead.
- [x] Given a crawled page, when the result is returned, then it includes links, interactive elements with XPath selectors, and Markdown content.
- [x] Given the crawler is running inside a Docker container, when a local host URL is used, then it is rewritten to `host.docker.internal`.

### Technical Notes

No automated tests exist for this feature within the analyzed scope; see `audit-web-crawler-2026-09-29` Q1.

### Testing Notes

Not available: no test files were found for this module (`audit-web-crawler-2026-09-29` Q1).

## FEAT-2-2: Authenticate before crawling using a recorded action sequence

**Source:** spec2test: [web-crawler/capture_auth.py](../../../web-crawler/capture_auth.py); spec2test: [web-crawler/src/crawler/web_crawler.py#L49-L85](../../../web-crawler/src/crawler/web_crawler.py) split_actions_by_navigation

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Lets an operator record a real login session (clicks, typing, submissions) as a replayable JSON action sequence, then replays it in stages bounded by page navigations before a crawl, so the crawl starts already authenticated.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-2-2-1 | Recorded auth actions are replayed in stages bounded by navigation | Recorded actions are grouped into stages by navigation timestamp so a multi-page login flow replays correctly across page transitions | Completed | spec2test: [web_crawler.py#L49-L85](../../../web-crawler/src/crawler/web_crawler.py) split_actions_by_navigation |
| ESC-2-2-2 | Crawling proceeds authenticated when auth replay succeeds | When every auth replay stage succeeds, the crawl proceeds using the authenticated session | Completed | spec2test: [web_crawler.py#L293-L412](../../../web-crawler/src/crawler/web_crawler.py) web_crawler |
| ESC-2-2-3 | Record a login's clicks, typing, and submissions into a replayable JSON file | Operator interactions in a real browser are captured and saved as a JSON file usable by `web_crawl` | Completed | spec2test: [capture_auth.py#L177-L336](../../../web-crawler/capture_auth.py) capture_auth_actions |
| ESC-2-2-4 | Passwords are masked in the recorded action log | A `fill` action on a password input is shown as `****` in the console log and summary instead of its real value | Completed | spec2test: [capture_auth.py#L177-L336](../../../web-crawler/capture_auth.py) capture_auth_actions |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a recorded auth actions file with navigations, when it is replayed, then actions are grouped into stages bounded by those navigations.
- [x] Given every auth replay stage succeeds, when the crawl continues, then it proceeds using the authenticated session.
- [x] Given an operator logs in inside the recorder browser, when the session ends, then the recorded actions are saved as a replayable JSON file.
- [x] Given a recorded `fill` action on a password field, when it is logged or summarized, then its value is shown as `****`.

### Technical Notes

The recorded value itself is still written unmasked to the output JSON file (only console output is masked); see `audit-web-crawler-2026-09-29` Q3. No automated tests exist for this feature within the analyzed scope.

### Testing Notes

Not available: no test files were found for this module (`audit-web-crawler-2026-09-29` Q1).

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-2-1 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-2-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| **Total** | **8** | 0 | 0 | 0 | 0 | 0 | **8** | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `web-crawler` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |
