# Spec2Test for VS Code

A sidebar for the Spec2Test **input-processor**: create projects, drop in specs and recordings, process them with live progress, choose the LLMs and API keys, and open the original, pre-processed and cached files from one card. The extension starts and stops the Docker container for you.

## Requirements

- Docker (Docker Desktop on macOS/Windows, Docker Engine on Linux)
- Python 3 (only to run `scripts/sync_projects.py`)
- A clone of the `spec2test` repository

## Install (from source)

```bash
cd vscode-extension
npm ci
npm run package        # creates spec2test-<version>.vsix
code --install-extension spec2test-0.1.0.vsix
```

Open the **Spec2Test** icon in the activity bar. The header shows what is missing (Docker, the repo folder, a stopped container) and offers the next step.

## What it does

**Main page**

- **Top bar:** a searchable project dropdown (with *New project…*), a **+** button and the **⚙** settings button.
- **Project menu (⋮):** *Open* and *Change…* entries for each of the three folders (inputs, cache, pre-processed), use the project for agents, and remove it (there is also a trash button next to the menu). Removing asks whether to **detach only** or also **move the project's inputs and results to the trash**; other files in those folders are never touched. Changing a folder recreates the container (the folders are bind mounts) and does not move existing files.
- **Drop files** (a small native section above the page): drag files onto it from Finder/Explorer or from the VS Code Explorer, or click it to choose files. It has to be native because VS Code webviews cannot receive drops from the Explorer.
- **Files:** an *Add files…* button, then a card per file with its type icon, status, progress and actions:
  **Original**, **Pre-processed** and **Result** open the file in VS Code; the icons preview the result, show extracted images, compare with earlier results, process / reprocess and remove (to the trash).
- **Footer:** the Docker status with a small menu to start, stop, restart, rebuild the image and show the logs.

**Settings (⚙)** has four sections: **Models** (text and vision model, per project or for all projects), **Environment** (API keys), **Video** (how recordings are split) and **Advanced** (logging, the spec2test folder, rebuild, logs).

Notes:

- Dropped files are **copied** into the project's inputs folder; your originals are not touched.
- API keys are kept in the OS keychain (VS Code SecretStorage) and mirrored into the repo's `.env`, which the container reads. Changing keys or video/logging values needs a container restart: the **Apply and restart** bar does it.
- Adding, editing or removing a project regenerates `docker-compose.override.yaml` (via `scripts/sync_projects.py`) and recreates the container, because every project is its own bind mount.
- **Start** builds the image first (a no-op when nothing changed), so an image built by an older version is repaired. A container that runs but does not answer for 30 s is shown as *Not responding* with a **Rebuild** button.
- Opening a PDF uses the `tomoki1207.pdf` extension if installed (VS Code has no built-in PDF viewer).

## Traceability comments (Gherkin ↔ inputs)

The extension links each input to the scenarios generated from it through **comments in the `.feature` files**. The comments are the single source of truth; nothing else has to be kept in sync. This is the format the Gherkin agent should write:

```gherkin
# Inputs: SoA.md, QABAGE.md            <- before `Feature:`: every input used by this file
# Created: 2026-09-30

Feature: Assess Gherkin scenarios against the QABAGE quality attributes

  # Source: QABAGE.md | Created: 2026-09-30            <- directly above each scenario
  Scenario: Flag a scenario that lacks a When step

  # Source: SoA.md, QABAGE.md | Created: 2026-09-30    <- several inputs: comma-separated
  Scenario Outline: Route a low-confidence judgement to the LLM
```

Rules:

- Names are the input files' names **exactly** as they appear in the project's inputs folder (case-sensitive; names with spaces are fine, commas separate).
- `# Source:` belongs to the next `Scenario`, `Scenario Outline`, `Scenario Template` or `Example`. Blank lines, other comments and `@tags` may sit in between; any step line in between cancels it.
- `# Inputs:` is only read above `Feature:` and is not inherited by scenarios. `Created:` is optional.
- A scenario without `# Source:` is reported as *without a source*; a name that is not an input file is reported as *unknown input* (with a hint when only the case differs).

What you get:

- **Gherkin button** (in *Files*, next to Process): set the project's features folder (⋮ menu → *Set features folder…*; subfolders are scanned), then toggle the view. Under every input card it lists the features that cite it and their scenarios; clicking a scenario opens the `.feature` at that line. The **⟳** half of the button re-reads every `.feature` file. While the view is on, changes to feature files reload it automatically.
- **Traceability file:** each reload writes `<features folder>/.spec2test-traceability.json` (paths relative to the features folder, so it can be committed). It is only rewritten when its content changes. It has `features`, `byInput`, `unknownSources` and `untraced`.
- **Inside the `.feature` editor**, in files under a project's features folder: input names in `# Inputs:` / `# Source:` are links that select the input's card in the sidebar, hovering shows whether it is processed and how many scenarios cite it, and unknown names get a warning in the Problems panel.

## Settings

| Setting | Default | |
| --- | --- | --- |
| `spec2test.repoPath` | *(auto)* | Folder of the spec2test repository |
| `spec2test.port` | `8003` | Host port of the input-processor |
| `spec2test.pythonPath` | `python3` | Python used for `sync_projects.py` |
| `spec2test.autoStartService` | `false` | Start the container when VS Code opens |

## Development

```bash
npm ci
npm run watch          # rebuild on change; press F5 in VS Code to launch the extension host
npm run lint           # type-check the extension and the webview
npm test               # unit tests (vitest)
```

Layout: `src/core/` (project file, `.env`, file/cache mapping, job queue, `gherkin.ts` for the traceability comments) holds the logic that does not depend on VS Code (project file, `.env`, file/cache mapping, job queue) and is unit-tested; `src/controller.ts` wires it to VS Code, Docker and the MCP server; `webview-ui/` is the React sidebar. Manual end-to-end checklist: [`scripts/e2e-checklist.md`](scripts/e2e-checklist.md).
