# Spec2Test - Gherkin Generator Agent Workflow
<img src="./Spec2Test.png" alt="Spec2Test Logo" width="180" />

This repository contains a small stack of MCP (Model Context Protocol) services used to support Gherkin feature generation in a VS Code Copilot workflow. It combines structured crawling, input analysis, and safe filesystem access to feed downstream test generation.

## What is included

- **input-processor**: MCP server that analyzes MP4, PDF, Markdown, and text files, then caches structured summaries for test generation.
- **web-crawler**: MCP server that crawls a site to extract links, UI elements, and page content in markdown.
- **filesystem-mcp**: MCP server that exposes safe, sandboxed file operations within allowed directories only.
- `.claude/skills/gherkin-multiple-v5/` — The Claude Skill that computes all maintainability metrics and produces the Excel workbooks and JSON state files to help assess the maintainability quality of the generated Gherkin. The paper regarding the measurement is waiting to be published. The metric descriptions are in the document .claude/skills/gherkin-multiple-v5/Feature Maintainability Metrics.md.

## Quick start (Docker)

1. Create a `.env` file from `.env.example`. At minimum configure:
	- `INPUTS_DIR` and `INPUTS_CACHE_DIR` as host paths for mounted input and cache storage
	- `INPUT_PROCESSOR_PROVIDER` and the matching provider API key
	- `CRAWLER_AUTH_ACTIONS_FILE` only when authenticated crawling is required

	The authentication JSON file is sensitive. Keep it outside version control and mount it
	through the `crawler` service as `auth_actions.json`.
2. Build and run the stack:
	```bash
	docker compose up -d --build
	```
3. Optional GPU support:
	```bash
	docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d --build
	```

## Services and ports

- `web-crawler`: `http://localhost:8000`
- `filesystem-mcp`: `http://localhost:8002`
- `input-processor`: `http://localhost:8003`

All MCP services expose their endpoint at `/mcp`. The ports above are host ports; the
containers listen on port `8000` internally.

Refer to each service README for MCP configuration snippets and tool details.

## Typical workflow

1. Place documents and recordings in `INPUTS_DIR`.
2. Run the input processor to analyze and cache content.
3. Crawl the target web app to capture structure and UI elements.
4. Use both outputs to generate Gherkin features and step definitions.

## Development

- Input processing: see `input-processor/README.md`
- Web crawling: see `web-crawler/README.md`
- Filesystem MCP: see `filesystem-mcp/README.md`

The Compose file mounts the `src` directories of the Python services for local
development. For a production-like image, remove those source mounts and rebuild the
images so the code copied during `docker build` is used.

Do not expose these services directly to the public internet. They currently rely on
network-level isolation and should be placed behind an authenticated, restricted
network when used outside a local development environment.

## Repository layout

```
filesystem-mcp/        # Sandboxed filesystem read/write for agents
input-processor/       # File analysis for MP4, PDF, Markdown, and text inputs
web-crawler/           # Site crawler that extracts links, UI elements, and content
docker-compose.yaml    # Core services
docker-compose.gpu.yaml # GPU override
```

## Support

For installation questions or issues encountered, please contact `bperez@lksnext.com`
or `eneko.pizarro@ehu.eus`.

# LICENSE:
The code developed for this project is licensed under the PolyForm Noncommercial
License 1.0.0. The `filesystem-mcp` component remains separately licensed under the MIT License.

You may use, study, modify, and share this software for non-commercial purposes,
including personal, educational, research, and evaluation use.

Commercial use is not permitted without prior written permission from the copyright holder.
For commercial licensing, please contact LKS Next at `qacontact@lksnext.com`.