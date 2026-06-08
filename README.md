# Spec2Test - Gherkin Generator Agent Workflow
<img src="./Spec2Test.png" alt="Spec2Test Logo" width="180" />

This repository contains a small stack of MCP (Model Context Protocol) services used to support Gherkin feature generation in a VS Code Copilot workflow. It combines structured crawling, input analysis, and safe filesystem access to feed downstream test generation.

## What is included

- **input-processor**: MCP server that analyzes MP4, PDF, Markdown, and text files, then caches structured summaries for test generation.
- **web-crawler**: MCP server that crawls a site to extract links, UI elements, and page content in markdown.
- **filesystem-mcp**: MCP server that exposes safe, sandboxed file operations within allowed directories only.

## Quick start (Docker)

1. Create a `.env` file (see the component READMEs for full details). Common values:
	- `INPUTS_DIR` and `INPUTS_CACHE_DIR` for mounted input storage
	- `GOOGLE_API_KEY` for Gemini-based analysis in the input processor
	- `HF_TOKEN` (optional) for Hugging Face models
	- `CRAWLER_AUTH_STATE_FILE` (optional) for authenticated crawling
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

## Repository layout

```
filesystem-mcp/        # Sandboxed filesystem read/write for agents
input-processor/       # File analysis for MP4, PDF, Markdown, and text inputs
web-crawler/           # Site crawler that extracts links, UI elements, and content
docker-compose.yaml    # Core services
docker-compose.gpu.yaml # GPU override
```

# LICENSE:
This project is licensed under the PolyForm Noncommercial License 1.0.0.

You may use, study, modify, and share this software for non-commercial purposes,
including personal, educational, research, and evaluation use.

Commercial use is not permitted without prior written permission from the copyright holder.
For commercial licensing, please contact: `bperez@lksnext.com` or `eneko.pizarro@ehu.eus`.