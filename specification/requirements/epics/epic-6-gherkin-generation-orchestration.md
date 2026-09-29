# EPIC-6: Gherkin Generation Orchestration

**Status:** Approved

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Medium

## Overview

Orchestrates input processing (EPIC-1) and web crawling (EPIC-2) into
generated `.feature` files: an orchestrator agent (`Gherkin-Generator`)
processes every available input file, delegates crawling to a restricted
subagent (`Web-Crawler`), reads existing `.feature` files to avoid
duplication, analyzes edge cases, and authors scenarios following BRIEF
quality principles, `Rule:`-based grouping, and Scenario/Scenario Outline
guidance shared with the `gherkin` skill.

**This epic's evidence is `Documented`, not `Implemented`, and its status is
therefore `Approved` rather than `Completed`.** Every other epic in this
project (`EPIC-1` through `EPIC-5`) was marked `Completed` because direct
reading of deterministic source code (Python/TypeScript) confirms what
actually executes. This epic instead documents instructions given to an
LLM-based Copilot agent: reading `Gherkin-Generator.agent.md` and
`Web-Crawler.agent.md` confirms what the agent is *instructed* to do, not
that it verifiably does so on every invocation. No tests exist, and none are
possible in the sense used for the other epics. This distinction is recorded
in the domain model's gaps section and must not be lost when this epic is
referenced elsewhere.

## Feature Index

- [FEAT-6-1: Orchestrate input processing and crawling into Gherkin scenarios](#feat-6-1-orchestrate-input-processing-and-crawling-into-gherkin-scenarios)
- [FEAT-6-2: Constrain crawling to verified, evidenced tool calls](#feat-6-2-constrain-crawling-to-verified-evidenced-tool-calls)

## Dependencies

- EPIC-1: `Gherkin-Generator` depends on the `input-processor` MCP tools (`current_project`, `process_files`, `list_processed_files`, `get_processed_content`).
- EPIC-2: `Web-Crawler` depends on the `web_crawl` MCP tool.

## References

- Document: spec2test: [.github/agents/Gherkin-Generator.agent.md](../../../.github/agents/Gherkin-Generator.agent.md)
- Document: spec2test: [.github/agents/Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md)
- Document: spec2test: [.github/skills/gherkin/SKILL.md](../../../.github/skills/gherkin/SKILL.md)
- Audit: [audit-github-agents-2026-09-29](../../tasks/audits/audit-github-agents-2026-09-29.md)
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
infer an E2E result. For this epic specifically, no source can establish
`Completed` at all, because the sources are prompt instructions rather than
deterministic code or passing tests.

---

## FEAT-6-1: Orchestrate input processing and crawling into Gherkin scenarios

**Source:** Document: spec2test: [Gherkin-Generator.agent.md, Steps 0-5](../../../.github/agents/Gherkin-Generator.agent.md)

**Priority:** Medium

**Status:** Approved

**Owner:** @bperez

**Description:** Gathers the application URL and output directory, processes every available input file through `input-processor`, delegates crawling to `Web-Crawler`, reads existing `.feature` files to avoid duplication, analyzes edge cases, and generates `.feature` files grouped by `Rule:` with BRIEF-compliant scenarios, choosing `Scenario` vs. `Scenario Outline` per the documented decision table.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-6-1-1 | Process every available input file before generating scenarios | Every file returned by `list_processed_files` is fully analyzed, extracting user stories, workflows, business rules, and UI components, before feature generation begins | Approved | Document: spec2test: [Gherkin-Generator.agent.md Step 1](../../../.github/agents/Gherkin-Generator.agent.md) |
| ESC-6-1-2 | Avoid duplicating existing `.feature` files | Existing `.feature` files are read first, and only genuinely new scenarios are added instead of duplicating existing ones | Approved | Document: spec2test: [Gherkin-Generator.agent.md Step 3](../../../.github/agents/Gherkin-Generator.agent.md) |
| ESC-6-1-3 | Group generated scenarios by business rule using `Rule:` | Scenarios sharing a business rule are grouped under a Gherkin `Rule:` keyword rather than a comment divider | Approved | Document: spec2test: [Gherkin-Generator.agent.md Step 5.2](../../../.github/agents/Gherkin-Generator.agent.md); Document: spec2test: [SKILL.md](../../../.github/skills/gherkin/SKILL.md) |
| ESC-6-1-4 | Choose Scenario Outline only for same-structure, different-data cases | A Scenario Outline is used only when every row shares the same step structure and differs only in data; otherwise separate scenarios are used | Approved | Document: spec2test: [Gherkin-Generator.agent.md Step 5.4 decision table](../../../.github/agents/Gherkin-Generator.agent.md) |

### Comments

| Scenario ID | Comments |
|--------------|-------------|
| ESC-6-1-3 | Observation from `audit-github-agents-2026-09-29`: this authoring rule is stated in both `Gherkin-Generator.agent.md` and `.github/skills/gherkin/SKILL.md`, which is a maintenance risk (possible future drift) rather than a functional conflict. |

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [ ] Given input files are available, when generation starts, then every file is processed and analyzed before scenarios are written.
- [ ] Given `.feature` files already exist in the output directory, when generation runs, then only new, non-duplicate scenarios are added.
- [ ] Given scenarios share a business rule, when the feature file is written, then they are grouped under a `Rule:` keyword.
- [ ] Given a set of data variations shares the same step structure, when scenarios are authored, then a `Scenario Outline` is used instead of separate scenarios.

### Technical Notes

This feature's behavior is `Documented` (Copilot agent instructions), not `Implemented` code; see the epic overview and `audit-github-agents-2026-09-29`.

### Testing Notes

Not applicable: prompt-governed LLM behavior cannot be pinned by deterministic tests (`audit-github-agents-2026-09-29` Q1).

## FEAT-6-2: Constrain crawling to verified, evidenced tool calls

**Source:** Document: spec2test: [Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md)

**Priority:** Medium

**Status:** Approved

**Owner:** @bperez

**Description:** Restricts the crawling subagent to the `web_crawl` MCP tool, forbidding any non-MCP scraping fallback or simulated crawl data, and requires a structured evidence block reporting every `web_crawl` call and its outcome in every response.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-6-2-1 | Crawling is never simulated or guessed | A crawl result is never returned as guessed, inferred, or template-only data; at least one successful `web_crawl` call must be present | Approved | Document: spec2test: [Web-Crawler.agent.md "Mandatory MCP Usage"](../../../.github/agents/Web-Crawler.agent.md) |
| ESC-6-2-2 | Non-MCP scraping fallbacks are forbidden | `wget`, `curl`, `fetch`, browser DevTools exports, and handcrafted DOM assumptions are never used as a substitute for `web_crawl` | Approved | Document: spec2test: [Web-Crawler.agent.md "Forbidden Fallbacks"](../../../.github/agents/Web-Crawler.agent.md) |
| ESC-6-2-3 | Every response includes an MCP evidence block | Every `Web-Crawler` response opens with a block reporting the tool, calls made, last call parameters, last call status, and the error text if it failed | Approved | Document: spec2test: [Web-Crawler.agent.md "Required Evidence in Every Response"](../../../.github/agents/Web-Crawler.agent.md) |
| ESC-6-2-4 | Crawl strategy is chosen by documented BFS/DFS criteria | Breadth-first search is used for first/broad discovery; depth-first search is used for a specific deep workflow or after a prior broad crawl | Approved | Document: spec2test: [Web-Crawler.agent.md "Crawl Strategy Decision"](../../../.github/agents/Web-Crawler.agent.md) |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [ ] Given `web_crawl` fails, when a response is returned, then it reports failure only, with no partial or guessed crawl data.
- [ ] Given a crawl is requested, when it is performed, then no non-MCP scraping tool is used as a substitute for `web_crawl`.
- [ ] Given any `Web-Crawler` response, when it is returned, then it opens with a complete MCP evidence block.
- [ ] Given the feature's crawling need, when a strategy is chosen, then it follows the documented BFS/DFS decision criteria.

### Technical Notes

This feature's behavior is `Documented` (Copilot agent instructions), not `Implemented` code; see the epic overview and `audit-github-agents-2026-09-29`. Compare with `filesystem-mcp`'s `validatePath` (EPIC-3), which is a runtime-enforced boundary, not a documented one.

### Testing Notes

Not applicable: prompt-governed LLM behavior cannot be pinned by deterministic tests (`audit-github-agents-2026-09-29` Q1).

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-6-1 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| FEAT-6-2 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **8** | 0 | 0 | **8** | 0 | 0 | 0 | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `github-agents` audit. Documented agent/skill behavior reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests, so marked `Approved` rather than `Completed` | analyst-requirements (Claude Sonnet 5) |
