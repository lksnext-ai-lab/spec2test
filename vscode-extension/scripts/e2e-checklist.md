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

Reload VS Code, open the `spec2test` repository folder, and use a scratch copy of a
`.mp4` (a few minutes long, ideally > 12 MB so it is split), a `.pdf` with images, a `.md`
and a `.txt`. Have one API key ready (Google is the default provider).

Optionally check the backend on its own first: `python -m pytest input-processor/tests`.

## Steps

1. **Docker stopped.** Stop Docker Desktop. Open the Spec2Test icon.
   *Expect:* a banner "Docker is not running" with a **Start Docker** button and the footer
   showing "Docker off"; starting Docker turns it into "The input-processor is stopped" within about 10 s.
0. **Switching pages.** Click ⚙, switch between the four tabs, then go back with the arrow.
   *Expect:* the page never goes blank (if it ever does, it shows "Something went wrong" with **Try again**).
2. **Start.** Press **Start input-processor** (banner or footer menu). *Expect:* "Building and
   starting…" with a moving bar, then a green "Running" in the footer. The first build takes
   minutes. **Footer menu → Show logs** streams the container logs.
   *Regression to check:* with an old image already present, it must still become "Running"
   (the compose file now sets `HOST=0.0.0.0`, and Start rebuilds). If the container is up but
   silent, after ~30 s the footer must say "Not responding" and offer **Rebuild and restart**.
3. **Environment.** ⚙ → *Environment*, paste your key next to its provider, **Save**.
   *Expect:* the chip turns *Set* and a "Restart the input-processor…" bar appears;
   **Apply and restart** recreates the container and the bar disappears. `.env` now has the
   key (`grep GOOGLE_API_KEY .env`); other lines and comments are unchanged. In *Video* and
   *Advanced*, change a value: an "Unsaved changes" bar offers Save / Discard.
4. **Create a project.** **+** (or the dropdown's *New project…*) → name `demo` → *Use the default folder* (or *Choose the folder with my specs…*).
   Then open the project **⋮** menu and try *Change cache folder…* and *Open cache folder*: each acts on that one folder only.
   *Expect:* a notification while the container is recreated; `projects.json` and
   `docker-compose.override.yaml` contain `demo`; the project is selected.
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

## Known limits to keep in mind while testing

- Reprocess redoes the model calls of the final summary; a PDF or Markdown's
  *pre-processed* file (image descriptions) is reused while its content is unchanged.
- The extension needs a clone of the repository and Python 3 for `scripts/sync_projects.py`.
