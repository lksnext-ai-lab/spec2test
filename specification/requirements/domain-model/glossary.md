# Domain Glossary

Use this document as the terminology source before drafting requirements,
scenarios, plans, tasks, or audits. It may start empty.

## Terms

| Preferred term | Definition | Type | Prohibited or ambiguous synonyms | Status |
|-------------------|------------|------|----------------------------------|--------|
| Project | A named workspace with its own input, cache, and provider configuration, selected per request via the `X-Spec2Test-Project` header | entity | workspace (avoid; ambiguous with editor workspace) | Confirmed |
| ProcessingReport | The outcome of processing every supported input file for a project in one run: successful results and orphaned entries | entity | — | Confirmed |
| FileResult | The per-file outcome of processing: name, format, digest, status, and error when applicable | entity | — | Confirmed |
| CacheEntry | A cached record of a previously processed source file, keyed by name and content digest | entity | — | Confirmed |
| Processing status | The enumerated outcome of processing a file: `new`, `cached`, `updated`, `renamed`, `orphaned`, `error` | status | — | Confirmed |
| Provider capability | The enumerated kind of content a configured LLM provider or model can analyze: `text`, `images`, `video_inline` | status | — | Confirmed |
| FileHandler | A component that knows how to process one input format (Markdown, PDF, text, or video) | entity | — | Confirmed |
| VideoAnalyzer | A component that analyzes video content using a specific strategy (frame sampling, inline, file-API, or metadata-only) | entity | — | Confirmed |
| ProviderRegistry | The registry of native and catalog-declared LLM providers available to a project | entity | — | Confirmed |
| Orphaned | The processing status of a cached file whose source disappeared from the input folder; its content stays readable | status | — | Confirmed |
| CrawlRequest | A request to crawl one web page or site, with a strategy, depth, page limit, and whether to authenticate first | entity | — | Confirmed |
| AuthActionsFile | A recorded, replayable JSON sequence of browser interactions (fill, click, submit) used to log in to a target site before crawling | entity | — | Confirmed |
| ReplayStage | A group of recorded auth actions bounded by a page navigation, replayed in order against its own URL | entity | — | Confirmed |
| AllowedDirectories | The set of directories a `filesystem-mcp` server instance is permitted to read, write, search, or list, resolved from its startup arguments | entity | — | Confirmed |
| FileInfo | Metadata about a file or directory: size, timestamps, type, and permissions | entity | — | Confirmed |
| TreeEntry | One node of a recursive directory tree: its name, type (file or directory), and children when it is a directory | entity | — | Confirmed |
| SyncProject | A project entry from `projects.json`, with its name and resolved host-side inputs, preprocessed, and cache paths | entity | — | Confirmed |
| ComposeOverride | The generated `docker-compose.override.yaml` that mounts every configured project's folders into the services that need them | entity | — | Confirmed |
| GherkinFeatureReport | The maintainability metrics computed for one analyzed Gherkin feature (SPC, OAR, BDI, ASL, FMI) | entity | — | Confirmed |
| SuiteReport | The averaged maintainability metrics and Structural Suite Index (SSI) for the full accumulated set of features | entity | — | Confirmed |
| GherkinState | The persisted JSON record of every analyzed feature, used to consolidate results incrementally across upload batches | entity | — | Confirmed |
| DocumentSummarizer | The component that turns extracted document text into a structured, test-generation-friendly summary via the configured LLM | entity | — | Confirmed |
| ImageDescriber | The component that produces a QA-oriented description of an image for use as alt text in enriched Markdown | entity | — | Confirmed |
| PdfToMarkdown | The component that converts a PDF's pages to Markdown, injecting a description for every embedded image | entity | — | Confirmed |
| MarkdownImageEnricher | The component that replaces local image references in Markdown with generated descriptions | entity | — | Confirmed |
| PromptTemplate | A named instruction template, backed by a `prompts/<name>.md` file, used to guide an LLM call for a specific analysis kind | entity | Prompt (kept for readability; PromptTemplate is preferred in the model) | Confirmed |
| GherkinGeneratorAgent | The Copilot agent that orchestrates input processing and web crawling into generated `.feature` files (Documented) | entity | — | Confirmed |
| WebCrawlerSubagent | The Copilot subagent restricted to the `web_crawl` MCP tool, invoked by `GherkinGeneratorAgent` (Documented) | entity | — | Confirmed |
| MCPEvidenceBlock | The mandatory summary of tool calls and outcomes that must open every `WebCrawlerSubagent` response (Documented) | entity | — | Confirmed |

## Rules

- Preferred terms are used consistently throughout the documentation.
- New terms are recorded as `Pending` until confirmed.
- An empty glossary is valid during initial installation.

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Added terms confirmed by the validated `input-processor` audit | analyst-requirements (Claude Sonnet 5) |
| 29/09/2026 | @bperez | Added terms confirmed by the validated `web-crawler` audit | analyst-requirements (Claude Sonnet 5) |
| 29/09/2026 | @bperez | Added terms confirmed by the validated `filesystem-mcp` audit | analyst-requirements (Claude Sonnet 5) |
| 29/09/2026 | @bperez | Added terms confirmed by the validated `scripts` audit | analyst-requirements (Claude Sonnet 5) |
| 29/09/2026 | @bperez | Added terms confirmed by the validated `gherkin-multiple-v5` audit | analyst-requirements (Claude Sonnet 5) |
| 29/09/2026 | @bperez | Added terms (Documented) confirmed by the validated `github-agents` audit | analyst-requirements (Claude Sonnet 5) |
| 29/09/2026 | @bperez | Added terms confirmed by the `input-processor` audit addendum (content extraction and summarization) | analyst-requirements (Claude Sonnet 5) |
