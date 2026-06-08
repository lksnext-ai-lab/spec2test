# TFM-Eneko Web Crawler

A sophisticated web crawler built with Python that extracts structured data from web pages and exposes it through an MCP (Model Context Protocol) server. This tool is designed for TFM (Final Master's Project) research purposes.

## Features

- **Deep Web Crawling**: Supports both Breadth-First Search (BFS) and Depth-First Search (DFS) crawling strategies
- **Structured Data Extraction**: Extracts links, buttons, input fields, and their XPath selectors
- **Markdown Content Generation**: Converts web page content to markdown format
- **MCP Server Integration**: Exposes crawling capabilities through a FastAPI-based MCP server
- **Docker Support**: Fully containerized application with Docker Compose support
- **VSCode Integration**: Compatible with VSCode MCP extension

## What It Does

The crawler performs the following operations on target websites:

1. **Link Extraction**: Identifies all internal and external links with their URLs
2. **Interactive Elements**: Finds buttons and input fields with their types and XPath selectors
3. **Content Processing**: Converts page content to clean markdown format
4. **Multi-page Crawling**: Can crawl multiple pages up to specified depth and page limits
5. **Error Handling**: Provides user-friendly error messages for connection issues

## Output Format

For each crawled page, the tool generates:

- **Link URLs**: List of all discovered links
- **Links**: Detailed link information with names, types, XPaths, and hrefs
- **Buttons**: Button elements with names, types, and XPath selectors
- **Inputs**: Input fields with names, types, and XPath selectors
- **Page Content**: Clean markdown representation of the page content

## Quick Start

### Using Docker (Recommended)

1. **Launch the application**:
   ```bash
   docker compose up -d --build
   ```

2. **Configure VSCode** by adding to your `settings.json`:
   ```json
   {
       "mcp": {
           "servers": {
               "tfm-crawler": {
                   "url": "http://127.0.0.1:8000/mcp/"
               }
           }
       }
   }
   ```

### Local Development Setup

1. **Prepare the environment**:
   ```bash
   cd tfm-crawler
   rm -rf .venv
   uv venv
   uv sync --no-dev
   ```

2. **Run locally**:
   ```bash
   python src/main.py
   ```

## Usage

### As MCP Tool

Once the server is running, you can use the `web_crawl` tool through any MCP-compatible interface. The tool will crawl `http://host.docker.internal:8080` by default with the following parameters:
- **Strategy**: BFS (Breadth-First Search)
- **Max Depth**: 2 levels
- **Max Pages**: 50 pages

### Direct Usage

You can also use the crawler directly:

```python
from crawler.web_crawler import web_crawler
import asyncio

# Crawl a website with custom parameters
result = await web_crawler(
    url="https://example.com",
    use_DFS=False,  # Use BFS strategy
    max_depth=3,
    max_pages=100
)
print(result)
```

## Technical Stack

- **Python 3.11+**: Core language
- **crawl4ai**: Advanced web crawling capabilities with Playwright
- **FastMCP**: MCP server implementation
- **BeautifulSoup4**: HTML parsing and XPath generation
- **Docker**: Containerization and deployment
- **UV**: Fast Python package management

## Configuration

### Authentication for Protected Sites

Most PoC web applications require login. Instead of manually extracting cookies and tokens, use the **interactive capture tool** to log in once and save the full auth state.

#### Quick Auth Setup (Recommended)

1. **Install Playwright locally** (one-time):
   ```bash
   pip install playwright
   python -m playwright install chromium
   ```

2. **Run the capture tool** — a browser will open:
   ```bash
   python capture_auth.py http://localhost:8080
   ```

3. **Log in normally** in the browser that opens, then press **Enter** in the terminal.

4. The tool saves `auth_state.json` containing all cookies, localStorage, and sessionStorage.

5. **Set the env var** in your `.env`:
   ```env
   CRAWLER_AUTH_STATE_FILE=auth_state.json
   ```

6. Rebuild/restart the crawler — it will use the captured state automatically.

> **Tip**: Re-run `capture_auth.py` whenever tokens expire. You can maintain multiple files for different apps (`prestashop_auth.json`, `joomla_auth.json`, etc.).

#### Legacy: Manual Cookie Configuration

You can still pass cookies manually via environment variable:

```env
CRAWLER_COOKIES=[{"session_id": "abc123"}, {"csrf_token": "xyz"}]
```

#### Legacy: Storage Injection

```env
CRAWLER_LOCAL_STORAGE=[{"token": "Bearer eyJ..."}]
CRAWLER_SESSION_STORAGE=[{"user": "{\"id\":1}"}]
```

#### Legacy: Login Recording Replay

Set `CRAWLER_LOGIN_RECORDING_FILE` to a Chrome DevTools Recorder JSON export.

### Crawling Parameters

- `url`: Target website URL
- `use_DFS`: Boolean flag for crawling strategy (True for DFS, False for BFS)
- `max_depth`: Maximum crawling depth
- `max_pages`: Maximum number of pages to crawl

### Server Configuration

The MCP server runs on port 8000 and provides:
- HTTP endpoint at `http://localhost:8000/mcp/`
- Stateless operation with JSON responses
- Tool registration for web crawling functionality

## Project Structure

```
tfm-crawler/
├── src/
│   ├── main.py              # MCP server entry point
│   └── crawler/
│       └── web_crawler.py   # Core crawling logic
├── docker-compose.yaml      # Docker Compose configuration
├── Dockerfile              # Container definition
├── pyproject.toml          # Project dependencies
└── README.md              # This file
```

## Error Handling

The crawler provides intelligent error handling for common issues:
- Connection refused errors with helpful diagnostics
- HTML parsing errors with graceful fallback
- Network timeout handling
- Invalid URL detection

## License

This project is part of a Final Master's Project (TFM) by Eneko P.