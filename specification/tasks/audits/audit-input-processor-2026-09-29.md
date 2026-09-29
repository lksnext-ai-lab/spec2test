# Domain Audit: input-processor

**Date:** 2026-09-29
**Audit ID:** audit-input-processor-2026-09-29

## Scope and Tools

| Alias | Modules | CBM state | Fallback | Limitations |
|---|---|---|---|---|
| spec2test | input-processor/src, input-processor/tests | project `C-VSCode-WS-spec2Test`, generation `2026-09-29T10:49:01Z`, 1,349 nodes / 5,758 edges | none | Commit hash not returned by the MCP output. Some attribute-based calls (for example `runtime.service().process_all()`) are not resolved as `CALLS` edges; confirmed instead by reading the source directly. No specialist agent is configured for this alias; this is a local read-only inspection by `analyst-requirements`. |

## Entry-Point Inventory

| Module | Entry point | Kind | Qualified symbol and file | Coverage |
|---|---|---|---|---|
| input-processor | `process_files` | MCP tool | [main.py#L116-L159](../../../input-processor/src/main.py) `C-VSCode-WS-spec2Test.input-processor.src.main.process_files` | ok |
| input-processor | `list_processed_files` | MCP tool | [main.py#L163-L191](../../../input-processor/src/main.py) `...main.list_processed_files` | ok |
| input-processor | `get_processed_content` | MCP tool | [main.py#L195-L232](../../../input-processor/src/main.py) `...main.get_processed_content` | ok |
| input-processor | `get_all_processed_content` | MCP tool | [main.py#L236-L269](../../../input-processor/src/main.py) `...main.get_all_processed_content` | ok |
| input-processor | `current_project` | MCP tool | [main.py#L96-L112](../../../input-processor/src/main.py) `...main.current_project` | ok |

The server runs as a standalone process (`uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=8000)`, [main.py#L275-L280](../../../input-processor/src/main.py)), exposed to the workspace as `input-processor` in [.vscode/mcp.json](../../../.vscode/mcp.json).

## Q1. Behaviors Pinned by Tests

| Behavior | Test (file, case, link) | Code (symbol, link) | Confidence |
|---|---|---|---|
| An unchanged source file is reused from cache; a modified one is reprocessed and the previous version archived; a renamed file is re-keyed without a model call; a deleted source is reported as orphaned but stays readable | `input-processor/tests/test_processing_service.py`: `test_an_unchanged_file_is_reused`, `test_a_modified_file_is_reprocessed_and_the_old_version_archived`, `test_a_renamed_file_is_rekeyed_without_reprocessing`, `test_a_rename_across_formats_is_reprocessed`, `test_a_deleted_file_is_reported_as_orphaned` | `ProcessingService.process_all/_process` ([processing_service.py#L159-L239](../../../input-processor/src/processing_service.py)) | High |
| A handler failure is reported with its cause instead of crashing the run | `test_processing_service.py`: `test_a_failing_handler_is_reported_with_its_cause`, `test_a_file_that_vanished_before_being_read_is_reported` | `ProcessingService._process`, `FileResult.failure/unreadable` ([processing_service.py#L55-L75](../../../input-processor/src/processing_service.py)) | High |
| Cache entries are archived on change, never overwritten twice, and legacy caches are migrated to a name-based layout, parking (not deleting) old files | `input-processor/tests/test_cache.py`: `test_archiving_keeps_the_previous_version`, `test_archiving_twice_does_not_overwrite`, `test_legacy_cache_is_migrated_to_the_named_layout`, `test_legacy_files_are_parked_not_deleted`, `test_index_reports_orphans` | `CacheReconciler.plan/apply` ([reconcile.py#L76-L136](../../../input-processor/src/cache/reconcile.py)) | High |
| Cached content can be read by name, hash, or a unique prefix; ambiguous prefixes are refused | `test_cache.py`: `test_cached_content_can_be_read_by_name_hash_or_prefix` (as `test_entries_expose_the_cached_metadata` at [reconcile evidence] and equivalents), `test_ambiguous_prefixes_are_refused` | `ProcessingService.read_cached` ([processing_service.py#L191-L198](../../../input-processor/src/processing_service.py)) | High |
| Each MCP tool reports a clear error for a missing project header, an unknown project, or a missing/ambiguous key | `input-processor/tests/test_tools.py`: `test_a_missing_header_is_explained`, `test_an_unknown_project_is_explained`, `test_get_processed_content_requires_a_key`, `test_get_processed_content_explains_an_unknown_name`, `test_current_project_reports_the_active_project` | `main.py` tools + `headers.py` | High |
| Every project gets its own runtime and lock; a duplicate or invalid project name is refused; adding a project does not disturb the running one | `input-processor/tests/test_projects.py`: `test_each_project_gets_its_own_runtime_and_lock`, `test_duplicate_project_names_are_refused`, `test_invalid_project_names_are_refused`, `test_adding_a_project_does_not_disturb_the_running_one`, `test_an_unconfigured_project_is_refused_by_the_pool` | `ProjectRegistry`, `RuntimePool` ([registry.py](../../../input-processor/src/projects/registry.py), [runtime.py#L167-L197](../../../input-processor/src/projects/runtime.py)) | High |
| The default provider registry includes native providers and the JSON catalog; a provider without extensions or a malformed catalog is rejected | `input-processor/tests/test_providers.py`: `test_default_registry_contains_natives_and_catalog`, `test_a_provider_without_extensions_is_rejected`, `test_catalog_capabilities_must_be_known`, `test_catalog_file_is_valid`, `test_catalog_reports_invalid_json`, `test_catalog_requires_a_providers_list` | `ProviderRegistry`, `catalog.json` ([registry.py](../../../input-processor/src/providers/registry.py)) | High |
| Video analysis is selected by declared provider capability; long videos are split by duration with a fallback to the whole file on failure; frame sampling is limited and explained when there are no frames | `input-processor/tests/test_video.py`: `test_factory_selects_by_capability`; `input-processor/tests/test_video_analyzers.py`: `test_a_long_video_is_split_by_duration`, `test_a_failing_split_falls_back_to_the_whole_video`, `test_frame_sampling_limits_the_number_of_frames`, `test_frame_sampling_explains_a_video_without_frames` | `analysis/video/*` (`VideoAnalyzer`, `FrameSamplingAnalyzer`, `GeminiFileApiAnalyzer`, `InlineVideoAnalyzer`) | High |
| PDF/Markdown conversion is cached and reused when the source and format are unchanged; a changed source rebuilds and archives the old images | `input-processor/tests/test_preprocessed.py`: `test_conversion_is_cached`, `test_a_renamed_source_reuses_the_content_without_rebuilding`, `test_a_source_with_a_different_format_is_rebuilt`, `test_a_changed_source_rebuilds_and_archives_the_old_images` | `preprocessing/pdf_to_markdown.py`, `cache/preprocessed.py` | High |
| Environment settings fall back to defaults on invalid values; LLM provider/model choices are not read from the environment (they come from `projects.json`) | `input-processor/tests/test_settings.py`: `test_invalid_values_fall_back_to_defaults`, `test_llm_choices_are_not_read_from_the_environment`, `test_llm_settings_merge_prefers_overrides` | `Settings.from_env` ([settings.py#L67-L87](../../../input-processor/src/settings.py)) | High |
| Every prompt referenced by the code exists on disk, and an unknown requested prompt lists the available ones | `input-processor/tests/test_prompts.py`: `test_every_prompt_used_by_the_code_exists`, `test_an_unknown_prompt_lists_the_available_ones` | `prompts/__init__.py`, `prompts/*.md` | High |

## Q2. Exposed Capabilities

| Capability | Source (specification operation or route, link) | Handler | Confidence |
|---|---|---|---|
| Process and analyze input files (video `.mp4`, `.pdf`, `.md`, `.txt`) for automated test-scenario generation, skipping unchanged files and archiving reprocessed ones | MCP tool `process_files`, docstring at [main.py#L118-L142](../../../input-processor/src/main.py) | `ProcessingService.process_all` | High |
| List every file with cached content and its identifiers | MCP tool `list_processed_files`, [main.py#L163-L177](../../../input-processor/src/main.py) | `ProcessingService.entries` | High |
| Retrieve the full analysis of a single processed file by name (hash lookup marked deprecated) | MCP tool `get_processed_content`, [main.py#L195-L219](../../../input-processor/src/main.py) | `ProcessingService.read_cached` | High |
| Retrieve the full analysis of every processed file in one call | MCP tool `get_all_processed_content`, [main.py#L236-L253](../../../input-processor/src/main.py) | `ProcessingService.entries` + `cache.read` | High |
| Report which project is active for the current request | MCP tool `current_project`, [main.py#L96-L112](../../../input-processor/src/main.py) | `headers.project_name_from_context` + `ProjectRegistry` | High |

## Q3. Entities, States, and Rules

| Entity or rule | Source (migration, entity, enum, constraint, link) | Values | Confidence |
|---|---|---|---|
| `Project` / `ProjectRegistry` / `ProjectRuntime` / `RuntimePool` | [projects/model.py](../../../input-processor/src/projects/model.py), [projects/registry.py](../../../input-processor/src/projects/registry.py), [projects/runtime.py](../../../input-processor/src/projects/runtime.py) | One runtime and lock per project name, loaded from `projects.json` | High |
| File processing status | `FileResult.to_dict` ([processing_service.py#L77-L89](../../../input-processor/src/processing_service.py)) and `process_files` docstring | `new \| cached \| updated \| renamed \| orphaned \| error` | High |
| `CacheEntry` / `CacheIndex` / `CacheStatus` / `Reconciliation` | [cache/entry.py](../../../input-processor/src/cache/entry.py), [cache/index.py](../../../input-processor/src/cache/index.py), [cache/reconcile.py](../../../input-processor/src/cache/reconcile.py) | Cache reconciliation plan/apply/orphans | High |
| `LlmSettings` / `VideoSettings` / `Settings` | [settings.py#L27-L87](../../../input-processor/src/settings.py) | Default provider `google_genai`; video tuning knobs (`segment_seconds=60`, `split_min_mb=12.0`, `frame_interval_seconds=2`, `max_frames=20`, etc.), all overridable by `INPUT_PROCESSOR_*` environment variables | High |
| Provider catalog entries (`deepseek`, `openrouter`, `qwen`) with declared capabilities | [providers/catalog.json](../../../input-processor/src/providers/catalog.json) | Capabilities: `text`, `images`, `video_inline` (per provider or per model) | High |
| `FileHandler` implementations | [handlers/](../../../input-processor/src/handlers): `MarkdownHandler`, `PdfHandler`, `TextHandler`, `VideoHandler` | Each declares its supported extensions via `HandlerRegistry` | High |
| `VideoAnalyzer` implementations | [analysis/video/](../../../input-processor/src/analysis/video): `FrameSamplingAnalyzer`, `GeminiFileApiAnalyzer`, `InlineVideoAnalyzer`, `MetadataOnlyAnalyzer` | Selected by declared provider capability | High |

## Q4. Actors and Permissions

| Actor | Capability | Source (guard, policy, role, link) | Confidence |
|---|---|---|---|
| Editor workspace (identified by project name, not a user or role) | Selects which project's files and cache are visible for the request | `X-Spec2Test-Project` HTTP header, resolved in [headers.py](../../../input-processor/src/projects/headers.py) | High |

No user- or role-based authorization was found within the analyzed scope; access is scoped per project only. Write `Not found within the analyzed scope` rather than `Does not exist`, since coverage of `input-processor` is complete but authentication could still be enforced at an infrastructure layer outside this repository.

## Q5. User Vocabulary

| Term | Where it appears (i18n key, screen, message, link) | Candidate glossary entry |
|---|---|---|
| Project | `X-Spec2Test-Project` header; `current_project` tool ([headers.py](../../../input-processor/src/projects/headers.py)) | A named workspace with its own input, cache, and provider configuration |
| Orphaned | `process_files` docstring and `FileResult` status ([main.py#L138](../../../input-processor/src/main.py)) | A cached file whose source disappeared from the input folder; content stays readable |
| Prompt | `prompts/*.md` file names: `document_summary`, `image_description`, `video`, `video_consolidation`, `video_segment` ([prompts/](../../../input-processor/src/prompts)) | A named template used to instruct the LLM provider for a specific analysis kind |

## Q6. Intent

| Capability | Reference (`alias#N` or commit, link) | Stated reason |
|---|---|---|
| Provider registry, multi-project workspaces, name-based cache | Commit `19a87fd` "Refactor input-processor: provider registry, multi-project workspaces, name-based cache" | States the reason for the current `ProviderRegistry`, per-project `RuntimePool`, and name-keyed cache design |

Only local commit history was available (read-only `git log`); no `gh` issues were queried for this alias in this pass.

## Q7. Call Paths

| Entry point | Path to persistence or integrations | Tool | Confidence |
|---|---|---|---|
| `process_files` | `main.process_files` → `_runtime` (project resolution via `headers.py` → `ProjectRegistry` → `RuntimePool.for_project`) → `runtime.service()` → `ProcessingService.process_all` → `CacheReconciler`/`CacheRepository` (filesystem cache) and `HandlerRegistry` (per-format handlers, which call `LLMProvider`/`LLMHandle` for video/PDF/image analysis) | `trace_path` (depth 4, outbound) + direct source read | High |
| `current_project` | `main.current_project` → `headers.project_name_from_context` → `ProjectRegistry.get` → `RuntimePool.for_name`/`for_project` | `trace_path` (depth 3, outbound) | High |
| `get_processed_content` / `get_all_processed_content` | `runtime.service()` → `ProcessingService.read_cached`/`entries` → filesystem cache read | Direct source read (attribute calls not resolved by `trace_path`) | Medium |

## Contradictions

Not applicable. No conflicting sources were found within the analyzed scope.

## Technical Evidence

| Alias | CBM project | Commit/generation | Tool/query | Symbol or path | Coverage | Confirmation | Limitations |
|---|---|---|---|---|---|---|---|
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `get_code_snippet` (outline/full) | `input-processor.src.main`, `.processing_service`, `.settings`, `.projects.headers`, `.projects.runtime`, `.cache.reconcile`, `.providers.registry`, `.analysis.video.base` | complete | snippet read | none |
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `search_graph` (label=Class, file_pattern=input-processor/src/**) | 54 classes across cache, handlers, providers, analysis, projects | complete | listing confirmed | none |
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `search_graph` (qn_pattern=`.*\.test_.*`, file_pattern=input-processor/tests/**) | 259 test functions (150 returned, paginated) | partial (page 1 of 2) | listing confirmed | Second page not fetched; representative sample used per behavior area |
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `trace_path` (mode=calls, outbound, depth 3-4) | `main.process_files`, `main.current_project` | partial | direct source read confirms the gap | Attribute-based calls (`runtime.service().process_all()`) are not resolved as edges |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | `git log --oneline -n 20 -- input-processor` | 4 commits touching `input-processor` | complete for this path | local reading | No `gh` issue query performed for this alias in this pass |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | Direct file read | `providers/catalog.json`, `prompts/*.md` | complete | local reading | none |

## Requirement Gaps

Not applicable (code-first mode: no documented scenarios exist yet for this domain).

## Addendum: Content Extraction and Summarization (2026-09-29)

Deeper pass over the analysis internals behind `get_processed_content`/`get_all_processed_content`, requested after the initial audit and the six-epic review.

### Q1. Behaviors Pinned by Tests (addendum)

| Behavior | Test (file, case, link) | Code (symbol, link) | Confidence |
|---|---|---|---|
| A Markdown file is summarized, enriching local images via a vision model when an enricher is configured; without one, the raw file is read | `input-processor/tests/test_handlers.py`: `test_markdown_handler_uses_the_enricher_when_available`, `test_markdown_handler_without_enricher_reads_the_file` | `MarkdownHandler.handle` ([markdown_handler.py](../../../input-processor/src/handlers/markdown_handler.py)) | High |
| A PDF is converted to enriched Markdown (text plus image descriptions) when a converter is configured; without one, its plain text layer is extracted | `test_handlers.py`: `test_pdf_handler_uses_the_converter`, `test_pdf_handler_without_converter_uses_the_text_layer`, `test_pdf_handler_reports_an_empty_pdf`, `test_pypdf2_guidance_when_the_package_is_missing` | `PdfHandler.handle` ([pdf_handler.py](../../../input-processor/src/handlers/pdf_handler.py)) | High |
| A plain text file is summarized directly; an empty file yields a clear message instead of a summarization call | `test_handlers.py`: `test_text_handler_summarises_the_file`, `test_text_handler_reports_an_empty_file` | `TextHandler.handle` ([text_handler.py](../../../input-processor/src/handlers/text_handler.py)) | High |
| A video file's analysis is delegated to the configured `VideoAnalyzer` | `test_handlers.py`: `test_video_handler_delegates_to_the_analyzer` | `VideoHandler.handle` ([video_handler.py](../../../input-processor/src/handlers/video_handler.py)) | High |
| Summarizing empty content is rejected before any model call | `test_handlers.py`: `test_summarizer_rejects_empty_content` | `DocumentSummarizer.summarize` ([document_summarizer.py#L26-L32](../../../input-processor/src/analysis/document_summarizer.py)) | High |
| An image description is sent as a base64 data URL to the vision model; an empty model answer is rejected | `test_handlers.py`: `test_image_describer_sends_a_data_url`, `test_image_describer_rejects_an_empty_answer` | `ImageDescriber.describe` ([image_describer.py#L28-L49](../../../input-processor/src/analysis/image_describer.py)) | High |
| Local images referenced in Markdown are described and the reference enriched; a missing image file keeps the original reference, and a failing description does not abort the rest of the enrichment | `test_handlers.py`: `test_markdown_enricher_describes_local_images`, `test_markdown_enricher_keeps_the_original_when_a_file_is_missing`, `test_markdown_enricher_survives_a_failing_description`, `test_resolve_image_path` | `MarkdownImageEnricher.enrich`/`_describe_match` ([markdown_images.py](../../../input-processor/src/preprocessing/markdown_images.py)) | High |
| A handler must declare at least one extension; the registry refuses duplicate extension registration and reports unsupported formats by listing what it does support | `test_handlers.py`: `test_handlers_must_declare_extensions`, `test_registry_refuses_duplicate_extensions`, `test_registry_reports_unsupported_formats`, `test_registry_maps_extensions_to_handlers` | `HandlerRegistry.register`/`get` ([registry.py](../../../input-processor/src/handlers/registry.py)) | High |
| Prompt templates are loaded once (cached) from `prompts/<name>.md`; an unknown prompt name fails, listing the available ones; templates render their `{placeholder}` values, and the document-summary prompt is filled with the document content | `input-processor/tests/test_prompts.py`: `test_prompts_are_loaded_once`, `test_an_unknown_prompt_lists_the_available_ones`, `test_templates_render_their_placeholders`, `test_the_summary_prompt_is_filled_with_the_document_content`, `test_every_prompt_used_by_the_code_exists` | `prompts.load`/`render` ([prompts/__init__.py](../../../input-processor/src/prompts/__init__.py)) | High |

### Q2. Exposed Capabilities (addendum)

| Capability | Source (specification operation or route, link) | Handler | Confidence |
|---|---|---|---|
| Turn extracted document text into a structured, test-generation-friendly summary via the configured LLM | Module docstring, [document_summarizer.py](../../../input-processor/src/analysis/document_summarizer.py) | `DocumentSummarizer.summarize` | High |
| Produce a QA-oriented description of an image, for use as alt text in enriched Markdown | Module docstring, [image_describer.py](../../../input-processor/src/analysis/image_describer.py) | `ImageDescriber.describe` | High |
| Convert a PDF's pages to Markdown, injecting a description for every embedded image found | [pdf_to_markdown.py#L44-L104](../../../input-processor/src/preprocessing/pdf_to_markdown.py) | `PdfToMarkdown.convert`/`_inject_image_descriptions` | High |
| Enrich Markdown by replacing local image references with generated descriptions | [markdown_images.py#L36-L46](../../../input-processor/src/preprocessing/markdown_images.py) | `MarkdownImageEnricher.enrich` | High |
| Load and render the Markdown-file prompt templates used by every analysis component | [prompts/__init__.py](../../../input-processor/src/prompts/__init__.py) | `prompts.load`/`render` | High |

### Q3. Entities, States, and Rules (addendum)

| Entity or rule | Source (migration, entity, enum, constraint, link) | Values | Confidence |
|---|---|---|---|
| `DocumentSummarizer` | [document_summarizer.py](../../../input-processor/src/analysis/document_summarizer.py) | Uses prompt `document_summary` by default; raises on empty input | High |
| `ImageDescriber` / `ImageDescriptionError` | [image_describer.py](../../../input-processor/src/analysis/image_describer.py) | Uses prompt `image_description` by default; raises `ImageDescriptionError` on an empty model answer | High |
| `PdfToMarkdown` / `PdfConversionError` | [pdf_to_markdown.py](../../../input-processor/src/preprocessing/pdf_to_markdown.py) | Converts PDF pages, injects image descriptions in order, drops newly extracted image files on failure | High |
| `MarkdownImageEnricher` | [markdown_images.py](../../../input-processor/src/preprocessing/markdown_images.py) | Matches Markdown image syntax via `IMAGE_RE`; keeps the original reference when the image file is missing or its description fails | High |
| `PromptTemplate` (`prompts.load`/`render`) | [prompts/__init__.py](../../../input-processor/src/prompts/__init__.py) | Backed by `prompts/<name>.md`; `document_summary`, `image_description`, `video`, `video_consolidation`, `video_segment` | High |
| `HandlerRegistry` extension rules | [registry.py](../../../input-processor/src/handlers/registry.py) | Every registered extension must start with `.`; a handler with no declared extensions is rejected; duplicate extensions are refused unless `replace=True` | High |

### Q7. Call Paths (addendum)

| Entry point | Path to persistence or integrations | Tool | Confidence |
|---|---|---|---|
| `process_files` (per file, by extension) | `HandlerRegistry.get` → `MarkdownHandler`/`PdfHandler`/`TextHandler`/`VideoHandler` → (Markdown/PDF only) `MarkdownImageEnricher`/`PdfToMarkdown` → `ImageDescriber.describe` (vision model call) → `DocumentSummarizer.summarize` (text model call), both loading their prompt via `prompts.load` | Direct source read | High |

### Technical Evidence (addendum)

| Alias | CBM project | Commit/generation | Tool/query | Symbol or path | Coverage | Confirmation | Limitations |
|---|---|---|---|---|---|---|---|
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `get_code_snippet` (full/outline) | `analysis.document_summarizer`, `.image_describer`, `preprocessing.pdf_to_markdown`, `.markdown_images`, `handlers.registry` | complete | snippet read | none |
| spec2test | C-VSCode-WS-spec2Test | generation `2026-09-29T10:49:01Z` | `search_graph` (file_pattern=`**/test_handlers.py`/`**/test_prompts.py`, qn_pattern=`.*test_.*`) | 18 test functions in `test_handlers.py`, 5 in `test_prompts.py` | complete | listing confirmed | none |
| spec2test | n/a (local file read) | working tree at 2026-09-29 | Direct file read | `handlers/base.py`, `handlers/markdown_handler.py`, `handlers/pdf_handler.py`, `handlers/text_handler.py`, `handlers/video_handler.py`, `prompts/__init__.py` | complete | local reading | none |
