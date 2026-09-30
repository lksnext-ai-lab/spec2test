"""MCP tools for the Spec2Test input processor.

The tools are deliberately thin: they resolve the project from the request
headers, hand the work to the project's processing service, and shape the
result as JSON. Everything else lives in dedicated modules.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable, TypeVar

import anyio
from mcp.server.fastmcp import Context, FastMCP

from cache.entry import CacheEntry
from cache.lookup import CacheLookupError
from processing_service import ProcessingReport
from progress import CallbackReporter, ProcessingCancelled, use_reporter
from projects.headers import project_name_from_context
from projects.model import ProjectConfigError
from projects.registry import ProjectRegistry
from projects.runtime import ProjectRuntime, RuntimePool
from providers.describe import describe_providers
from providers.registry import build_default_registry
from settings import Settings

settings = Settings.from_env()

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
_log = logging.getLogger("input_processor")

providers = build_default_registry()
pool = RuntimePool(
    projects=ProjectRegistry(settings.projects_config, settings.projects_root),
    providers=providers,
    env=os.environ,
    settings=settings,
)

# json_response stays off: tool calls answer as an SSE stream so progress and
# log notifications reach the client while a long file is being processed.
mcp = FastMCP("Spec2Test-InputProcessor", stateless_http=True, json_response=False)

T = TypeVar("T")


async def _run_blocking(work: Callable[[], T]) -> T:
    """Run blocking work in a worker thread so requests stay parallel."""
    return await anyio.to_thread.run_sync(work)


async def _notify(context: Context, message: str, counter: int) -> None:
    """Send one progress notification plus a log line to the client."""
    report = getattr(context, "report_progress", None)
    if report is not None:
        try:
            await report(counter, None, message)
        except TypeError:  # older SDKs have no ``message`` argument
            await report(counter, None)
    info = getattr(context, "info", None)
    if info is not None:
        await info(message)


async def _run_reported(context: Context, work: Callable[[], T]) -> T:
    """Run ``work`` in a worker thread, streaming its progress to the client.

    When the client cancels the request the thread cannot be interrupted, so
    it is told to stop at its next checkpoint instead; the project lock is
    held until it does.
    """
    cancelled = threading.Event()
    counter = 0

    def sink(message: str, progress: Any, total: Any) -> None:
        nonlocal counter
        counter += 1
        anyio.from_thread.run(_notify, context, message, counter)

    reporter = CallbackReporter(sink, cancelled)

    def run() -> T:
        with use_reporter(reporter):
            return work()

    try:
        return await anyio.to_thread.run_sync(run, abandon_on_cancel=True)
    except anyio.get_cancelled_exc_class():
        cancelled.set()
        raise


def _runtime(context: Context) -> ProjectRuntime:
    """Resolve the project this request belongs to."""
    return pool.for_name(project_name_from_context(context) or "")


def _error(message: str) -> str:
    return json.dumps({"error": message})


def _entry_summary(entry: CacheEntry) -> dict[str, Any]:
    return {
        "name": entry.source,
        "format": entry.format,
        "size": entry.size,
        "sha256": entry.sha256,
        "processed_at": entry.processed_at,
        "provider": entry.provider,
        "model": entry.model,
    }


def _orphan_summary(entry: CacheEntry) -> dict[str, Any]:
    """A cached file whose source is gone: kept, readable, but reported."""
    return {
        "name": entry.source,
        "format": entry.format,
        "size": entry.size,
        "sha256": entry.sha256,
        "status": "orphaned",
        "processed_at": entry.processed_at,
    }


def _configured_projects() -> str:
    """Project names for the startup line, without failing when unconfigured."""
    try:
        return ", ".join(pool.project_names()) or "none configured"
    except ProjectConfigError as exc:
        return f"none configured ({exc})"


@mcp.tool()
async def current_project(ctx: Context) -> str:
    """
    Report which project this request is processed as.

    Returns the project name, its input/preprocessed/cache paths inside the
    container, and the models configured for it. Use it to confirm you are
    working on the intended set of files.

    Returns:
        JSON object with the active project's name, paths and models
    """
    try:
        project = _runtime(ctx).project
    except ProjectConfigError as exc:
        return _error(str(exc))

    return json.dumps(project.describe(), indent=2)


@mcp.tool()
async def process_files(ctx: Context) -> str:
    """
    Process and analyze files for automated test scenario generation.

    Supports video recordings (MP4) of browser sessions and documentation files
    in PDF, Markdown, and plain text formats.
    Videos are analyzed to extract UI interactions, workflows, and user journeys.
    PDFs are processed to extract requirements, specifications, and business rules.
    Markdown files enrich local images with generated descriptions when available,
    while text files are read without preprocessing.

    Already processed files are skipped, changed files are reprocessed (the
    previous result is archived), renamed files are re-keyed without any model
    call, and cached files whose source disappeared from the input folder are
    reported as orphaned (their content is kept and stays readable).

    Returns:
        JSON string containing a list of file objects:
        - name: Original filename (use this with get_processed_content)
        - format: File format (.mp4, .pdf, .md, .txt)
        - size: Size in bytes
        - sha256: Content digest of the source file
        - status: new | cached | updated | renamed | orphaned | error
        - processed_at: When this content was produced
        - error: Why the file could not be processed (only for status 'error')
    """
    try:
        runtime = _runtime(ctx)
    except ProjectConfigError as exc:
        return _error(str(exc))

    def work() -> ProcessingReport:
        with runtime.lock:
            return runtime.service().process_all()

    try:
        report = await _run_reported(ctx, work)
    except ProcessingCancelled:
        return _error("Processing was cancelled.")
    except Exception as exc:  # noqa: BLE001 - report the failure instead of crashing
        _log.exception("process_files failed for project %s", runtime.project.name)
        return _error(f"Processing failed: {exc}")

    payload = [result.to_dict() for result in report.results]
    payload.extend(_orphan_summary(entry) for entry in report.orphaned)
    return json.dumps(payload, indent=2)


@mcp.tool()
async def list_input_files(ctx: Context) -> str:
    """
    List the input files of this project and their cache state, without processing.

    Use it to see what process_files or process_file would do.

    Returns:
        JSON string containing a list of file objects:
        - name: Original filename
        - format: File format (.mp4, .pdf, .md, .txt)
        - size: Size in bytes
        - sha256: Content digest of the source file
        - cache_status: cached | stale | renamed | new
        - processed_at: When the cached content was produced (if any)
    """
    try:
        runtime = _runtime(ctx)
    except ProjectConfigError as exc:
        return _error(str(exc))

    try:
        return json.dumps(await _run_blocking(lambda: runtime.service().inspect()), indent=2)
    except Exception as exc:  # noqa: BLE001
        _log.exception("list_input_files failed")
        return _error(f"Could not list the input files: {exc}")


@mcp.tool()
async def process_file(ctx: Context, file_name: str, force: bool = False) -> str:
    """
    Process a single input file and report progress while it runs.

    Behaves like process_files for one file: cached files are reused, changed
    files are reprocessed and the previous result archived. With force=True
    the file is processed again even if the cache is up to date.

    Args:
        file_name: Name of a file in the project's input folder
        force: Process again even when the cached result is up to date

    Returns:
        JSON object with name, format, size, sha256, status
        (new | cached | updated | renamed | error), processed_at and error.
    """
    name = (file_name or "").strip()
    if not name or Path(name).name != name:
        return _error("file_name must be the name of a file in the input folder.")

    try:
        runtime = _runtime(ctx)
    except ProjectConfigError as exc:
        return _error(str(exc))

    def work() -> dict[str, Any]:
        with runtime.lock:
            service = runtime.service()
            path = service.input_dir / name
            if not path.is_file():
                raise FileNotFoundError(f"'{name}' is not in the input folder.")
            if not service.handlers.supports(path):
                raise ValueError(f"'{name}' has an unsupported format.")
            return service.process_file(path, force=force).to_dict()

    try:
        return json.dumps(await _run_reported(ctx, work), indent=2)
    except ProcessingCancelled:
        return _error("Processing was cancelled.")
    except (FileNotFoundError, ValueError) as exc:
        return _error(str(exc))
    except Exception as exc:  # noqa: BLE001
        _log.exception("process_file failed for %s", name)
        return _error(f"Processing failed: {exc}")


@mcp.tool()
async def list_providers(ctx: Context) -> str:
    """
    List the LLM providers and curated models that can be configured.

    Returns:
        JSON list of providers with name, api_key_env, api_key_set (whether the
        server has the key; the key itself is never returned), default_model,
        capabilities and models [{id, capabilities}].
    """
    return json.dumps(describe_providers(providers, os.environ), indent=2)


@mcp.tool()
async def list_processed_files(ctx: Context) -> str:
    """
    List all processed files with their identifiers.

    Returns one entry per file that has cached content, so you can decide which
    ones to read with get_processed_content.

    Returns:
        JSON string containing a list of file objects:
        - name: Original filename (use this with get_processed_content)
        - sha256: Content digest of the source file
        - processed_at: When this content was produced
    """
    try:
        runtime = _runtime(ctx)
    except ProjectConfigError as exc:
        return _error(str(exc))

    try:
        entries = await _run_blocking(lambda: runtime.service().entries())
    except Exception as exc:  # noqa: BLE001
        _log.exception("list_processed_files failed")
        return _error(f"Could not list processed files: {exc}")

    payload = [
        {"name": entry.source, "sha256": entry.sha256, "processed_at": entry.processed_at}
        for entry in sorted(entries, key=lambda item: item.source)
    ]
    return json.dumps(payload, indent=2)


@mcp.tool()
async def get_processed_content(ctx: Context, file_name: str = "", file_hash: str = "") -> str:
    """
    Retrieve detailed analysis results for a single file.

    Returns the complete processed analysis of a specific file, ready for use in
    generating automated test scenarios. Content includes UI element identification,
    user workflow analysis, requirements extraction, and technical details needed
    for test automation.

    Args:
        file_name: Name of the processed file, as returned by list_processed_files
        file_hash: Deprecated. SHA-256 hash (or unique prefix) of the file

    Returns:
        Complete analysis results including:
        - Video files: UI components, user interactions, workflows, timestamps
        - Document files (.pdf, .md, .txt): Requirements, user stories, business
          rules, data models, acceptance criteria, and image context when available
    """
    key = (file_name or file_hash or "").strip()
    if not key:
        return (
            "Error: a file name is required. Use list_processed_files to get "
            "the available names."
        )

    try:
        runtime = _runtime(ctx)
    except ProjectConfigError as exc:
        return f"Error: {exc}"

    try:
        return await _run_blocking(lambda: runtime.service().read_cached(key))
    except CacheLookupError as exc:
        return f"Error: {exc}"
    except Exception as exc:  # noqa: BLE001
        _log.exception("get_processed_content failed for %s", key)
        return f"Error: could not read '{key}': {exc}"


@mcp.tool()
async def get_all_processed_content(ctx: Context) -> str:
    """
    Retrieve detailed analysis results for all processed files.

    Returns the complete processed analysis of every available file in a single
    request. Use this when you need all file content at once, instead of one
    call per file.

    Returns:
        JSON string containing a list of objects:
        - name: Original filename
        - sha256: Content digest of the source file
        - processed_at: When this content was produced
        - content: The full analysis for that file
    """
    try:
        runtime = _runtime(ctx)
    except ProjectConfigError as exc:
        return _error(str(exc))

    def collect() -> list[dict[str, Any]]:
        service = runtime.service()
        payload: list[dict[str, Any]] = []
        for entry in sorted(service.entries(), key=lambda item: item.source):
            payload.append({**_entry_summary(entry), "content": service.cache.read(entry)})
        return payload

    try:
        results = await _run_blocking(collect)
    except Exception as exc:  # noqa: BLE001
        _log.exception("get_all_processed_content failed")
        return _error(f"Could not read the cached content: {exc}")

    return json.dumps(results, indent=2)


def bind_host() -> str:
    """Address to listen on.

    ``HOST`` wins when set. Otherwise a container must listen on every interface
    (a published port cannot reach 127.0.0.1 inside it), and anything else stays
    on loopback.
    """
    explicit = (os.getenv("HOST") or "").strip()
    if explicit:
        return explicit
    in_container = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")
    return "0.0.0.0" if in_container else "127.0.0.1"  # noqa: S104 - published port needs it


if __name__ == "__main__":
    import uvicorn

    host = bind_host()
    _log.info("Starting input processor on %s:8000 (projects: %s)", host, _configured_projects())
    # streamable_http_app() is a method returning the Starlette ASGI app, so it
    # has to be called: passing the method itself makes uvicorn treat it as an
    # app factory and fail.
    uvicorn.run(mcp.streamable_http_app(), host=host, port=8000)
