# Manual end-to-end checklist

Run this on a machine with Docker. It exercises what the unit tests cannot: the real
container, the real VS Code host and the real LLM providers. Each step says what you
should see. Stop at the first step that does not match and note it.

## Prepare

```bash
cd vscode-extension
npm ci
npm run package
code --install-extension spec2test-0.1.0.vsix --force
```

Reload VS Code and use a scratch copy of a
`.mp4` (a few minutes long, ideally > 12 MB so it is split), a `.pdf` with images, a `.md`
and a `.txt`. Have one API key ready (Google is the default provider).

Until the images are published, run `./scripts/verify-image.sh` first: it builds both images as `:dev`, starts them with the extension's own `docker run` arguments on spare ports and checks the mount and the no-restart behaviour. Then set `spec2test.image.inputProcessor` to `spec2test-input-processor:dev` and `spec2test.image.webCrawler` to `spec2test-web-crawler:dev`.

Optionally check the backend on its own first: `python -m pytest input-processor/tests`.

## Steps

1. **Docker stopped.** Stop Docker Desktop. Open the Spec2Test icon.
   *Expect:* a banner "Docker is not running" with a **Start Docker** button and the footer
   showing "Docker off"; starting Docker turns it into "The input-processor is stopped" within about 10 s.
0. **Switching pages.** Click ⚙, switch between the four tabs, then go back with the arrow.
   *Expect:* the page never goes blank (if it ever does, it shows "Something went wrong" with **Try again**).
2. **Start.** Press **Start input-processor** (banner or footer menu). *Expect:* the image is
   pulled if it is missing (progress in *Show logs*), then a green "Running" in the footer and a
   small "Crawler running" note next to it. **Footer menu → Show logs** streams the input-processor
   logs, *Show web-crawler logs* the crawler's. `docker ps` lists `spec2test-input-processor` and
   `spec2test-web-crawler`, both published on `127.0.0.1` only, and `docker inspect` of the first
   shows no API key in its command line.
   *Regression to check:* if the container is up but silent, after ~30 s the footer must say
   "Not responding" and offer **Update image and restart**. After rebuilding a `:dev` image,
   the footer says "Update available" until you restart.
3. **Environment.** ⚙ → *Environment*, paste your key next to its provider, **Save**.
   *Expect:* the chip turns *Set* and a "Restart the input-processor…" bar appears;
   **Apply and restart** recreates the container and the bar disappears. The
   container has the key (`docker exec spec2test-input-processor printenv GOOGLE_API_KEY`) while
   `docker inspect spec2test-input-processor` shows it nowhere in the command line, and no
   `.env` file was written. In *Video* and
   *Advanced*, change a value: an "Unsaved changes" bar offers Save / Discard.
4. **Create a project.** **+** (or the dropdown's *New project…*) → name `demo` → *Use the default folder* (or *Choose the folder with my specs…*).
   Then open the project **⋮** menu and try *Change cache folder…* and *Open cache folder*: each acts on that one folder only.
   *Expect:* no restart; `~/.spec2test/projects.json` contains `demo`; the project is selected.
   Create a second project on an outside folder while the first is processing: the running job is not interrupted.
5. **Drop files.** Drag the four files from Finder onto the **Drop files** line at the top of the
   sidebar, and one more from the VS Code Explorer. Include a video larger than 100 MB.
   *Expect:* cards appear as **New**; the originals are still where they were; an unsupported
   file (e.g. `.docx`) is rejected with a message. Drop the same file again: you are asked
   Replace / Keep both / Skip. **Add files…** in the page does the same with a file picker.
6. **Process with live progress.** Press **Process**. *Expect:* the card being processed
   shows the stage and a bar, e.g. `Analysing video segment 3/8`, `Describing image 4/12`,
   `Consolidating segment summaries`; the others say **Queued**; finished cards turn
   **Processed** and the timestamp and model appear.
7. **Open from the card.** For the PDF card: **Original** (offers the PDF viewer
   extension), **Pre-processed**, **Result**, and the eye (preview) and image icons. For the video:
   **Original** plays it in VS Code. *Expect:* everything opens in VS Code; nothing needs
   a file browser.
8. **Cancel.** Add another long video and press **Process**, then **Cancel** mid-way.
   *Expect:* the card shows **Cancelled** within a few seconds; `docker compose logs
   input-processor` stops advancing; no half-written `cache/<name>.md`.
9. **Reprocess + history.** On a processed card press the refresh icon. *Expect:* it runs
   again and a clock icon with a "1" appears; it opens a diff of the old result against the
   new one.
10. **Change the model.** ⚙ → *Models* → *Project: demo* → pick another provider and model
    (try typing a custom model id in the search box).
    *Expect:* a warning appears if that provider has no key (with an inline key field), and
    if the vision model cannot read images. Reprocess a file: the card shows the new model.
11. **Orphans and remove.** Delete an input file outside VS Code. *Expect:* a "1 result without
    a source file" line with **Archive**; it moves the result into `cache/.history` (nothing is
    deleted). The trash icon on a card moves the input to the trash.
12. **Agents still work.** Project **⋮** menu → *Use this project for agents*, then run the Gherkin generator agent.
    *Expect:* `.vscode/mcp.json` has `X-Spec2Test-Project: demo` and the agent's
    `process_files` / `list_processed_files` calls return the same files.
13. **Remove a project.** Create a throw-away project with a file, press the trash button next to the project's **⋮** menu. *Expect:* a dialog with **Detach only** and **Detach and move … to the trash**. Detach only: the project disappears, the files stay on disk. Repeat with the trash option: the input files and their results go to the OS trash, any other file in the folder stays.
14. **Gherkin traceability.** Put a `.feature` file with `# Inputs:` / `# Source:` comments (see the README) in a folder, e.g. `features/`, naming two of your inputs and one name that does not exist.
    - Project **⋮** → *Set features folder…* → pick it, then press **Gherkin**. *Expect:* under each input card, "N scenarios · M features" and the scenarios; an input nobody cites says "Not referenced by any scenario"; a strip shows "1 unknown input".
    - Click a scenario. *Expect:* the `.feature` opens with the cursor on that scenario's line.
    - Open the `.feature`. *Expect:* the input names in the comments are underlined links; clicking `SoA.md` (or whichever) focuses the sidebar and flashes that card; hovering shows the status; the unknown name has a yellow warning (Problems panel).
    - Edit a comment and save. *Expect:* the sidebar updates by itself; **⟳** forces a rescan; `features/.spec2test-traceability.json` exists and only changes when the content changes.
    - *If the editor links do nothing when clicked:* that is the one unverified part (links that run a command); tell me and I will switch them to another mechanism.
15. **Stop.** Footer menu → **Stop**. *Expect:* "Input-processor is stopped"; files and results
    remain on disk.

## Self-update

1. Build an older version (`npm version 0.0.1 --no-git-tag-version`, `npm run package`, then revert the version) and install it in a clean profile, with a newer release published on GitHub.
2. *Spec2Test: Check for updates*. *Expect:* "Spec2Test X is available (you have 0.0.1)" with **Update / Release notes / Skip this version**. **Skip** hides the startup prompt for that version but the command still offers it.
3. **Update**. *Expect:* a download notification, then "installed, reload the window". After **Reload Window**, `code --list-extensions --show-versions` shows the new version. If a container was running, the footer shows "Updating the image…" and ends with the images of the new version (`docker ps --format '{{.Image}}'`).
4. Offline or unauthenticated 404: the command says it could not check; the startup check stays silent.

## Data folder

1. ⚙ → *Advanced* → **Data folder → Change…**, pick an empty folder outside `~/.spec2test`. *Expect:* a dialog offering *Copy and switch*; after it, the footer shows the container restarting, `projects.json` and the project work areas are in the new folder, your input folders are untouched, and processing a file works.
2. **Default** returns to `~/.spec2test`. Editing `spec2test.dataFolder` in settings by hand has the same effect.
3. Linux only (native Docker Engine): `docker inspect spec2test-input-processor --format '{{.Config.User}}'` prints your `uid:gid`; after processing a file, `ls -ln <data folder>/<project>/cache` shows your uid, and `<data folder>/.hf-cache` exists. If the folder held root-owned files from an earlier run, the output panel shows "Giving you back the files…" once.

## Gherkin-Generator installer

1. Open an empty folder with a project created. Click the **feature** button in the header. *Expect:* a picker with Copilot, Claude Code and Codex; choose all three.
2. *Expect:* `.github/agents/*.agent.md`, `.vscode/mcp.json`, `.claude/skills/gherkin-generator/SKILL.md`, `.claude/agents/web-crawler.md`, `.mcp.json`, `.agents/skills/gherkin-generator/SKILL.md` and `.codex/config.toml` exist; every config names `http://localhost:8003/mcp` with the project header, and `.codex/config.toml` has one `spec2test` block.
3. Run it again. *Expect:* "0 file(s) written". Edit one agent file and run again: you are asked Overwrite / Keep mine.
4. Create a second project and switch to it in the sidebar. *Expect:* the header changes in all three configs without any dialog.
5. Copilot: start the servers from `.vscode/mcp.json` and list tools of `input-processor`. Claude Code: `claude mcp list` shows the three servers. Codex: trust the folder and check `/mcp`.
6. Open a different folder for the first time. *Expect:* a notification offering to add the agent; *Never for this project* stops it from coming back.

## Known limits to keep in mind while testing

- Reprocess redoes the model calls of the final summary; a PDF or Markdown's
  *pre-processed* file (image descriptions) is reused while its content is unchanged.
- The extension no longer needs the repository: images come from the registry (or a local `:dev` tag), keys from the OS keychain.

## Staged processing (single mount)

1. After updating from an older version, press **Restart** once. `~/.spec2test/projects.json` exists and lists your old projects; old results are in each project's cache folder (default `<inputs>/.spec2test/cache`).
2. Project on an **outside** folder: process a `.md` and a video larger than 1 GB.
   *Expect:* the card says `Copying <file> (1.2 GB) to the Spec2Test work area…` (instant on APFS, a percentage elsewhere); afterwards `~/.spec2test/<project>/inputs` is empty, the result is in `<inputs>/.spec2test/cache`, and your original is untouched.
3. Press **Process** again on the same file. *Expect:* it finishes at once as cached, with no copy.
4. Delete `~/.spec2test/<project>` and reopen the sidebar. *Expect:* `ls ~/.spec2test/<project>/cache` is rebuilt, and the agent's `get_processed_content` still returns the content.
5. Rename a processed input in Finder and process it. *Expect:* no model calls; the cache entry is re-keyed in the project cache and the old name is gone.
6. Make the cache folder read-only (`chmod -w`) and process a small file. *Expect:* an error saying the result could not be copied and will be retried; after `chmod +w` the result appears in the project cache on the next refresh.
7. Project without an outside folder (default): works as before, nothing is staged or copied.
