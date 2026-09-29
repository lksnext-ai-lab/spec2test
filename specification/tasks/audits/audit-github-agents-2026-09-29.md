# Domain Audit: github-agents (Gherkin generation orchestration)

**Date:** 2026-09-29
**Audit ID:** audit-github-agents-2026-09-29

## Scope and Tools

| Alias | Modules | CBM state | Fallback | Limitations |
|---|---|---|---|---|
| spec2test | .github/agents/Gherkin-Generator.agent.md, .github/agents/Web-Crawler.agent.md, .github/skills/gherkin/SKILL.md | project `C-VSCode-WS-spec2Test` (Markdown content available only as `Section` nodes, not evaluated here) | local file read | These are Copilot agent/skill prompt instructions, not deterministic code. No specialist agent is configured for this alias; local read-only inspection by `analyst-requirements`. No tests exist, and none are possible for prompt-governed LLM behavior in the sense used elsewhere in this project. |

**Evidence-state note:** every finding in this audit is `Documented`, never `Implemented`. The reviewed files are instructions given to an LLM-based agent, not deterministic source code; reading them confirms what the agent is *instructed* to do, not what it verifiably *does* on every invocation. This differs from every other module audited for this project (`input-processor`, `web-crawler`, `filesystem-mcp`, `scripts`, `gherkin-multiple-v5`), where direct code reading was treated as `Implemented` evidence because the code is deterministic.

## Entry-Point Inventory

| Module | Entry point | Kind | Qualified symbol and file | Coverage |
|---|---|---|---|---|
| github-agents | `Gherkin-Generator` | Copilot agent (orchestrator) | [Gherkin-Generator.agent.md](../../../.github/agents/Gherkin-Generator.agent.md) | ok (Documented) |
| github-agents | `Web-Crawler` | Copilot agent (subagent) | [Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md) | ok (Documented) |
| github-agents | `gherkin` | Copilot skill (authoring guide, consulted by the orchestrator) | [SKILL.md](../../../.github/skills/gherkin/SKILL.md) | ok (Documented) |

`Gherkin-Generator` depends on the `input-processor` MCP tools already audited in `audit-input-processor-2026-09-29` (EPIC-1) and delegates crawling to `Web-Crawler`, which depends on the `web_crawl` MCP tool already audited in `audit-web-crawler-2026-09-29` (EPIC-2). This audit covers only the orchestration and authoring-rule layer that those two prior audits do not.

## Q1. Behaviors Pinned by Tests

Not applicable. Prompt-governed LLM behavior cannot be pinned by deterministic tests the way the other modules' code can be.

## Q2. Exposed Capabilities

| Capability | Source (specification operation or route, link) | Handler | Confidence |
|---|---|---|---|
| Gather the application URL and output directory from the user, process every available input file through `input-processor`, delegate crawling to `Web-Crawler`, read existing `.feature` files to avoid duplication, analyze edge cases, and generate `.feature` files grouped by `Rule:` with BRIEF-compliant scenarios | [Gherkin-Generator.agent.md, Steps 0-5](../../../.github/agents/Gherkin-Generator.agent.md) | Documented | High |
| Crawl a target application strictly through the `web_crawl` MCP tool, choosing BFS or DFS based on the feature's needs, and return a structured report of pages, forms, navigation, interactive elements, and XPath locators | [Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md) | Documented | High |
| Author quality Gherkin: business language, declarative steps, one business rule per scenario, Background limited to shared semantic context, Scenario Outline only for same-structure/different-data cases | [SKILL.md](../../../.github/skills/gherkin/SKILL.md) | Documented | High |

## Q3. Entities, States, and Rules

| Entity or rule | Source (migration, entity, enum, constraint, link) | Values | Confidence |
|---|---|---|---|
| BRIEF principles | [SKILL.md "Core Rules"/"Good Practices"](../../../.github/skills/gherkin/SKILL.md), [Gherkin-Generator.agent.md "Quality Principles: BRIEF"](../../../.github/agents/Gherkin-Generator.agent.md) | Business language, Real data, Intention revealing, Essential, Focused | Documented |
| `Rule:` grouping | [Gherkin-Generator.agent.md Step 5.2](../../../.github/agents/Gherkin-Generator.agent.md) | Replaces comment dividers; each `Rule:` groups scenarios for one business rule and may have its own scoped `Background:` | Documented |
| Background constraints | [Gherkin-Generator.agent.md Step 5.3](../../../.github/agents/Gherkin-Generator.agent.md), [SKILL.md "Core Rules" #5](../../../.github/skills/gherkin/SKILL.md) | Maximum 3-4 steps; semantic context only, never heavy data setup | Documented |
| Scenario vs. Scenario Outline decision | [Gherkin-Generator.agent.md Step 5.4 decision table](../../../.github/agents/Gherkin-Generator.agent.md) | Outline only when steps are identical and only data varies; separate scenarios when each row asserts a different business capability | Documented |
| MCP Evidence block | [Web-Crawler.agent.md "Required Evidence in Every Response"](../../../.github/agents/Web-Crawler.agent.md) | Tool, Calls made, Last call params, Last call status, Error (if failure); a missing block makes the response invalid | Documented |
| Forbidden crawl fallbacks | [Web-Crawler.agent.md "Forbidden Fallbacks"](../../../.github/agents/Web-Crawler.agent.md) | `wget`, `curl`, `fetch`, browser DevTools exports, handcrafted DOM assumptions, any non-MCP HTTP scraping, and simulated/guessed crawl output are all strictly forbidden | Documented |
| Crawl strategy decision | [Web-Crawler.agent.md "Crawl Strategy Decision"](../../../.github/agents/Web-Crawler.agent.md) | BFS for first/broad discovery; DFS for a specific deep workflow or after a prior BFS found entry points | Documented |
| Crawl safety rules | [Web-Crawler.agent.md "Safety Rules"](../../../.github/agents/Web-Crawler.agent.md) | Same-origin only; strip query/fragment when tracking visited URLs; respect `max_depth`/`max_pages` strictly | Documented |

## Q4. Actors and Permissions

| Actor | Capability | Source (guard, policy, role, link) | Confidence |
|---|---|---|---|
| `Gherkin-Generator` (orchestrator agent) | Reads/edits files, searches, invokes `input-processor` MCP tools and the `agent` tool (to call `Web-Crawler`) | Frontmatter `tools:` list, [Gherkin-Generator.agent.md](../../../.github/agents/Gherkin-Generator.agent.md) | Documented |
| `Web-Crawler` (subagent) | Only the `web_crawl` MCP tool and `todo` | Frontmatter `tools:` list, [Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md) | Documented |

This is a documented capability boundary between two agent roles (orchestrator vs. subagent), not a runtime-enforced authorization mechanism like `filesystem-mcp`'s `validatePath` (`audit-filesystem-mcp-2026-09-29` Q4): nothing in this repository prevents an agent platform from ignoring the frontmatter `tools:` restriction.

## Q5. User Vocabulary

| Term | Where it appears (i18n key, screen, message, link) | Candidate glossary entry |
|---|---|---|
| BRIEF | [SKILL.md](../../../.github/skills/gherkin/SKILL.md), [Gherkin-Generator.agent.md](../../../.github/agents/Gherkin-Generator.agent.md) | The five quality principles a generated Gherkin scenario must follow: Business language, Real data, Intention revealing, Essential, Focused |
| MCP Evidence block | [Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md) | The mandatory summary of `web_crawl` tool calls and outcomes that must open every `Web-Crawler` response |
| Proposed edge case | [SKILL.md "Bad Practices"/"Core Rules" #4](../../../.github/skills/gherkin/SKILL.md) | The comment marker used above an agent-proposed (rather than user-stated) edge-case scenario |

## Q6. Intent

| Capability | Reference (`alias#N` or commit, link) | Stated reason |
|---|---|---|
| The Gherkin-generation agent/skill instructions | Commit `f4fcc48` "Document the project workflow, the tools and the agent instructions" | States directly that this commit documents the agent instructions themselves |

Only two commits touch these paths (`f4fcc48`, `5b9980f`); no `gh` issues were queried for this alias in this pass.

## Q7. Call Paths

| Entry point | Path to persistence or integrations | Tool | Confidence |
|---|---|---|---|
| `Gherkin-Generator` | `Gherkin-Generator` → `input-processor` MCP tools (`current_project`, `process_files`, `list_processed_files`, `get_processed_content`; already audited in EPIC-1) → `agent` tool invoking `Web-Crawler` with the target URL and crawl intent → `Web-Crawler` → `web_crawl` MCP tool (already audited in EPIC-2) → `Gherkin-Generator` reads existing `.feature` files, analyzes edge cases, and writes new `.feature` files | Direct document read; no code trace possible | Documented |

## Contradictions

Not applicable as a functional contradiction, but worth recording as an observation: `Gherkin-Generator.agent.md`'s "Quality Principles: BRIEF" section and `.github/skills/gherkin/SKILL.md` state overlapping (not conflicting) Gherkin authoring rules in two separate documents. This is a maintenance risk (the two could drift apart over time), not a behavioral conflict.

## Technical Evidence

| Alias | CBM project | Commit/generation | Tool/query | Symbol or path | Coverage | Confirmation | Limitations |
|---|---|---|---|---|---|---|---|
| spec2test | n/a (local file read) | working tree at 2026-09-29 | Direct file read | `Gherkin-Generator.agent.md`, `Web-Crawler.agent.md`, `.github/skills/gherkin/SKILL.md` (full) | complete | local reading | Evidence state is `Documented`, not `Implemented`, throughout this audit (see Scope and Tools note) |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | `git log --oneline -n 20 -- .github/agents .github/skills/gherkin` | 2 commits touching these paths | complete for this path | local reading | No `gh` issue query performed for this alias in this pass |

## Requirement Gaps

Not applicable (code-first/document-first mode: no documented scenarios existed for this domain before this audit).
