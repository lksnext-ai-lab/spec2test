# Gherkin generator for Claude Code

This is the Agent Skills version of the same generator: `gherkin-generator/`, packaged as `gherkin-generator.skill` (the standard, importable artifact) or usable directly from the folder. It follows the [Agent Skills open standard](https://agentskills.io), so besides Claude Code it also works in any compatible harness, including GitHub Copilot's own Agent Skills support and OpenAI Codex CLI.

## 1. Install the skill

**Option A — import the `.skill` package (recommended, works in claude.ai and Claude Code):**

1. In Claude Code, run `/plugin` or open Settings → Capabilities → Skills, and upload `gherkin-generator.skill`.
2. Claude reads its `SKILL.md` and shows a summary. Toggle it on.

**Option B — project skill from the folder:**

Copy the whole `gherkin-generator/` folder into your project:

```
.claude/skills/gherkin-generator/
```

(Claude Code also reads `.agents/skills/` and, for GitHub Copilot compatibility, `.github/skills/` — same layout, pick the one matching your primary tool.) The folder name must equal the `name` field in `SKILL.md`'s frontmatter (`gherkin-generator`); this is required by the standard and is already correct in this package.

The skill loads automatically when a task matches its description (creating, updating, or reviewing Gherkin/BDD/`.feature` files), or on demand by typing `/gherkin-generator` in Claude Code.

## 2. Install the web-crawler subagent

A skill cannot register a subagent by itself, so the crawler's instructions ship inside the skill at `agents/web-crawler.md` and need one extra step:

```bash
cp gherkin-generator/agents/web-crawler.md .claude/agents/web-crawler.md
```

This registers `web-crawler` as a named subagent Claude Code can invoke by the Task tool. If you skip this step, the generator still works: it starts a general-purpose subagent and tells it to read and follow `agents/web-crawler.md` from the skill folder, giving equivalent behavior at slightly more overhead per crawl round.

## 3. Set up the MCP servers, including Playwright

The generator needs two MCP servers, `input-processor` and `web-crawler`, and the crawler needs a third, `playwright`, as a fallback for pages the static crawler cannot reach. In Claude Code, MCP servers are not part of the skill package; they are configured for the project (or your user account) separately, the same way you would add any MCP server.

**The command you're looking for is `claude mcp add`, run once from your terminal** (not the in-chat `/mcp`, which only lists and reconnects already-configured servers):

```bash
# Your own servers (adjust transport and URL/command to how you run them)
claude mcp add input-processor -s project --transport http http://localhost:REPLACE_PORT/mcp
claude mcp add web-crawler -s project --transport http http://localhost:REPLACE_PORT/mcp

# Playwright MCP: official server, launched locally through npx
claude mcp add playwright -s project -- npx @playwright/mcp@latest
```

`-s project` writes the server into `.mcp.json` at the project root, which you can commit so the whole team gets the same setup; teammates just approve the servers the first time they open the project. Use `-s user` instead for a server you want in every project, or omit `-s` for a private, project-scoped entry that is not shared.

Equivalently, you can hand-write `.mcp.json` yourself; `assets/mcp.json.example` in the skill folder shows the expected shape:

```json
{
  "mcpServers": {
    "input-processor": { "type": "http", "url": "http://localhost:REPLACE_PORT/mcp" },
    "web-crawler": { "type": "http", "url": "http://localhost:REPLACE_PORT/mcp" },
    "playwright": { "command": "npx", "args": ["@playwright/mcp@latest"] }
  }
}
```

Verify all three are up with:

```bash
claude mcp list
```

or `/mcp` inside a Claude Code session, which also lets you reconnect a server without restarting.

**Server names matter.** The skill's instructions reference tools as `mcp__input-processor__*`, `mcp__web-crawler__*`, and `mcp__playwright__*`. If you name a server differently, either rename it to match or update the tool references in `SKILL.md` and `agents/web-crawler.md`.

**Do not translate `localhost` to `host.docker.internal` yourself.** The `web_crawl` tool on your `web-crawler` MCP server is expected to do that on its side. Give the skill the application's normal URL.

## 4. Set up the Gherkin linter

The linter is a bundled Python script, not an MCP server, so there is nothing to register: `scripts/run_lint.py`, called by the skill in its review step, creates a virtual environment (`.venv-gherkin`, in your project root) the first time it runs, installs the pinned `gherkin-official` package into it, and reuses that environment on every later call. This needs Python 3.9 or later on your machine; nothing else.

Add the virtual environment to your `.gitignore`:

```
.venv-gherkin/
```

To swap the linter later (a different tool, extra rules), edit `scripts/lint_gherkin.py` and `scripts/requirements.txt`; the calling instruction is one line in `SKILL.md`'s review step.

## 5. Permissions for unattended runs

By default, Claude Code asks for approval before an MCP tool or a shell command runs. For an interactive session this is fine and matches the skill's own checkpoints. For unattended evaluation runs, pre-approve the MCP servers and `python`/`py` in your permission settings, or the run will stop at a permission prompt rather than a skill checkpoint.

## 6. Run it

Start a task that matches the skill's description, for example:

> Generate the Gherkin features for the checkout flow. Documentation is already in the input processor. The app runs at http://localhost:3000.

Claude loads the skill, asks the setup questions it cannot infer, and proceeds through analysis, exploration, planning, and writing, stopping at each checkpoint for your approval (through the AskUserQuestion tool where available). Feature files land wherever you told it to; `traceability.md` sits alongside them.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Skill never triggers | Check its `name` matches the parent folder exactly; a mismatch makes it fail to load silently |
| `mcp__web-crawler__*` tool not found | Server not added, wrong name, or not yet approved this session; check `claude mcp list` |
| Crawler never asks you anything mid-round | Expected: subagents cannot talk to you during a run; it returns a bounded report each round instead, and the generator asks between rounds |
| Linter step fails to run | Confirm `python3` (or `py` on Windows) is on the path; delete `.venv-gherkin` to force a clean reinstall |
| Playwright fallback fails | Confirm Node.js and `npx` are installed; the first run of `npx @playwright/mcp@latest` downloads the package |
