# Consolidated epics document
_This document is generated automatically from the epics in the configured path._

**Last updated:** 2026-09-29 14:35

## Table of contents

- [EPIC-1: Automated Test-Scenario Input Processing](#epic-1-automated-test-scenario-input-processing)
- [EPIC-2: Automated Web Crawling and Login Capture](#epic-2-automated-web-crawling-and-login-capture)
- [EPIC-3: Scoped Filesystem Access via MCP](#epic-3-scoped-filesystem-access-via-mcp)
- [EPIC-4: Project Provisioning for Docker Compose](#epic-4-project-provisioning-for-docker-compose)
- [EPIC-5: Gherkin Suite Maintainability Analysis](#epic-5-gherkin-suite-maintainability-analysis)
- [EPIC-6: Gherkin Generation Orchestration](#epic-6-gherkin-generation-orchestration)

---

<a id="epic-1-automated-test-scenario-input-processing"></a>
# EPIC-1: Automated Test-Scenario Input Processing

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** High

## Overview

Converts raw input files supplied per project — browser-session video
recordings (`.mp4`), PDFs, Markdown, and plain text — into cached, structured
analysis content that downstream tooling uses to generate automated test
scenarios. Exposed as the `input-processor` MCP server: files are processed
once and reused from cache until they change, each project is isolated with
its own runtime, and the LLM provider/model and video-analysis strategy are
resolved per project rather than from the environment. This capability is
foundational to the product: every other Spec2Test capability that turns
recordings and documents into test scenarios depends on it.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-input-processor-2026-09-29` (including its addendum on content
extraction and summarization) and validated by the epic owner; it is not new
work.

## Feature Index

- [FEAT-1-1: Process input files into cached analysis content](#feat-1-1-process-input-files-into-cached-analysis-content)
- [FEAT-1-2: List and retrieve processed file content](#feat-1-2-list-and-retrieve-processed-file-content)
- [FEAT-1-3: Isolate work per project workspace](#feat-1-3-isolate-work-per-project-workspace)
- [FEAT-1-4: Resolve LLM provider and video-analysis strategy per project](#feat-1-4-resolve-llm-provider-and-video-analysis-strategy-per-project)
- [FEAT-1-5: Extract and summarize document content per format](#feat-1-5-extract-and-summarize-document-content-per-format)
- [FEAT-1-6: Load and render prompt templates](#feat-1-6-load-and-render-prompt-templates)

## Dependencies

None known.

## References

- Code: spec2test: [input-processor/src/main.py](../../../input-processor/src/main.py)
- Audit: [audit-input-processor-2026-09-29](../../tasks/audits/audit-input-processor-2026-09-29.md)
- Domain model: [domain-model.md](../domain-model.md)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result.

---

<a id="feat-1-1-process-input-files-into-cached-analysis-content"></a>
## FEAT-1-1: Process input files into cached analysis content

**Source:** spec2test: [input-processor/src/processing_service.py#L159-L239](../../../input-processor/src/processing_service.py) ProcessingService.process_all; spec2test: [input-processor/src/cache/reconcile.py#L76-L136](../../../input-processor/src/cache/reconcile.py) CacheReconciler.plan/apply

**Priority:** High

**Status:** Completed

**Owner:** @bperez

**Description:** Processes every supported input file for the active project, reusing cached results for unchanged files, reprocessing changed ones while archiving the previous version, re-keying renamed files without a model call, and reporting files whose source disappeared as orphaned without losing their cached content. Handler failures are reported with their cause instead of crashing the run.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-1-1-1 | Unchanged file is reused from cache | An input file whose content digest has not changed since the last run is served from cache without reprocessing | Completed | spec2test: [processing_service.py#L159-L175](../../../input-processor/src/processing_service.py) ProcessingService.process_all; spec2test: input-processor/tests/test_processing_service.py test_an_unchanged_file_is_reused |
| ESC-1-1-2 | Modified file is reprocessed and archived | An input file whose content changed is reprocessed and the previous cached version is archived | Completed | spec2test: [cache/reconcile.py#L99-L136](../../../input-processor/src/cache/reconcile.py) CacheReconciler.apply; spec2test: input-processor/tests/test_processing_service.py test_a_modified_file_is_reprocessed_and_the_old_version_archived |
| ESC-1-1-3 | Renamed file is re-keyed without reprocessing | A renamed input file with unchanged content is re-keyed to its new name without any model call | Completed | spec2test: [cache/reconcile.py#L76-L97](../../../input-processor/src/cache/reconcile.py) CacheReconciler.plan; spec2test: input-processor/tests/test_processing_service.py test_a_renamed_file_is_rekeyed_without_reprocessing |
| ESC-1-1-4 | Deleted source file is reported as orphaned | An input file whose source disappeared from the input folder is reported as orphaned while its cached content stays readable | Completed | spec2test: [processing_service.py#L93-L112](../../../input-processor/src/processing_service.py) ProcessingReport; spec2test: input-processor/tests/test_processing_service.py test_a_deleted_file_is_reported_as_orphaned |
| ESC-1-1-5 | A handler failure is reported without crashing the run | When a format handler fails for one file, the run continues and the failure is reported with its cause | Completed | spec2test: [processing_service.py#L214-L245](../../../input-processor/src/processing_service.py) ProcessingService._process; spec2test: input-processor/tests/test_processing_service.py test_a_failing_handler_is_reported_with_its_cause |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given an input file whose content has not changed since the last run, when `process_files` runs, then the file is reused from cache without reprocessing.
- [x] Given an input file whose content changed, when `process_files` runs, then the file is reprocessed and its previous cached version is archived.
- [x] Given an input file whose source disappeared from the input folder, when `process_files` runs, then it is reported as orphaned and its cached content stays readable.

### Technical Notes

Implemented by `ProcessingService.process_all`/`_process`, backed by `CacheReconciler` for cache planning and application; see `audit-input-processor-2026-09-29` Q1 and Q7 for the full call path.

### Testing Notes

Covered by `input-processor/tests/test_processing_service.py` and `input-processor/tests/test_cache.py`; see the audit's Q1 table for the complete list of cases.

<a id="feat-1-2-list-and-retrieve-processed-file-content"></a>
## FEAT-1-2: List and retrieve processed file content

**Source:** spec2test: [input-processor/src/main.py#L163-L269](../../../input-processor/src/main.py) list_processed_files/get_processed_content/get_all_processed_content

**Priority:** High

**Status:** Completed

**Owner:** @bperez

**Description:** Lets a client discover which files have cached content and retrieve the complete analysis for one file or for every file in a single call, reporting a clear error when the requested file cannot be identified.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-1-2-1 | List processed files with identifiers | Every file with cached content is listed with its name, digest, and processing timestamp | Completed | spec2test: [main.py#L163-L191](../../../input-processor/src/main.py) list_processed_files; spec2test: input-processor/tests/test_tools.py test_list_processed_files_lists_names_and_digests |
| ESC-1-2-2 | Retrieve content of a single processed file by name | The complete analysis of one processed file is returned given its name | Completed | spec2test: [main.py#L195-L232](../../../input-processor/src/main.py) get_processed_content; spec2test: input-processor/tests/test_tools.py test_get_processed_content_by_name |
| ESC-1-2-3 | Retrieve content of all processed files at once | The complete analysis of every processed file is returned in a single call | Completed | spec2test: [main.py#L236-L269](../../../input-processor/src/main.py) get_all_processed_content; spec2test: input-processor/tests/test_tools.py test_get_all_processed_content_returns_every_file |
| ESC-1-2-4 | A missing or ambiguous key is explained | A request without a file name or hash, or with an unknown or ambiguous one, returns a clear explanatory error | Completed | spec2test: [main.py#L195-L219](../../../input-processor/src/main.py) get_processed_content; spec2test: input-processor/tests/test_tools.py test_get_processed_content_requires_a_key |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a project with cached content, when `list_processed_files` is called, then every processed file is listed with its name, digest, and processing timestamp.
- [x] Given a valid file name, when `get_processed_content` is called, then the complete analysis for that file is returned.
- [x] Given no file name or hash is provided, when `get_processed_content` is called, then a clear error is returned.

### Technical Notes

`file_hash` on `get_processed_content` is documented as deprecated in favor of `file_name`; see `audit-input-processor-2026-09-29` Q2.

### Testing Notes

Covered by `input-processor/tests/test_tools.py`.

<a id="feat-1-3-isolate-work-per-project-workspace"></a>
## FEAT-1-3: Isolate work per project workspace

**Source:** spec2test: [input-processor/src/projects/headers.py](../../../input-processor/src/projects/headers.py); spec2test: [input-processor/src/projects/runtime.py#L167-L197](../../../input-processor/src/projects/runtime.py) RuntimePool

**Priority:** High

**Status:** Completed

**Owner:** @bperez

**Description:** Resolves the active project for each request from the `X-Spec2Test-Project` header, giving every project its own runtime and lock so one editor workspace's activity never disturbs another's, and refusing duplicate or invalid project names.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-1-3-1 | Active project is resolved from the request header | The project named by the `X-Spec2Test-Project` header is used to scope the request | Completed | spec2test: [main.py#L96-L112](../../../input-processor/src/main.py) current_project; spec2test: input-processor/tests/test_tools.py test_current_project_reports_the_active_project |
| ESC-1-3-2 | Each project has its own runtime and lock | Two different projects operate independently, each with its own runtime and lock | Completed | spec2test: [projects/runtime.py#L167-L197](../../../input-processor/src/projects/runtime.py) RuntimePool; spec2test: input-processor/tests/test_projects.py test_each_project_gets_its_own_runtime_and_lock |
| ESC-1-3-3 | Duplicate or invalid project name is refused | A project registration with a duplicate or invalid name is rejected | Completed | spec2test: [projects/registry.py](../../../input-processor/src/projects/registry.py) ProjectRegistry; spec2test: input-processor/tests/test_projects.py test_duplicate_project_names_are_refused |
| ESC-1-3-4 | A missing project header is explained | A request without the project header returns a clear explanatory error | Completed | spec2test: [projects/headers.py](../../../input-processor/src/projects/headers.py) project_name_from_headers; spec2test: input-processor/tests/test_tools.py test_a_missing_header_is_explained |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a request carrying the `X-Spec2Test-Project` header, when any tool is called, then the active project is resolved from that header.
- [x] Given two different projects, when each is used concurrently, then each has its own runtime and lock.
- [x] Given a duplicate or invalid project name, when it is registered, then it is refused.

### Technical Notes

No user- or role-based authorization was found within the analyzed scope; isolation is per project only. See `audit-input-processor-2026-09-29` Q4 and the domain model's gaps section.

### Testing Notes

Covered by `input-processor/tests/test_projects.py` and `input-processor/tests/test_tools.py`.

<a id="feat-1-4-resolve-llm-provider-and-video-analysis-strategy-per-project"></a>
## FEAT-1-4: Resolve LLM provider and video-analysis strategy per project

**Source:** spec2test: [input-processor/src/providers/registry.py](../../../input-processor/src/providers/registry.py) ProviderRegistry; spec2test: [input-processor/src/analysis/video/base.py](../../../input-processor/src/analysis/video/base.py) VideoAnalyzer

**Priority:** High

**Status:** Completed

**Owner:** @bperez

**Description:** Resolves which LLM provider, model, and video-analysis strategy to use from each project's own configuration rather than from environment variables, validating the provider catalog and falling back to whole-file analysis when splitting a long video fails.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-1-4-1 | Provider/model choice comes from project configuration | The LLM provider and model used for a project come from its configuration, never from environment variables | Completed | spec2test: [settings.py#L67-L87](../../../input-processor/src/settings.py) Settings.from_env; spec2test: input-processor/tests/test_settings.py test_llm_choices_are_not_read_from_the_environment |
| ESC-1-4-2 | Video analyzer is selected by declared provider capability | The video-analysis strategy used is the one matching the configured provider's declared capability | Completed | spec2test: [analysis/video/base.py#L13-L24](../../../input-processor/src/analysis/video/base.py) VideoAnalyzer; spec2test: input-processor/tests/test_video.py test_factory_selects_by_capability |
| ESC-1-4-3 | A long video is split by duration with a fallback | A video is split by duration when it is too long; if the split fails, the whole file is analyzed instead | Completed | spec2test: input-processor/src/analysis/video/segmenter.py VideoSegmenter; spec2test: input-processor/tests/test_video_analyzers.py test_a_long_video_is_split_by_duration; spec2test: input-processor/tests/test_video_analyzers.py test_a_failing_split_falls_back_to_the_whole_video |
| ESC-1-4-4 | A malformed provider catalog is rejected | A provider catalog file that is invalid JSON, missing the providers list, or missing required keys is rejected | Completed | spec2test: [providers/registry.py](../../../input-processor/src/providers/registry.py) ProviderRegistry; spec2test: input-processor/tests/test_providers.py test_catalog_reports_invalid_json |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a project's configuration, when a provider and model are resolved, then the choice comes from `projects.json` and not from environment variables.
- [x] Given a long video and a provider capability of `video_inline`, when the video is analyzed, then it is split by duration, falling back to whole-file analysis if the split fails.
- [x] Given an invalid provider catalog file, when the registry loads it, then it is rejected.

### Technical Notes

The exact multiplicity between `VideoAnalyzer` and declared provider capability was not fully confirmed at the code level; see the domain model's gaps section (`VideoAnalyzer selection multiplicity`).

### Testing Notes

Covered by `input-processor/tests/test_settings.py`, `input-processor/tests/test_video.py`, `input-processor/tests/test_video_analyzers.py`, and `input-processor/tests/test_providers.py`.

<a id="feat-1-5-extract-and-summarize-document-content-per-format"></a>
## FEAT-1-5: Extract and summarize document content per format

**Source:** spec2test: [analysis/document_summarizer.py](../../../input-processor/src/analysis/document_summarizer.py); spec2test: [analysis/image_describer.py](../../../input-processor/src/analysis/image_describer.py); spec2test: [preprocessing/pdf_to_markdown.py](../../../input-processor/src/preprocessing/pdf_to_markdown.py); spec2test: [preprocessing/markdown_images.py](../../../input-processor/src/preprocessing/markdown_images.py); spec2test: [handlers/registry.py](../../../input-processor/src/handlers/registry.py)

**Priority:** High

**Status:** Completed

**Owner:** @bperez

**Description:** Turns each supported input format into the structured content returned by `get_processed_content`: Markdown and PDF are summarized, optionally enriching or converting embedded images to descriptions first; plain text is summarized directly; and every registered handler must declare valid, non-duplicate extensions.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-1-5-1 | A Markdown file is summarized, enriching local images when available | With an image enricher configured, local image references are described before summarizing; without one, the raw file is read | Completed | spec2test: [handlers/markdown_handler.py](../../../input-processor/src/handlers/markdown_handler.py) MarkdownHandler.handle; spec2test: input-processor/tests/test_handlers.py test_markdown_handler_uses_the_enricher_when_available |
| ESC-1-5-2 | A PDF is converted to enriched Markdown or its plain text is extracted | With a converter configured, the PDF becomes Markdown with image descriptions injected; without one, its plain text layer is extracted | Completed | spec2test: [handlers/pdf_handler.py](../../../input-processor/src/handlers/pdf_handler.py) PdfHandler.handle; spec2test: input-processor/tests/test_handlers.py test_pdf_handler_uses_the_converter |
| ESC-1-5-3 | A plain text file is summarized directly | The file's text is passed straight to the summarizer | Completed | spec2test: [handlers/text_handler.py](../../../input-processor/src/handlers/text_handler.py) TextHandler.handle; spec2test: input-processor/tests/test_handlers.py test_text_handler_summarises_the_file |
| ESC-1-5-4 | Empty or unreadable content yields a clear message instead of a model call | An empty PDF, text, or Markdown file returns an explanatory message and never reaches the summarizer | Completed | spec2test: [analysis/document_summarizer.py#L26-L32](../../../input-processor/src/analysis/document_summarizer.py) DocumentSummarizer.summarize; spec2test: input-processor/tests/test_handlers.py test_summarizer_rejects_empty_content |
| ESC-1-5-5 | Image enrichment survives a missing file or a failing description | A missing local image keeps the original Markdown reference; a failing image description does not abort enrichment of the rest | Completed | spec2test: [preprocessing/markdown_images.py](../../../input-processor/src/preprocessing/markdown_images.py) MarkdownImageEnricher; spec2test: input-processor/tests/test_handlers.py test_markdown_enricher_keeps_the_original_when_a_file_is_missing |
| ESC-1-5-6 | A handler with no extensions, or a duplicate extension, is refused | Registering a handler without declared extensions, or for an extension another handler already owns, is rejected | Completed | spec2test: [handlers/registry.py](../../../input-processor/src/handlers/registry.py) HandlerRegistry.register; spec2test: input-processor/tests/test_handlers.py test_handlers_must_declare_extensions |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a Markdown file and a configured image enricher, when it is processed, then local image references are described before the file is summarized.
- [x] Given a PDF and a configured converter, when it is processed, then it becomes Markdown with image descriptions injected; without a converter, its plain text layer is used.
- [x] Given an empty document, when it is processed, then a clear message is returned without any model call.
- [x] Given a missing image file or a failing image description during Markdown enrichment, when enrichment runs, then the rest of the document is still enriched.

### Technical Notes

See `audit-input-processor-2026-09-29`, Addendum: Content Extraction and Summarization.

### Testing Notes

Covered by `input-processor/tests/test_handlers.py` (18 cases across handler, summarizer, image-describer, enricher, and registry behavior).

<a id="feat-1-6-load-and-render-prompt-templates"></a>
## FEAT-1-6: Load and render prompt templates

**Source:** spec2test: [prompts/__init__.py](../../../input-processor/src/prompts/__init__.py)

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Loads named prompt templates from `prompts/<name>.md` files, caching each after its first load, rendering `{placeholder}` values, and failing clearly (listing every available prompt) when an unknown name is requested.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-1-6-1 | An unknown prompt name fails, listing the available ones | Requesting a prompt that does not exist on disk raises an error naming every prompt that does | Completed | spec2test: [prompts/__init__.py](../../../input-processor/src/prompts/__init__.py) load; spec2test: input-processor/tests/test_prompts.py test_an_unknown_prompt_lists_the_available_ones |
| ESC-1-6-2 | Every prompt referenced by the code exists on disk | The set of prompt names the code loads matches the `.md` files actually present | Completed | spec2test: [prompts/__init__.py](../../../input-processor/src/prompts/__init__.py); spec2test: input-processor/tests/test_prompts.py test_every_prompt_used_by_the_code_exists |
| ESC-1-6-3 | A prompt template is loaded once and reused | Repeated loads of the same prompt name return the cached content instead of re-reading the file | Completed | spec2test: [prompts/__init__.py](../../../input-processor/src/prompts/__init__.py) load; spec2test: input-processor/tests/test_prompts.py test_prompts_are_loaded_once |
| ESC-1-6-4 | Templates render their placeholder values | Rendering a prompt substitutes its named `{placeholder}` values | Completed | spec2test: [prompts/__init__.py](../../../input-processor/src/prompts/__init__.py) render; spec2test: input-processor/tests/test_prompts.py test_templates_render_their_placeholders |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given an unknown prompt name, when it is loaded, then the error lists every available prompt name.
- [x] Given the prompts used by the code, when compared to the files on disk, then every referenced prompt exists.
- [x] Given a prompt is loaded twice, when the second load happens, then the cached content is returned without re-reading the file.
- [x] Given a template with placeholders, when it is rendered, then its named values are substituted.

### Technical Notes

See `audit-input-processor-2026-09-29`, Addendum: Content Extraction and Summarization.

### Testing Notes

Covered by `input-processor/tests/test_prompts.py`.

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-1-1 | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| FEAT-1-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-1-3 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-1-4 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-1-5 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| FEAT-1-6 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| **Total** | **27** | 0 | 0 | 0 | 0 | 0 | **27** | 0 | 0 |


## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `input-processor` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |
| 29/09/2026 | @bperez | Added FEAT-1-5 and FEAT-1-6 from the `input-processor` audit addendum (content extraction and summarization). Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |

---

<a id="epic-2-automated-web-crawling-and-login-capture"></a>
# EPIC-2: Automated Web Crawling and Login Capture

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Medium

## Overview

Crawls a target web application to extract structured page content — links,
interactive elements (buttons, inputs) with XPath selectors, and Markdown
content — for use in generating automated test scenarios, with an optional
authenticated crawl that replays a previously recorded login action sequence.
Exposed as the `web-crawler` MCP server (`web_crawl` tool) plus a standalone
CLI (`capture_auth.py`) that records a real login session for later replay.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-web-crawler-2026-09-29`; it is not new work. No automated
tests exist for this module within the analyzed scope, so scenario
confirmation relies on direct code reading rather than test evidence; this
limitation is recorded in the domain model's gaps section.

## Feature Index

- [FEAT-2-1: Crawl a web application and extract structured content](#feat-2-1-crawl-a-web-application-and-extract-structured-content)
- [FEAT-2-2: Authenticate before crawling using a recorded action sequence](#feat-2-2-authenticate-before-crawling-using-a-recorded-action-sequence)

## Dependencies

None known.

## References

- Code: spec2test: [web-crawler/src/main.py](../../../web-crawler/src/main.py)
- Audit: [audit-web-crawler-2026-09-29](../../tasks/audits/audit-web-crawler-2026-09-29.md)
- Domain model: [domain-model.md](../domain-model.md)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result.

---

<a id="feat-2-1-crawl-a-web-application-and-extract-structured-content"></a>
## FEAT-2-1: Crawl a web application and extract structured content

**Source:** spec2test: [web-crawler/src/main.py#L10-L38](../../../web-crawler/src/main.py) web_crawl; spec2test: [web-crawler/src/crawler/web_crawler.py#L293-L545](../../../web-crawler/src/crawler/web_crawler.py) web_crawler

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Crawls a target URL breadth-first (default) or depth-first, up to a configurable depth and page limit, extracting links, interactive elements, and XPath selectors, and converting page content to Markdown; local host URLs are rewritten for Docker compatibility.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-2-1-1 | Crawl a site breadth-first up to a configured depth and page limit | By default, the crawl explores breadth-first up to `max_depth` levels and `max_pages` pages | Completed | spec2test: [main.py#L10-L23](../../../web-crawler/src/main.py) web_crawl; spec2test: [web_crawler.py#L239-L290](../../../web-crawler/src/crawler/web_crawler.py) crawl_pages |
| ESC-2-1-2 | Crawl a site depth-first when requested | When `use_dfs` is true, the crawl explores depth-first into the site hierarchy instead | Completed | spec2test: [main.py#L10-L23](../../../web-crawler/src/main.py) web_crawl; spec2test: [web_crawler.py#L239-L290](../../../web-crawler/src/crawler/web_crawler.py) crawl_pages |
| ESC-2-1-3 | Extract links, interactive elements, and Markdown content | The crawl result includes discovered links, buttons and inputs with XPath selectors, and the page content as Markdown | Completed | spec2test: [web_crawler.py#L220-L236](../../../web-crawler/src/crawler/web_crawler.py) extract_internal_links; spec2test: [web_crawler.py#L87-L120](../../../web-crawler/src/crawler/web_crawler.py) get_xpath |
| ESC-2-1-4 | Local host URLs are rewritten for Docker compatibility | A `localhost`, `127.0.0.1`, or `0.0.0.0` host in the crawl URL is rewritten to `host.docker.internal` when running inside a Docker container | Completed | spec2test: [web_crawler.py#L17-L39](../../../web-crawler/src/crawler/web_crawler.py) is_running_in_docker/canonicalize_url |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a target URL and default options, when `web_crawl` runs, then the site is explored breadth-first up to `max_depth` and `max_pages`.
- [x] Given `use_dfs` is set to true, when `web_crawl` runs, then the site is explored depth-first instead.
- [x] Given a crawled page, when the result is returned, then it includes links, interactive elements with XPath selectors, and Markdown content.
- [x] Given the crawler is running inside a Docker container, when a local host URL is used, then it is rewritten to `host.docker.internal`.

### Technical Notes

No automated tests exist for this feature within the analyzed scope; see `audit-web-crawler-2026-09-29` Q1.

### Testing Notes

Not available: no test files were found for this module (`audit-web-crawler-2026-09-29` Q1).

<a id="feat-2-2-authenticate-before-crawling-using-a-recorded-action-sequence"></a>
## FEAT-2-2: Authenticate before crawling using a recorded action sequence

**Source:** spec2test: [web-crawler/capture_auth.py](../../../web-crawler/capture_auth.py); spec2test: [web-crawler/src/crawler/web_crawler.py#L49-L85](../../../web-crawler/src/crawler/web_crawler.py) split_actions_by_navigation

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Lets an operator record a real login session (clicks, typing, submissions) as a replayable JSON action sequence, then replays it in stages bounded by page navigations before a crawl, so the crawl starts already authenticated.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-2-2-1 | Recorded auth actions are replayed in stages bounded by navigation | Recorded actions are grouped into stages by navigation timestamp so a multi-page login flow replays correctly across page transitions | Completed | spec2test: [web_crawler.py#L49-L85](../../../web-crawler/src/crawler/web_crawler.py) split_actions_by_navigation |
| ESC-2-2-2 | Crawling proceeds authenticated when auth replay succeeds | When every auth replay stage succeeds, the crawl proceeds using the authenticated session | Completed | spec2test: [web_crawler.py#L293-L412](../../../web-crawler/src/crawler/web_crawler.py) web_crawler |
| ESC-2-2-3 | Record a login's clicks, typing, and submissions into a replayable JSON file | Operator interactions in a real browser are captured and saved as a JSON file usable by `web_crawl` | Completed | spec2test: [capture_auth.py#L177-L336](../../../web-crawler/capture_auth.py) capture_auth_actions |
| ESC-2-2-4 | Passwords are masked in the recorded action log | A `fill` action on a password input is shown as `****` in the console log and summary instead of its real value | Completed | spec2test: [capture_auth.py#L177-L336](../../../web-crawler/capture_auth.py) capture_auth_actions |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a recorded auth actions file with navigations, when it is replayed, then actions are grouped into stages bounded by those navigations.
- [x] Given every auth replay stage succeeds, when the crawl continues, then it proceeds using the authenticated session.
- [x] Given an operator logs in inside the recorder browser, when the session ends, then the recorded actions are saved as a replayable JSON file.
- [x] Given a recorded `fill` action on a password field, when it is logged or summarized, then its value is shown as `****`.

### Technical Notes

The recorded value itself is still written unmasked to the output JSON file (only console output is masked); see `audit-web-crawler-2026-09-29` Q3. No automated tests exist for this feature within the analyzed scope.

### Testing Notes

Not available: no test files were found for this module (`audit-web-crawler-2026-09-29` Q1).

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-2-1 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-2-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| **Total** | **8** | 0 | 0 | 0 | 0 | 0 | **8** | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `web-crawler` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |

---

<a id="epic-3-scoped-filesystem-access-via-mcp"></a>
# EPIC-3: Scoped Filesystem Access via MCP

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Medium

## Overview

Exposes read, write, search, and metadata operations over a filesystem as MCP
tools, with every operation confined to a set of allowed directories
configured at server startup. This is the only audited module with a real
access-control boundary: paths outside the allowed directories, including
resolved symlink targets, are rejected.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-filesystem-mcp-2026-09-29`; it is not new work. No automated
tests exist for this module within the analyzed scope, so scenario
confirmation relies on direct code reading rather than test evidence; this
limitation is recorded in the domain model's gaps section.

## Feature Index

- [FEAT-3-1: Confine every operation to allowed directories](#feat-3-1-confine-every-operation-to-allowed-directories)
- [FEAT-3-2: Read, write, and edit files](#feat-3-2-read-write-and-edit-files)
- [FEAT-3-3: Browse, search, and inspect the filesystem](#feat-3-3-browse-search-and-inspect-the-filesystem)

## Dependencies

None known.

## References

- Code: spec2test: [filesystem-mcp/index.ts](../../../filesystem-mcp/index.ts)
- Audit: [audit-filesystem-mcp-2026-09-29](../../tasks/audits/audit-filesystem-mcp-2026-09-29.md)
- Domain model: [domain-model.md](../domain-model.md)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result.

---

<a id="feat-3-1-confine-every-operation-to-allowed-directories"></a>
## FEAT-3-1: Confine every operation to allowed directories

**Source:** spec2test: [filesystem-mcp/index.ts#L53-L94](../../../filesystem-mcp/index.ts) validatePath

**Priority:** High

**Status:** Completed

**Owner:** @bperez

**Description:** Rejects any requested path that resolves outside the directories configured at server startup, including resolved symlink targets, and checks the parent directory for paths that do not yet exist (for example, a new file to be created).

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-3-1-1 | A path outside the allowed directories is rejected | Any tool call with a resolved path outside the configured allowed directories fails with an access-denied error | Completed | spec2test: [index.ts#L53-L66](../../../filesystem-mcp/index.ts) validatePath |
| ESC-3-1-2 | A symlink pointing outside the allowed directories is rejected | When a path resolves to a symlink, its real target is also checked against the allowed directories | Completed | spec2test: [index.ts#L68-L77](../../../filesystem-mcp/index.ts) validatePath |
| ESC-3-1-3 | The allowed directories can be listed | A client can retrieve the list of directories this server instance is permitted to access | Completed | spec2test: [index.ts#L423-L429](../../../filesystem-mcp/index.ts) list_allowed_directories |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a path outside every allowed directory, when any tool is called with it, then the call fails with an access-denied error.
- [x] Given a path that resolves to a symlink whose target is outside the allowed directories, when it is used, then the call fails.
- [x] Given a client calls `list_allowed_directories`, when the call completes, then the configured allowed directories are returned.

### Technical Notes

No automated tests exist for this feature within the analyzed scope; see `audit-filesystem-mcp-2026-09-29` Q1.

### Testing Notes

Not available: no test files were found for this module (`audit-filesystem-mcp-2026-09-29` Q1).

<a id="feat-3-2-read-write-and-edit-files"></a>
## FEAT-3-2: Read, write, and edit files

**Source:** spec2test: [filesystem-mcp/index.ts#L254-L330](../../../filesystem-mcp/index.ts) applyFileEdits

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Reads one or many files, creates or overwrites a file, and applies exact-text line edits to a file with an optional dry-run preview returned as a git-style diff.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-3-2-1 | Read a single file's complete contents | A file's contents are returned given its path | Completed | spec2test: [index.ts#L459-L467](../../../filesystem-mcp/index.ts) read_file |
| ESC-3-2-2 | Read multiple files in one call without one failure stopping the batch | Every requested file is read; a failed individual read is reported without aborting the others | Completed | spec2test: [index.ts#L469-L487](../../../filesystem-mcp/index.ts) read_multiple_files |
| ESC-3-2-3 | Create or overwrite a file | A file is created, or fully overwritten if it already exists | Completed | spec2test: [index.ts#L489-L498](../../../filesystem-mcp/index.ts) write_file |
| ESC-3-2-4 | Preview an edit as a diff without writing it | When `dryRun` is set, the edit is not applied and a git-style diff of the would-be change is returned instead | Completed | spec2test: [index.ts#L254-L330](../../../filesystem-mcp/index.ts) applyFileEdits |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a valid path, when `read_file` is called, then the file's complete contents are returned.
- [x] Given several paths where one is unreadable, when `read_multiple_files` is called, then the readable files are still returned and the failure is reported per path.
- [x] Given `write_file` is called on an existing file, when it completes, then the file is fully overwritten with the new content.
- [x] Given `edit_file` is called with `dryRun` true, when it completes, then no write occurs and a diff of the intended change is returned.

### Technical Notes

No automated tests exist for this feature within the analyzed scope; see `audit-filesystem-mcp-2026-09-29` Q1.

### Testing Notes

Not available: no test files were found for this module (`audit-filesystem-mcp-2026-09-29` Q1).

<a id="feat-3-3-browse-search-and-inspect-the-filesystem"></a>
## FEAT-3-3: Browse, search, and inspect the filesystem

**Source:** spec2test: [filesystem-mcp/index.ts#L544-L564](../../../filesystem-mcp/index.ts) buildTree; spec2test: [filesystem-mcp/index.ts#L188-L232](../../../filesystem-mcp/index.ts) searchFiles

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Lists a directory's entries, returns a recursive JSON tree, searches recursively for files or directories by a case-insensitive partial-name pattern, retrieves file/directory metadata, moves or renames files and directories, and creates directories (including nested ones).

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-3-3-1 | List a directory's immediate entries | Entries are returned marked `[FILE]` or `[DIR]` | Completed | spec2test: [index.ts#L523-L536](../../../filesystem-mcp/index.ts) list_directory |
| ESC-3-3-2 | Return a recursive directory tree | A JSON tree of the directory is returned, with `children` present only for directories | Completed | spec2test: [index.ts#L544-L564](../../../filesystem-mcp/index.ts) buildTree |
| ESC-3-3-3 | Recursively search for files or directories by name | Items whose name partially matches a case-insensitive pattern are found under the given path, excluding any configured subpatterns | Completed | spec2test: [index.ts#L188-L232](../../../filesystem-mcp/index.ts) searchFiles |
| ESC-3-3-4 | Retrieve file or directory metadata | Size, timestamps, type, and permissions are returned for a given path | Completed | spec2test: [index.ts#L175-L186](../../../filesystem-mcp/index.ts) getFileStats |
| ESC-3-3-5 | Move or rename a file or directory | A file or directory is moved to a new path, or renamed within the same directory | Completed | spec2test: [index.ts#L575-L586](../../../filesystem-mcp/index.ts) move_file |
| ESC-3-3-6 | Create a directory, including nested ones | A directory (and any missing parent directories) is created; it succeeds silently if the directory already exists | Completed | spec2test: [index.ts#L512-L521](../../../filesystem-mcp/index.ts) create_directory |

### Comments

| Scenario ID | Comments |
|--------------|-------------|
| ESC-3-3-5 | Open question: the `move_file` tool description states the operation fails if the destination exists ([index.ts#L396-L403](../../../filesystem-mcp/index.ts)), but the handler calls `fs.rename` with no existence check ([index.ts#L575-L586](../../../filesystem-mcp/index.ts)), so actual overwrite behavior is platform-dependent. Is the documented failure-on-overwrite the intended behavior (requiring an explicit check), or should the description be corrected? (audit audit-filesystem-mcp-2026-09-29) |

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a directory path, when `list_directory` is called, then its immediate entries are returned marked `[FILE]` or `[DIR]`.
- [x] Given a directory path, when `directory_tree` is called, then a recursive JSON tree is returned with `children` only on directories.
- [x] Given a search pattern and a starting path, when `search_files` is called, then matching items are found recursively, excluding any configured subpatterns.
- [x] Given a path, when `get_file_info` is called, then its size, timestamps, type, and permissions are returned.
- [x] Given a source and destination path, when `move_file` is called, then the item is moved or renamed accordingly.
- [x] Given a path with missing parent directories, when `create_directory` is called, then the full path is created.

### Technical Notes

See the open question in the Comments table above regarding `move_file` overwrite behavior. No automated tests exist for this feature within the analyzed scope.

### Testing Notes

Not available: no test files were found for this module (`audit-filesystem-mcp-2026-09-29` Q1).

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-3-1 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| FEAT-3-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-3-3 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| **Total** | **13** | 0 | 0 | 0 | 0 | 0 | **13** | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `filesystem-mcp` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |

---

<a id="epic-4-project-provisioning-for-docker-compose"></a>
# EPIC-4: Project Provisioning for Docker Compose

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Medium

## Overview

Validates the host's `projects.json` and generates the Docker Compose
override that mounts each configured project's `inputs`, `preprocessed`, and
`cache` folders into the `input-processor` and `filesystem-mcp` services,
creating the output folders on the host as needed. Its own docstring states
that its container-side counterpart is `input-processor/src/projects/model.py`
(see EPIC-1): the two must agree on the project name rule and folder layout.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-scripts-2026-09-29`; it is not new work.

## Feature Index

- [FEAT-4-1: Validate project configuration](#feat-4-1-validate-project-configuration)
- [FEAT-4-2: Generate the Compose override](#feat-4-2-generate-the-compose-override)

## Dependencies

- EPIC-1: the project name rule and `inputs`/`preprocessed`/`cache` layout must stay compatible with `input-processor/src/projects/model.py`.

## References

- Code: spec2test: [scripts/sync_projects.py](../../../scripts/sync_projects.py)
- Audit: [audit-scripts-2026-09-29](../../tasks/audits/audit-scripts-2026-09-29.md)
- Domain model: [domain-model.md](../domain-model.md)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result.

---

<a id="feat-4-1-validate-project-configuration"></a>
## FEAT-4-1: Validate project configuration

**Source:** spec2test: [scripts/sync_projects.py#L71-L149](../../../scripts/sync_projects.py) load_config/check_paths

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Reads `projects.json`, resolving each project's `inputs`, `preprocessed`, and `cache` host paths, and rejects invalid or duplicate project names, malformed configuration, and missing input folders (reporting every missing folder together).

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-4-1-1 | Project paths are read from the configuration, with sensible defaults | Each project's inputs, preprocessed, and cache paths are resolved from `projects.json`, defaulting preprocessed/cache to a hidden data directory | Completed | spec2test: [sync_projects.py#L71-L126](../../../scripts/sync_projects.py) load_config/_project/_resolve; spec2test: input-processor/tests/test_sync_projects.py test_paths_are_read_from_the_configuration_file |
| ESC-4-1-2 | A missing, invalid, or malformed configuration file is reported | A missing file, invalid JSON, a non-object root, a non-object entry, or an empty projects list is reported as a configuration error | Completed | spec2test: [sync_projects.py#L71-L118](../../../scripts/sync_projects.py) load_config/_project; spec2test: input-processor/tests/test_sync_projects.py test_a_missing_configuration_file_is_reported |
| ESC-4-1-3 | An invalid or duplicate project name is refused | A project name that does not match the slug pattern, or that duplicates another project's name, is rejected | Completed | spec2test: [sync_projects.py#L41](../../../scripts/sync_projects.py), [#L101-L134](../../../scripts/sync_projects.py); spec2test: input-processor/tests/test_sync_projects.py test_invalid_names_are_refused |
| ESC-4-1-4 | Missing input folders are reported together | Every project with a missing `inputs` folder is listed in a single error, not just the first one found | Completed | spec2test: [sync_projects.py#L137-L149](../../../scripts/sync_projects.py) check_paths; spec2test: input-processor/tests/test_sync_projects.py test_missing_inputs_are_reported_together |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a valid `projects.json`, when it is loaded, then each project's paths are resolved with the documented defaults.
- [x] Given a missing or malformed `projects.json`, when it is loaded, then a configuration error is reported.
- [x] Given an invalid or duplicate project name, when the configuration is loaded, then it is rejected.
- [x] Given several projects with missing `inputs` folders, when paths are checked, then all of them are reported together.

### Technical Notes

The project name rule and folder layout must stay compatible with `input-processor/src/projects/model.py` (RULE-12); see EPIC-1.

### Testing Notes

Covered by `input-processor/tests/test_sync_projects.py`.

<a id="feat-4-2-generate-the-compose-override"></a>
## FEAT-4-2: Generate the Compose override

**Source:** spec2test: [scripts/sync_projects.py#L159-L254](../../../scripts/sync_projects.py) configured_services/render_override/main

**Priority:** Medium

**Status:** Completed

**Owner:** @bperez

**Description:** Creates the host-side output folders and writes `docker-compose.override.yaml`, mounting every configured project into only the services that both need project folders and are already declared in the base compose file, with a `--check` mode that validates and previews without writing.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-4-2-1 | The override only lists services declared in the base compose file | Services that need project folders but are not defined in the base compose file are excluded; a base file with neither service is reported as an error | Completed | spec2test: [sync_projects.py#L159-L185](../../../scripts/sync_projects.py) configured_services; spec2test: input-processor/tests/test_sync_projects.py test_services_are_read_from_the_base_compose_file |
| ESC-4-2-2 | The generated override mounts every project into both services | Each project's inputs, preprocessed, and cache paths are mounted into every service the override targets | Completed | spec2test: [sync_projects.py#L188-L205](../../../scripts/sync_projects.py) render_override; spec2test: input-processor/tests/test_sync_projects.py test_the_override_mounts_every_project_into_both_services |
| ESC-4-2-3 | Output folders are created on the host | The preprocessed and cache folders for every project are created if they do not exist | Completed | spec2test: [sync_projects.py#L152-L156](../../../scripts/sync_projects.py) create_output_folders; spec2test: input-processor/tests/test_sync_projects.py test_output_folders_are_created |
| ESC-4-2-4 | `--check` validates and previews without writing | Running with `--check` reports what would be written without creating folders or writing the override file | Completed | spec2test: [sync_projects.py#L226-L254](../../../scripts/sync_projects.py) main; spec2test: input-processor/tests/test_sync_projects.py test_check_validates_without_writing |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a base compose file missing one of the services that need project folders, when the override is generated, then only the services actually present are targeted.
- [x] Given valid, checked configuration, when the override is written, then every project is mounted into every targeted service.
- [x] Given projects whose output folders do not exist, when the override is generated (without `--check`), then those folders are created on the host.
- [x] Given `--check` is passed, when `sync_projects.py` runs, then nothing is written and the intended result is only reported.

### Technical Notes

The override never introduces a service the base compose file does not already define (RULE-13).

### Testing Notes

Covered by `input-processor/tests/test_sync_projects.py`, including `test_main_writes_the_override_and_the_folders`, `test_main_quiet_only_writes`, `test_the_committed_example_is_valid`, and `test_the_override_is_header_commentated`.

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-4-1 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-4-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| **Total** | **8** | 0 | 0 | 0 | 0 | 0 | **8** | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `scripts` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |

---

<a id="epic-5-gherkin-suite-maintainability-analysis"></a>
# EPIC-5: Gherkin Suite Maintainability Analysis

**Status:** Completed

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Low

## Overview

Computes maintainability metrics for one or more Gherkin features — per-feature
scores (SPC, OAR, BDI, ASL, combined into FMI) and a suite-level Structural
Suite Index (SSI) — exports a consolidated Excel workbook, and persists a JSON
state file so results can be accumulated incrementally across upload batches
that would otherwise exceed a single request. Implemented as a Claude Code
skill (`SKILL.md` plus `analyze_gherkin.py`), not an MCP server.

This epic documents pre-existing, already-implemented behavior discovered
through `audit-gherkin-multiple-v5-2026-09-29`; it is not new work. No
automated tests exist for this module within the analyzed scope, and its
metric-scoring internals were confirmed through their function outline and
`SKILL.md`'s formula descriptions rather than a full line-by-line read; this
limitation is recorded in the domain model's gaps section.

## Feature Index

- [FEAT-5-1: Compute Gherkin feature and suite maintainability metrics](#feat-5-1-compute-gherkin-feature-and-suite-maintainability-metrics)
- [FEAT-5-2: Consolidate results incrementally across upload batches](#feat-5-2-consolidate-results-incrementally-across-upload-batches)

## Dependencies

None known.

## References

- Code: spec2test: [.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py)
- Document: spec2test: [.claude/skills/gherkin-multiple-v5/SKILL.md](../../../.claude/skills/gherkin-multiple-v5/SKILL.md)
- Audit: [audit-gherkin-multiple-v5-2026-09-29](../../tasks/audits/audit-gherkin-multiple-v5-2026-09-29.md)
- Domain model: [domain-model.md](../domain-model.md)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result.

---

<a id="feat-5-1-compute-gherkin-feature-and-suite-maintainability-metrics"></a>
## FEAT-5-1: Compute Gherkin feature and suite maintainability metrics

**Source:** spec2test: [SKILL.md "Feature metrics" and "Suite metrics and totals sheet"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L288-L682](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py)

**Priority:** Low

**Status:** Completed

**Owner:** @bperez

**Description:** Parses one or more Gherkin inputs (files, directories, raw text, or a zip treated as one aggregated feature) and computes each feature's SPC, OAR, BDI, and ASL scores combined into an FMI, then combines every feature into a suite-level SSI, exporting a consolidated Excel workbook with one sheet per feature plus Totals and Repeated Steps.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-5-1-1 | Compute the four per-feature metrics and the combined FMI | Each analyzed feature gets SPC, OAR, BDI, and ASL scores, averaged into `FMI` | Completed | spec2test: [SKILL.md "Feature metrics"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L288-L572](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) summarize_feature/build_feature_report |
| ESC-5-1-2 | Compute the suite-level Structural Suite Index | The accumulated suite gets an `SSI`, the average of every feature's `FMI` | Completed | spec2test: [SKILL.md "Suite metrics and totals sheet"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L621-L682](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) build_suite_report |
| ESC-5-1-3 | Export a consolidated Excel workbook | The workbook has one sheet per feature plus Totals and Repeated Steps sheets | Completed | spec2test: [SKILL.md "Output contract"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L1006-L1016](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) export_xlsx |
| ESC-5-1-4 | A zip file is treated as one aggregated logical feature | Every supported file inside an uploaded zip is aggregated into a single feature keyed by the zip's filename | Completed | spec2test: [SKILL.md workflow steps 5-6](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L989-L1003](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) load_zip_as_single_feature |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a Gherkin feature, when it is analyzed, then it gets SPC, OAR, BDI, ASL, and a combined FMI.
- [x] Given an accumulated set of analyzed features, when the suite report is built, then it includes an SSI averaged from every feature's FMI.
- [x] Given the analysis completes, when an Excel output path is provided, then a workbook with one sheet per feature plus Totals and Repeated Steps is written.
- [x] Given a `.zip` file is uploaded, when it is analyzed, then all of its supported files are aggregated into one feature keyed by the zip's name.

### Technical Notes

No automated tests exist for this feature within the analyzed scope; the metric-scoring internals were confirmed through their function outline and `SKILL.md`'s formulas rather than a full line-by-line read (see `audit-gherkin-multiple-v5-2026-09-29` Q1 and Technical Evidence).

### Testing Notes

Not available: no test files were found for this module (`audit-gherkin-multiple-v5-2026-09-29` Q1).

<a id="feat-5-2-consolidate-results-incrementally-across-upload-batches"></a>
## FEAT-5-2: Consolidate results incrementally across upload batches

**Source:** spec2test: [SKILL.md "Incremental batch mode"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L1040-L1159](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py)

**Priority:** Low

**Status:** Completed

**Owner:** @bperez

**Description:** Persists analyzed features in a JSON state file so a suite that cannot be uploaded all at once can be analyzed in batches, replacing a feature already present in the state by its normalized title rather than duplicating it, and rejecting a state file from an incompatible schema version.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-5-2-1 | A feature already in the state is replaced, not duplicated | Re-analyzing a feature whose normalized title (or source filename) already exists in the state replaces the older entry | Completed | spec2test: [SKILL.md "Incremental batch mode"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L1078-L1159](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) main |
| ESC-5-2-2 | Suite totals are recomputed from the full accumulated state | Totals and Repeated Steps are recalculated from every feature in the state, not only the latest batch | Completed | spec2test: [analyze_gherkin.py#L1078-L1159](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) main |
| ESC-5-2-3 | An incompatible state file version is rejected | A JSON state file whose `version` does not match the script's expected version is rejected instead of being silently reinterpreted | Completed | spec2test: [analyze_gherkin.py#L1040-L1054](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) load_state |
| ESC-5-2-4 | A JSON state file is always produced, even for a single batch | Every run writes an updated JSON state file, so it can be reused for a later batch even when the current run is not incremental | Completed | spec2test: [SKILL.md "Incremental batch mode"](../../../.claude/skills/gherkin-multiple-v5/SKILL.md); spec2test: [analyze_gherkin.py#L1057-L1060](../../../.claude/skills/gherkin-multiple-v5/scripts/analyze_gherkin.py) save_state |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [x] Given a feature already present in the state (by normalized title or filename), when it is re-analyzed, then it replaces the older entry rather than duplicating it.
- [x] Given an accumulated state with multiple batches, when totals are computed, then they reflect every feature in the state, not only the latest batch.
- [x] Given a state file with an unsupported version, when it is loaded, then it is rejected with an explanatory error.
- [x] Given `--state-out` is provided, when the run completes, then the updated JSON state file is written regardless of batch mode.

### Technical Notes

No automated tests exist for this feature within the analyzed scope.

### Testing Notes

Not available: no test files were found for this module (`audit-gherkin-multiple-v5-2026-09-29` Q1).

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-5-1 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| FEAT-5-2 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| **Total** | **8** | 0 | 0 | 0 | 0 | 0 | **8** | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `gherkin-multiple-v5` audit. Already implemented; validated by @bperez on 29/09/2026 | analyst-requirements (Claude Sonnet 5) |

---

<a id="epic-6-gherkin-generation-orchestration"></a>
# EPIC-6: Gherkin Generation Orchestration

**Status:** Approved

**Owner:** @bperez

**Created:** 29/09/2026

**Last updated:** 29/09/2026

**Priority:** Medium

## Overview

Orchestrates input processing (EPIC-1) and web crawling (EPIC-2) into
generated `.feature` files: an orchestrator agent (`Gherkin-Generator`)
processes every available input file, delegates crawling to a restricted
subagent (`Web-Crawler`), reads existing `.feature` files to avoid
duplication, analyzes edge cases, and authors scenarios following BRIEF
quality principles, `Rule:`-based grouping, and Scenario/Scenario Outline
guidance shared with the `gherkin` skill.

**This epic's evidence is `Documented`, not `Implemented`, and its status is
therefore `Approved` rather than `Completed`.** Every other epic in this
project (`EPIC-1` through `EPIC-5`) was marked `Completed` because direct
reading of deterministic source code (Python/TypeScript) confirms what
actually executes. This epic instead documents instructions given to an
LLM-based Copilot agent: reading `Gherkin-Generator.agent.md` and
`Web-Crawler.agent.md` confirms what the agent is *instructed* to do, not
that it verifiably does so on every invocation. No tests exist, and none are
possible in the sense used for the other epics. This distinction is recorded
in the domain model's gaps section and must not be lost when this epic is
referenced elsewhere.

## Feature Index

- [FEAT-6-1: Orchestrate input processing and crawling into Gherkin scenarios](#feat-6-1-orchestrate-input-processing-and-crawling-into-gherkin-scenarios)
- [FEAT-6-2: Constrain crawling to verified, evidenced tool calls](#feat-6-2-constrain-crawling-to-verified-evidenced-tool-calls)

## Dependencies

- EPIC-1: `Gherkin-Generator` depends on the `input-processor` MCP tools (`current_project`, `process_files`, `list_processed_files`, `get_processed_content`).
- EPIC-2: `Web-Crawler` depends on the `web_crawl` MCP tool.

## References

- Document: spec2test: [.github/agents/Gherkin-Generator.agent.md](../../../.github/agents/Gherkin-Generator.agent.md)
- Document: spec2test: [.github/agents/Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md)
- Document: spec2test: [.github/skills/gherkin/SKILL.md](../../../.github/skills/gherkin/SKILL.md)
- Audit: [audit-github-agents-2026-09-29](../../tasks/audits/audit-github-agents-2026-09-29.md)
- Domain model: [domain-model.md](../domain-model.md)

When formalizing a requirement from existing code, link the evidence that
supports this epic and repeat the most specific reference in the **Source** of
each affected feature and scenario. Accepted source types:

- Document: document + section.
- Code: alias + qualified symbol + link.
- Test: alias + test path + case name + link.
- Contract: alias + specification file (OpenAPI, GraphQL, proto) + operation + link.
- Data: alias + migration or entity + link.
- History: `alias#N` of the pull request or issue + link.

Every source must be a verifiable link: a relative path from this epic in the
same repository, or a permalink to a commit and file in another repository.
Separate several sources in one cell with `;`, for example
`backend: service.py#L118 OrderService.cancel; backend: test_cancel.py#L42 test_cancel_order_after_shipping_fails; backend#214`.
No source, alone or combined, establishes `Completed`: use that configured
status only after the behavior is confirmed and the human validation required
by `workflow.human_validation_required_for_completion` is recorded; do not
infer an E2E result. For this epic specifically, no source can establish
`Completed` at all, because the sources are prompt instructions rather than
deterministic code or passing tests.

---

<a id="feat-6-1-orchestrate-input-processing-and-crawling-into-gherkin-scenarios"></a>
## FEAT-6-1: Orchestrate input processing and crawling into Gherkin scenarios

**Source:** Document: spec2test: [Gherkin-Generator.agent.md, Steps 0-5](../../../.github/agents/Gherkin-Generator.agent.md)

**Priority:** Medium

**Status:** Approved

**Owner:** @bperez

**Description:** Gathers the application URL and output directory, processes every available input file through `input-processor`, delegates crawling to `Web-Crawler`, reads existing `.feature` files to avoid duplication, analyzes edge cases, and generates `.feature` files grouped by `Rule:` with BRIEF-compliant scenarios, choosing `Scenario` vs. `Scenario Outline` per the documented decision table.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-6-1-1 | Process every available input file before generating scenarios | Every file returned by `list_processed_files` is fully analyzed, extracting user stories, workflows, business rules, and UI components, before feature generation begins | Approved | Document: spec2test: [Gherkin-Generator.agent.md Step 1](../../../.github/agents/Gherkin-Generator.agent.md) |
| ESC-6-1-2 | Avoid duplicating existing `.feature` files | Existing `.feature` files are read first, and only genuinely new scenarios are added instead of duplicating existing ones | Approved | Document: spec2test: [Gherkin-Generator.agent.md Step 3](../../../.github/agents/Gherkin-Generator.agent.md) |
| ESC-6-1-3 | Group generated scenarios by business rule using `Rule:` | Scenarios sharing a business rule are grouped under a Gherkin `Rule:` keyword rather than a comment divider | Approved | Document: spec2test: [Gherkin-Generator.agent.md Step 5.2](../../../.github/agents/Gherkin-Generator.agent.md); Document: spec2test: [SKILL.md](../../../.github/skills/gherkin/SKILL.md) |
| ESC-6-1-4 | Choose Scenario Outline only for same-structure, different-data cases | A Scenario Outline is used only when every row shares the same step structure and differs only in data; otherwise separate scenarios are used | Approved | Document: spec2test: [Gherkin-Generator.agent.md Step 5.4 decision table](../../../.github/agents/Gherkin-Generator.agent.md) |

### Comments

| Scenario ID | Comments |
|--------------|-------------|
| ESC-6-1-3 | Observation from `audit-github-agents-2026-09-29`: this authoring rule is stated in both `Gherkin-Generator.agent.md` and `.github/skills/gherkin/SKILL.md`, which is a maintenance risk (possible future drift) rather than a functional conflict. |

### Tasks

> There may be one row for each involved implementation repository.
> The `Repository` value must be one of the configurable aliases declared in
> `repositories` in `.project.yml`.

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [ ] Given input files are available, when generation starts, then every file is processed and analyzed before scenarios are written.
- [ ] Given `.feature` files already exist in the output directory, when generation runs, then only new, non-duplicate scenarios are added.
- [ ] Given scenarios share a business rule, when the feature file is written, then they are grouped under a `Rule:` keyword.
- [ ] Given a set of data variations shares the same step structure, when scenarios are authored, then a `Scenario Outline` is used instead of separate scenarios.

### Technical Notes

This feature's behavior is `Documented` (Copilot agent instructions), not `Implemented` code; see the epic overview and `audit-github-agents-2026-09-29`.

### Testing Notes

Not applicable: prompt-governed LLM behavior cannot be pinned by deterministic tests (`audit-github-agents-2026-09-29` Q1).

<a id="feat-6-2-constrain-crawling-to-verified-evidenced-tool-calls"></a>
## FEAT-6-2: Constrain crawling to verified, evidenced tool calls

**Source:** Document: spec2test: [Web-Crawler.agent.md](../../../.github/agents/Web-Crawler.agent.md)

**Priority:** Medium

**Status:** Approved

**Owner:** @bperez

**Description:** Restricts the crawling subagent to the `web_crawl` MCP tool, forbidding any non-MCP scraping fallback or simulated crawl data, and requires a structured evidence block reporting every `web_crawl` call and its outcome in every response.

### Scenarios

| Scenario ID | Scenario | Description | Status | Source |
|--------------|-----------|-------------|--------|--------|
| ESC-6-2-1 | Crawling is never simulated or guessed | A crawl result is never returned as guessed, inferred, or template-only data; at least one successful `web_crawl` call must be present | Approved | Document: spec2test: [Web-Crawler.agent.md "Mandatory MCP Usage"](../../../.github/agents/Web-Crawler.agent.md) |
| ESC-6-2-2 | Non-MCP scraping fallbacks are forbidden | `wget`, `curl`, `fetch`, browser DevTools exports, and handcrafted DOM assumptions are never used as a substitute for `web_crawl` | Approved | Document: spec2test: [Web-Crawler.agent.md "Forbidden Fallbacks"](../../../.github/agents/Web-Crawler.agent.md) |
| ESC-6-2-3 | Every response includes an MCP evidence block | Every `Web-Crawler` response opens with a block reporting the tool, calls made, last call parameters, last call status, and the error text if it failed | Approved | Document: spec2test: [Web-Crawler.agent.md "Required Evidence in Every Response"](../../../.github/agents/Web-Crawler.agent.md) |
| ESC-6-2-4 | Crawl strategy is chosen by documented BFS/DFS criteria | Breadth-first search is used for first/broad discovery; depth-first search is used for a specific deep workflow or after a prior broad crawl | Approved | Document: spec2test: [Web-Crawler.agent.md "Crawl Strategy Decision"](../../../.github/agents/Web-Crawler.agent.md) |

### Comments

| Scenario ID | Comments |
|--------------|-------------|

### Tasks

| Scenario ID | Issue | Status | Repository | Description |
|--------------|-------|--------|-------------|-------------|

### Acceptance Criteria

- [ ] Given `web_crawl` fails, when a response is returned, then it reports failure only, with no partial or guessed crawl data.
- [ ] Given a crawl is requested, when it is performed, then no non-MCP scraping tool is used as a substitute for `web_crawl`.
- [ ] Given any `Web-Crawler` response, when it is returned, then it opens with a complete MCP evidence block.
- [ ] Given the feature's crawling need, when a strategy is chosen, then it follows the documented BFS/DFS decision criteria.

### Technical Notes

This feature's behavior is `Documented` (Copilot agent instructions), not `Implemented` code; see the epic overview and `audit-github-agents-2026-09-29`. Compare with `filesystem-mcp`'s `validatePath` (EPIC-3), which is a runtime-enforced boundary, not a documented one.

### Testing Notes

Not applicable: prompt-governed LLM behavior cannot be pinned by deterministic tests (`audit-github-agents-2026-09-29` Q1).

## Progress Summary

| Feature | Total | Pending | In analysis | Approved | In development | In testing | Completed | Blocked | Rejected |
|---------|-------|---------|--------------|----------|-----------------|------------|-----------|---------|----------|
| FEAT-6-1 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| FEAT-6-2 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **8** | 0 | 0 | **8** | 0 | 0 | 0 | 0 | 0 |

## Change History

| Date | Author | Change | Agent |
|-------|-------|--------|-------|
| 29/09/2026 | @bperez | Created from the validated `github-agents` audit. Documented agent/skill behavior reviewed by @bperez on 29/09/2026; not confirmed by code execution or tests, so marked `Approved` rather than `Completed` | analyst-requirements (Claude Sonnet 5) |

---
