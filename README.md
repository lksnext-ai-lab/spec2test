# Spec2Test - Gherkin Generator Agent Workflow
<img src="./Spec2Test.png" alt="Spec2Test Logo" width="180" />

This repository contains a small stack of MCP (Model Context Protocol) services used to support Gherkin feature generation in a VS Code Copilot workflow. It combines structured crawling and input analysis to feed downstream test generation.

## What is included

- **input-processor**: MCP server that analyzes MP4, PDF, Markdown, and text files, then caches structured summaries for test generation.
- **web-crawler**: MCP server that crawls a site to extract links, UI elements, and page content in markdown.
- `.claude/skills/gherkin-multiple-v5/` — The Claude Skill that computes all maintainability metrics and produces the Excel workbooks and JSON state files to help assess the maintainability quality of the generated Gherkin. The paper regarding the measurement is waiting to be published. The metric descriptions are in the document .claude/skills/gherkin-multiple-v5/Feature Maintainability Metrics.md.

## Quick start (Docker)

1. Create a `.env` file from `.env.example`. At minimum configure:
	- the API key of the provider you will use (for example `GOOGLE_API_KEY`)
	- `CRAWLER_AUTH_ACTIONS_FILE` only when authenticated crawling is required

	The authentication JSON file is sensitive. Keep it outside version control and mount it
	through the `crawler` service as `auth_actions.json`.
2. Describe your projects in `projects.json` (see `projects.example.json`), then generate
	the mounts and start the stack:
	```bash
	cp projects.example.json projects.json   # first time only
	$EDITOR projects.json
	python scripts/sync_projects.py
	docker compose up -d --build
	```

	`projects.json` is yours and stays out of version control. Each project gets its own
	inputs folder plus its own cache and preprocessed folders, all mounted into
	`input-processor` under `/projects/<name>/…`.
3. Optional GPU support:
	```bash
	docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d --build
	```

## Services and ports

- `web-crawler`: `http://localhost:8000`
- `input-processor`: `http://localhost:8003`

All MCP services expose their endpoint at `/mcp`. The ports above are host ports; the
containers listen on port `8000` internally.

Refer to each service README for MCP configuration snippets and tool details.

## Typical workflow

1. Place documents and recordings in a project's inputs folder (see `projects.json`).
2. Run the input processor to analyze and cache content.
3. Crawl the target web app to capture structure and UI elements.
4. Use both outputs to generate Gherkin features and step definitions.

Each project is addressed by the `X-Spec2Test-Project` request header, so one stack
serves several workspaces at once. The committed `.vscode/mcp.json` sends that header
with the example project name: change it to the project you are working on, or add one
server entry per project. Call the `current_project` tool to check that a session
resolved to the project you meant.

## VS Code extension

`vscode-extension/` is a sidebar for the input-processor: it creates projects, copies
dropped files into them, processes them with live progress, lets you pick the models and
API keys, opens the original / pre-processed / cached file from one card, and starts and
stops the Docker container for you. See [`vscode-extension/README.md`](vscode-extension/README.md).

## Development

- Input processing: see `input-processor/README.md`
- Web crawling: see `web-crawler/README.md`

The Compose file mounts the `src` directories of the Python services for local
development. For a production-like image, remove those source mounts and rebuild the
images so the code copied during `docker build` is used.

Do not expose these services directly to the public internet. They currently rely on
network-level isolation and should be placed behind an authenticated, restricted
network when used outside a local development environment.

## Repository layout

```
input-processor/       # File analysis for MP4, PDF, Markdown, and text inputs
web-crawler/           # Site crawler that extracts links, UI elements, and content
vscode-extension/      # VS Code sidebar to manage projects, files and processing
scripts/               # sync_projects.py: projects.json -> Compose override
projects.example.json  # Starting point for your own projects.json (gitignored)
docker-compose.yaml    # Core services
docker-compose.gpu.yaml # GPU override
```

## Support

For installation questions or issues encountered, please contact `bperez@lksnext.com`
or `eneko.pizarro@ehu.eus`.

# LICENSE:
The code developed for this project is licensed under the PolyForm Noncommercial
License 1.0.0.

You may use, study, modify, and share this software for non-commercial purposes,
including personal, educational, research, and evaluation use.

Commercial use is not permitted without prior written permission from the copyright holder.
For commercial licensing, please contact LKS Next at `qacontact@lksnext.com`.