# Gherkin generator for VS Code Copilot

Two custom agents: `gherkin-generator` writes and maintains `.feature` files, and delegates exploration of the running application to `web-crawler`. Practices, examples, and review criteria are inside `gherkin-generator.agent.md`; nothing is loaded from an external file, so there is nothing that can silently fail to load.

## 1. Place the agent files

Copy both files into your workspace:

```
.github/agents/gherkin-generator.agent.md
.github/agents/web-crawler.agent.md
```

VS Code detects any `.md` file in `.github/agents/` as a custom agent automatically; no further registration step is needed. Open **Chat: Open Customizations** (Command Palette) → **Agents** tab, and both should be listed. If not, right-click in the Chat view and select **Diagnostics** to see load errors.

## 2. Set up the MCP servers

The generator needs two MCP servers, `input-processor` and `web-crawler`, and the crawler needs a third, `playwright`, as a fallback for pages the static crawler cannot reach (single-page applications, content behind interaction).

Add them in your workspace's `.vscode/mcp.json` (or through **MCP: Add Server** in the Command Palette):

```json
{
  "servers": {
    "input-processor": {
      "type": "http",
      "url": "http://localhost:REPLACE_PORT/mcp"
    },
    "web-crawler": {
      "type": "http",
      "url": "http://localhost:REPLACE_PORT/mcp"
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

Replace the `input-processor` and `web-crawler` URLs with your own MCP server endpoints. The `playwright` entry runs the official Playwright MCP server locally via `npx`; no separate installation is needed as long as Node.js is on the path.

**Do not rewrite `localhost` to `host.docker.internal` yourself and do not tell the agent to.** The `web_crawl` tool on the `web-crawler` MCP server is expected to do that translation on its side. Give the agents the application's normal URL (for example, `http://localhost:8080`).

Reload the window or run **MCP: List Servers** to confirm all three show as running.

## 3. Enable the Gherkin linter

The generator checks its own output against your editor's Gherkin diagnostics before finishing (agent Step 7). Install a `.feature` file linter extension, for example the **Cucumber (Gherkin) Full Support** extension, so that VS Code's Problems view reports Gherkin syntax errors.

If you use a different linter or extension, only one line needs to change: Step 7, item 1, of `gherkin-generator.agent.md`. The changelog entry "Linter: where to look if it changes" tells you exactly what to edit.

## 4. Run it

Open the Chat view, select **gherkin-generator** from the agent dropdown, and describe the task, for example:

> Generate the Gherkin features for the checkout flow. Documentation is already in the input processor. The app runs at http://localhost:3000.

The agent will ask setup questions it cannot infer (where to save files, how to organize them, the language), then work through analysis, exploration, planning, and writing, stopping at each checkpoint described in the prompt (`<human_in_the_loop>`) for your approval. You can tell it to skip checkpoints except the last one, which always asks before deleting or rewriting existing content.

## 5. Where things land

- `.feature` files, in the directory you choose.
- `traceability.md`, next to the feature files: one row per scenario and per Examples row, with provenance (documented, observed, or proposed) and the exact source.
- A summary in the chat at the end of each run, listing files changed, proposed cases, the linter result, and any open questions for QA review.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `gherkin-generator` or `web-crawler` missing from the agent dropdown | File not in `.github/agents/`, or a frontmatter error; check Chat Diagnostics |
| The generator cannot reach the crawler | The `agents` list in `gherkin-generator.agent.md`'s frontmatter must include `web-crawler`, and the `agent` tool must be in its `tools` list; both already are in this version |
| Crawler falls back to Playwright on every page | The static `web_crawl` tool may be misconfigured or the application is a single-page application; this is expected behavior for SPAs |
| Linter step finds nothing to check | Confirm the linting extension is installed and active for `.feature` files |
