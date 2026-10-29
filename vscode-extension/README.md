# Spec2Test for VS Code

A sidebar for the Spec2Test **input-processor**: create projects, drop in specs and recordings, process them with live progress, choose the LLMs and API keys, and open the original, pre-processed and cached files from one card. The extension pulls the images and starts and stops the Docker containers (input-processor and web crawler) for you.

## Requirements

- Docker (Docker Desktop on macOS/Windows, Docker Engine on Linux)

No clone of the repository, Python or Compose is needed.

## Install (from source)

```bash
cd vscode-extension
npm ci
npm run package        # creates spec2test-<version>.vsix
code --install-extension spec2test-0.1.0.vsix
```

Open the **Spec2Test** icon in the activity bar. The header shows what is missing (Docker, a stopped container) and offers the next step.

The extension runs `ghcr.io/lksnext-ai-lab/spec2test-input-processor:<extension version>` (and the matching web-crawler image). Until those are published, build them locally and point the image settings at them: `./scripts/verify-image.sh` builds both as `:dev`, then set `spec2test.image.inputProcessor` to `spec2test-input-processor:dev` and `spec2test.image.webCrawler` to `spec2test-web-crawler:dev`.

API keys are stored in the OS keychain and handed to the container as environment variables when it starts; no `.env` file is written. If you used the old setup, the keys, tuning values, projects and `auth_actions.json` of the clone you have open are imported once.

## What it does

**Main page**

- **Top bar:** a searchable project dropdown (with *New project…*), a **+** button and the **⚙** settings button.
- **Project menu (⋮):** *Open* and *Change…* entries for each of the three folders (inputs, cache, pre-processed), use the project for agents, and remove it (there is also a trash button next to the menu). Removing asks whether to **detach only** or also **move the project's inputs and results to the trash**; other files in those folders are never touched. Changing a folder does not move existing files.
- **Drop files** (a small native section above the page): drag files onto it from Finder/Explorer or from the VS Code Explorer, or click it to choose files. It has to be native because VS Code webviews cannot receive drops from the Explorer.
- **Files:** an *Add files…* button, then a card per file with its type icon, status, progress and actions:
  **Original**, **Pre-processed** and **Result** open the file in VS Code; the icons preview the result, show extracted images, compare with earlier results, process / reprocess and remove (to the trash).
- **Footer:** the container status with a small menu to start, stop, restart, update the image and show the logs. *Update available* appears when the running container does not use the image this version of the extension wants.

**Settings (⚙)** has four sections: **Models** (text and vision model, per project or for all projects), **Environment** (API keys), **Video** (how recordings are split) and **Advanced** (logging, the spec2test folder, rebuild, logs).

Notes:

- Dropped files are **copied** into the project's inputs folder; your originals are not touched.
- API keys are kept in the OS keychain (VS Code SecretStorage) and mirrored into the repo's `.env`, which the container reads. Changing keys or video/logging values needs a container restart: the **Apply and restart** bar does it.
- Projects live in `~/.spec2test/projects.json`. The container mounts only `~/.spec2test`, so adding, editing or removing a project never restarts it. After updating from an older version, press *Restart* once so the container gets the new mount.
- Your inputs folder is never modified. A file is copied into the work area (`~/.spec2test/<project>/inputs`, an instant clone on APFS) only while it is processed, with progress on its card; if it is already processed (same name and hash) nothing is copied. Results are copied back to `<inputs>/.spec2test/cache`, which you can commit. The work area can be deleted at any time and is rebuilt from your folders.
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
| `spec2test.port` | `8003` | Host port of the input-processor |
| `spec2test.autoStartService` | `false` | Start the containers when VS Code opens |
| `spec2test.image.inputProcessor` | *(published image)* | Image to run; set a local tag when developing |
| `spec2test.image.webCrawler` | *(published image)* | Same, for the web crawler |
| `spec2test.webCrawler.enabled` | `true` | Also run the web-crawler container |
| `spec2test.webCrawler.port` | `8000` | Host port of the web crawler |
| `spec2test.gpu` | `false` | Pass `--gpus all` to the input-processor |

## Development

```bash
npm ci
npm run watch          # rebuild on change; press F5 in VS Code to launch the extension host
npm run lint           # type-check the extension and the webview
npm test               # unit tests (vitest)
```

Layout: `src/core/` (project file, `.env`, file/cache mapping, job queue, `gherkin.ts` for the traceability comments) holds the logic that does not depend on VS Code (project file, `.env`, file/cache mapping, job queue) and is unit-tested; `src/controller.ts` wires it to VS Code, Docker and the MCP server; `webview-ui/` is the React sidebar. Manual end-to-end checklist: [`scripts/e2e-checklist.md`](scripts/e2e-checklist.md).
