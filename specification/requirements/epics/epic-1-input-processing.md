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
