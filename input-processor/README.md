# Input Processor Module

A component of the Spec2Test stack that analyzes input files for automated test
scenario generation. It runs as an MCP (Model Context Protocol) server that handles
video recordings of browser sessions plus PDF, Markdown, and plain text documentation,
extracting the information a Gherkin generator needs.

## Features

- **Video Processing**: Analyzes MP4 recordings of browser sessions to extract UI
  interactions, workflows, and user journeys
- **PDF Processing**: Extracts requirements, specifications, and business rules
- **Markdown Processing**: Reads Markdown documents and enriches local image references
  with generated descriptions when a vision model is configured
- **Text Processing**: Reads plain text documents without additional preprocessing
- **Project Workspaces**: One container serves several projects side by side; the
  request asks for one with a header
- **Name-based Caching**: Results are cached per source file name, with the content
  digest stored inside the file, so unchanged files are never reprocessed

## Quick start

1. Copy the example configuration and point it at your folders:

   ```bash
   cp projects.example.json projects.json
   ```

   Each entry names a project and the folder holding its inputs. Relative paths are
   resolved against the folder holding `projects.json`; `inputs` defaults to
   `<name>/inputs`, and `preprocessed`/`cache` to `.spec2test-data/<name>/…`.

2. Generate the Compose override that mounts every project into `input-processor`,
   then start the stack:

   ```bash
   python scripts/sync_projects.py
   docker compose up -d --build input-processor
   ```

   `sync_projects.py` also creates the output folders and refuses to run when an inputs
   folder is missing, so a typo in `projects.json` fails on the host instead of inside
   the container.

3. Point an MCP client at `http://localhost:8003/mcp` and send the project header:

   ```json
   {
     "servers": {
       "input-processor": {
         "url": "http://localhost:8003/mcp",
         "type": "http",
         "headers": { "X-Spec2Test-Project": "shop-app" }
       }
     }
   }
   ```

   The header is what selects the workspace — edit its value to switch project. To keep
   several projects available at once, add one server entry per project (for example
   `input-processor-admin-portal`); note that VS Code addresses tools as
   `<server>/<tool>`, so an agent that allowlists `input-processor/*` needs the extra
   entries added to its tool list as well. Call the `current_project` tool to confirm
   which project a session resolved to.

## Configuration

Provider keys and tuning live in `.env`; provider *choice* lives in `projects.json`, so
two projects can use different models from the same container.

```json
{
  "defaults": { "llm": { "provider": "google_genai", "model": "gemini-2.5-flash" } },
  "projects": [
    {
      "name": "shop-app",
      "inputs": "/home/me/specs/shop-app",
      "llm": { "model": "gemini-2.5-pro" },
      "vision": { "provider": "openai", "model": "gpt-4o" }
    }
  ]
}
```

- `defaults.llm` / `defaults.vision` apply to every project; a project may override
  either one, and a partial override only replaces the fields it sets.
- `llm` is the model that reads documents and drives video analysis.
- `vision` is the model that describes images (PDF renderings, Markdown images). Leave
  it unset to reuse `llm`, or set it to a project whose provider cannot see images to
  disable image enrichment for that project.
- Names must match `[a-z0-9][a-z0-9._-]*`. The container and `sync_projects.py` share
  that rule, and a duplicate name is refused.

### Choosing a provider and model

Providers are resolved by name from two sources:

| Provider                               | Capabilities         | Notes                                     |
| -------------------------------------- | -------------------- | ----------------------------------------- |
| `google_genai`                         | text, images, native video upload | Gemini; large recordings go through the File API |
| `openai` / `anthropic`                 | text, images         | Video is analyzed as sampled frames       |
| `deepseek`                             | text                 | Metadata-only video analysis              |
| `openrouter`                           | text, images, inline video | Model list in `src/providers/catalog.json` |
| `qwen`                                 | text, images         | DashScope compatible-mode endpoint        |

OpenAI-compatible providers are declared declaratively in
`src/providers/catalog.json` (base URL, API key variable, default model, capabilities,
and optional per-model capability overrides), so adding one is a config change rather
than code.

### How a video strategy is chosen

Capabilities decide, not provider names. In order of preference:

1. **Native upload** — the recording is uploaded through the provider's file API, polled
   until it is processed, analyzed, and deleted afterwards. Best fidelity, no size limit
   worth worrying about.
2. **Inline video** — the MP4 is sent base64-encoded, split into segments first when it
   is large or long; segment summaries are re-timestamped onto the full timeline and
   merged into one report.
3. **Frame sampling** — evenly spaced frames are sent as images.
4. **Metadata-only** — for text-only providers: a report built from frame count,
   duration, and resolution changes, with a warning that visual detail is unavailable.

### Environment variables

Secrets: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`,
`OPENROUTER_API_KEY`, `DASHSCOPE_API_KEY` (as required by the providers you use).

Tuning (all optional, defaults in brackets):

| Variable                                      | Purpose                                          |
| --------------------------------------------- | ------------------------------------------------ |
| `INPUT_PROCESSOR_PROJECTS_CONFIG`             | Path to `projects.json` in the container `[/config/projects.json]` |
| `INPUT_PROCESSOR_PROJECTS_ROOT`               | Folder holding the mounted projects `[/projects]` |
| `INPUT_PROCESSOR_LOG_LEVEL`                   | `DEBUG`, `INFO`, … `[INFO]`                      |
| `INPUT_PROCESSOR_VIDEO_SEGMENT_SECONDS`       | Target segment length `[60]`                     |
| `INPUT_PROCESSOR_VIDEO_SPLIT_MIN_MB`          | Split a file at least this big `[12]`            |
| `INPUT_PROCESSOR_VIDEO_SPLIT_BY_DURATION`     | Also split long recordings `[true]`              |
| `INPUT_PROCESSOR_VIDEO_FORCE_SPLIT`           | Always split `[false]`                           |
| `INPUT_PROCESSOR_VIDEO_REQUIRE_AUDIO`         | Refuse OpenCV splitting, which drops audio `[true]` |
| `INPUT_PROCESSOR_VIDEO_CONSOLIDATE`           | Merge segment summaries into one report `[true]` |
| `INPUT_PROCESSOR_VIDEO_FRAME_SECONDS`         | Seconds between sampled frames `[2]`             |
| `INPUT_PROCESSOR_VIDEO_MAX_FRAMES`            | Frame budget for frame sampling `[20]`           |

## MCP tools

### `current_project`

Reports which project the request was resolved as: name, container paths, and the
configured models. Use it to confirm you are looking at the intended files.

```json
{ "name": "shop-app", "inputs": "/projects/shop-app/inputs", "cache": "/projects/shop-app/cache",
  "provider": "google_genai", "model": "gemini-2.5-flash", "vision_provider": "", "vision_model": "" }
```

### `process_files`

Processes every supported file in the project's inputs folder and returns one object per
file, plus one per orphaned cache entry:

```json
[{ "name": "login-demo.mp4", "format": ".mp4", "size": 15728640,
   "sha256": "9f2c…", "status": "new", "processed_at": "2026-09-29T10:00:00Z" }]
```

`status` is one of:

| Status     | Meaning                                                                 |
| ---------- | ----------------------------------------------------------------------- |
| `new`      | First time this file is processed                                       |
| `cached`   | Unchanged since the last run: no model call                             |
| `updated`  | Content changed: reprocessed, and the previous result is archived       |
| `renamed`  | Same content under a new name: re-keyed, no model call                  |
| `orphaned` | Cached, but its source is gone from the inputs folder (content is kept) |
| `error`    | Could not be processed; the object carries an `error` field             |

Files that fail are reported individually — one unreadable PDF does not fail the run.

### `list_processed_files`

Lists everything with cached content: `name`, `sha256` and `processed_at`.

### `get_processed_content`

Returns the full analysis of one file. Pass `file_name` (as returned by
`list_processed_files`). `file_hash` is deprecated but still accepted: a SHA-256 digest
or any unambiguous prefix of one resolves to the same file.

### `get_all_processed_content`

Returns `name`, `sha256`, `processed_at` and `content` for every cached file in one call.

## Cache layout

Given a project whose cache is mounted at `/projects/shop-app/cache` and an input
`login-demo.mp4`:

```
cache/login-demo.mp4.md          # front-matter + processed content
cache/.history/login-demo.mp4.9f2c1a04.20260929T100000Z.md   # superseded result
preprocessed/login-demo.mp4.md   # intermediate form fed to the model
preprocessed/login-demo.mp4_images/  # images extracted from a PDF
cache/_segments/                 # scratch space for video splitting
```

Every cache file starts with a front-matter block:

```markdown
---
source: "login-demo.mp4"
format: ".mp4"
size: 15728640
sha256: "9f2c…"
processed_at: "2026-09-29T10:00:00Z"
provider: "google_genai"
model: "gemini-2.5-flash"
---

…processed content…
```

The source name makes the cache human-readable; the digest makes change detection
independent of the file name, so renaming a cache file by hand never causes a false
"changed". Writes are atomic (temporary file + rename), and a legacy `<hash>.txt` cache
from an older installation is migrated into this layout on first use.

## Architecture

```
src/
├── main.py              # MCP server: the five tools, header -> project resolution
├── settings.py          # Environment parsing (typed, with defaults)
├── processing_service.py# Orchestrates one project's run; reports per-file status
├── projects/            # projects.json parsing, header handling, per-project runtime
├── providers/           # Provider strategy + registry (+ catalog.json)
├── handlers/            # One handler per format: video, pdf, markdown, text
├── analysis/            # Document summarizer, image describer, video strategies
├── preprocessing/       # PDF -> Markdown, Markdown image enrichment
├── cache/               # Front-matter cache, index, reconciliation, preprocessed store
├── prompts/             # Prompt templates as .md files
└── utils/               # Hashing, text, media, lazy OpenCV access
```

Design notes:

- **Strategy + registry.** Providers and video analyzers are chosen by capability and
  registered in a registry; nothing switches on a provider name.
- **Constructor injection.** Every collaborator is passed in, so a test can build a
  service with a stub chat model and no network.
- **Blocking work runs off the event loop.** MCP tools are `async`, but hashing,
  file access, and LLM calls run in a worker thread under the project's lock.
- **Heavy imports are lazy.** OpenCV, PyPDF2, PyMuPDF, and the Google SDK load only
  when a file that needs them is processed.

## Development

```bash
pip install -r requirements-dev.txt      # plus -r requirements.txt for the runtime
python -m pytest tests -q
```

The suite needs no API keys and no heavyweight dependencies: chat models, OpenCV, the
Google SDK, and `mcp` are replaced with small test doubles in `tests/support.py`.

Run the server directly:

```bash
python src/main.py            # listens on 0.0.0.0:8000, endpoint /mcp
```

Inside Compose it listens on `8000`; `8003` is the host port.

## Error handling

- **Per-file isolation**: a file that fails is reported with `status: "error"` and an
  explanation; the rest of the run continues.
- **Missing project folder**: a project whose `inputs` folder was never mounted fails
  with a message naming `scripts/sync_projects.py`.
- **Unknown or missing header**: the tool returns an error listing the configured
  projects instead of guessing.
- **PDF encryption**: decryption is attempted before falling back to a clear error.
- **Optional packages**: if PyPDF2, OpenCV, or `google-generativeai` are missing, the
  error says which package to install.

## License

This module is part of the Spec2Test project and is licensed under the PolyForm
Noncommercial License 1.0.0. See the repository [LICENSE](../LICENSE) for the
applicable terms.
