"""MCP tools for the Spec2Test input processor.

The tools are deliberately thin: they resolve the project from the request
headers, hand the work to the project's processing service, and shape the
result as JSON. Everything else lives in dedicated modules.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, TypeVar

import anyio
from mcp.server.fastmcp import Context, FastMCP

from cache.entry import CacheEntry
from cache.lookup import CacheLookupError
from processing_service import ProcessingReport
from projects.headers import project_name_from_context
from projects.model import ProjectConfigError
from projects.registry import ProjectRegistry
from projects.runtime import ProjectRuntime, RuntimePool
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

mcp = FastMCP("Spec2Test-InputProcessor", stateless_http=True, json_response=True)

T = TypeVar("T")


async def _run_blocking(work: Callable[[], T]) -> T:
    """Run blocking work in a worker thread so requests stay parallel."""
    return await anyio.to_thread.run_sync(work)


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
        report = await _run_blocking(work)
    except Exception as exc:  # noqa: BLE001 - report the failure instead of crashing
        _log.exception("process_files failed for project %s", runtime.project.name)
        return _error(f"Processing failed: {exc}")

    payload = [result.to_dict() for result in report.results]
    payload.extend(_orphan_summary(entry) for entry in report.orphaned)
    return json.dumps(payload, indent=2)


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


if __name__ == "__main__":
    import uvicorn

    _log.info("Starting input processor on port 8000 (projects: %s)", _configured_projects())
    # streamable_http_app() is a method returning the Starlette ASGI app, so it
    # has to be called: passing the method itself makes uvicorn treat it as an
    # app factory and fail.
    uvicorn.run(mcp.streamable_http_app(), host=os.getenv("HOST", "127.0.0.1"), port=8000)
