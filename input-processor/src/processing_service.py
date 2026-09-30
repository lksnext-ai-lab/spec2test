"""Orchestration: input directory -> handler -> cache.

This replaces the old ``FileProcessor``. It owns no provider logic: the
handlers know how to process a format, the reconciler knows what the cache
already holds, and this class only walks the input directory and keeps the two
in step.
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cache.entry import CacheEntry
from cache.index import CacheIndex
from cache.lookup import resolve
from cache.preprocessed import PreprocessedStore
from cache.reconcile import CacheReconciler, CacheStatus, Reconciliation
from cache.repository import CacheRepository
from cache.source import SourceFile
from handlers.base import HandlerContext
from handlers.registry import HandlerRegistry

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileResult:
    """What happened to one input file."""

    name: str
    format: str
    size: int
    sha256: str
    status: CacheStatus
    processed_at: str = ""
    error: str = ""

    @classmethod
    def from_reconciliation(cls, source: SourceFile, result: Reconciliation) -> "FileResult":
        entry = result.entry
        return cls(
            name=source.name,
            format=source.format,
            size=source.size,
            sha256=source.sha256,
            status=result.status,
            processed_at=entry.processed_at if entry else "",
        )

    @classmethod
    def failure(cls, source: SourceFile, error: str) -> "FileResult":
        return cls(
            name=source.name,
            format=source.format,
            size=source.size,
            sha256=source.sha256,
            status=CacheStatus.ERROR,
            error=error,
        )

    @classmethod
    def unreadable(cls, path: Path, error: str) -> "FileResult":
        """A file that could not even be read, so it has no digest."""
        return cls(
            name=Path(path).name,
            format=Path(path).suffix.lower(),
            size=0,
            sha256="",
            status=CacheStatus.ERROR,
            error=error,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "format": self.format,
            "size": self.size,
            "sha256": self.sha256,
            "status": self.status.value,
        }
        if self.processed_at:
            payload["processed_at"] = self.processed_at
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass(frozen=True)
class ProcessingReport:
    """Outcome of one pass over the input directory."""

    results: tuple[FileResult, ...] = ()
    orphaned: tuple[CacheEntry, ...] = field(default_factory=tuple)

    @property
    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for result in self.results:
            counts[result.status.value] = counts.get(result.status.value, 0) + 1
        return counts

    def summarise(self) -> str:
        """Short human-readable summary for the logs and tool output."""
        counts = ", ".join(f"{status}={count}" for status, count in sorted(self.counts.items()))
        summary = counts or "nothing to process"
        if self.orphaned:
            summary += f", orphaned={len(self.orphaned)}"
        return summary


class ProcessingService:
    """Processes every supported file of one project."""

    def __init__(
        self,
        input_dir: Path,
        cache: CacheRepository,
        handlers: HandlerRegistry,
        provider: str,
        model: str,
        preprocessed: Optional[PreprocessedStore] = None,
    ) -> None:
        self.input_dir = Path(input_dir)
        self.cache = cache
        self.handlers = handlers
        self.provider = provider
        self.model = model
        self.preprocessed = preprocessed
        self._legacy_migrated = False

    @property
    def extensions(self) -> tuple[str, ...]:
        return self.handlers.extensions()

    def supported_files(self) -> list[Path]:
        """Input files this service can process, sorted by name."""
        if not self.input_dir.is_dir():
            _log.error("Input directory does not exist: %s", self.input_dir)
            return []

        files = [
            path
            for path in sorted(self.input_dir.iterdir())
            if path.is_file() and self.handlers.supports(path)
        ]
        unsupported = sorted(
            path.name
            for path in self.input_dir.iterdir()
            if path.is_file() and not self.handlers.supports(path)
        )
        if unsupported:
            _log.info("Skipping unsupported files: %s", ", ".join(unsupported))
        return files

    def process_all(self) -> ProcessingReport:
        """Reconcile every input file with the cache and process what changed."""
        self._initialise_cache()
        reconciler = CacheReconciler(self.cache)
        context = self._handler_context()
        files = self.supported_files()

        results: list[FileResult] = [
            self._process_path(path, reconciler, context) for path in files
        ]

        report = ProcessingReport(
            results=tuple(results),
            orphaned=reconciler.orphans(path.name for path in files),
        )
        _log.info("Processed %s file(s): %s", len(report.results), report.summarise())
        return report

    def process_file(self, path: Path) -> FileResult:
        """Process a single file (used by tests and ad-hoc runs)."""
        self._initialise_cache()
        return self._process_path(
            Path(path), CacheReconciler(self.cache), self._handler_context()
        )

    def cache_index(self) -> CacheIndex:
        """Current cache contents, read from disk."""
        return self.cache.index()

    def entries(self) -> tuple[CacheEntry, ...]:
        return self.cache_index().entries

    def read_cached(self, key: str) -> str:
        """Return the content addressed by ``key``.

        Raises :class:`cache.lookup.CacheLookupError` when the key is missing
        or ambiguous.
        """
        entry = resolve(self.cache_index(), key)
        return self.cache.read(entry)

    def _process_path(
        self,
        path: Path,
        reconciler: CacheReconciler,
        context: HandlerContext,
    ) -> FileResult:
        """Read one file and process it, reporting files that vanished."""
        try:
            source = SourceFile.from_path(path)
        except OSError as exc:
            _log.exception("Could not read %s", path)
            return FileResult.unreadable(path, _describe_error(exc))
        return self._process(source, reconciler, context)

    def _process(
        self,
        source: SourceFile,
        reconciler: CacheReconciler,
        context: HandlerContext,
    ) -> FileResult:
        handler = self.handlers.find(source.name)
        if handler is None:
            error = f"No handler for {source.format or source.name}"
            _log.error("%s", error)
            return FileResult.failure(source, error)

        try:
            result = reconciler.apply(
                source,
                lambda: handler.handle(source, context),
                self.provider,
                self.model,
            )
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the run
            _log.exception("Error processing %s", source.name)
            _log.debug("Traceback for %s:\n%s", source.name, traceback.format_exc())
            return FileResult.failure(source, _describe_error(exc))

        _log.info("%s: %s", source.name, result.status.value)
        return FileResult.from_reconciliation(source, result)

    def _handler_context(self) -> HandlerContext:
        if self.preprocessed is None:
            return HandlerContext()
        self.preprocessed.refresh()
        return HandlerContext(preprocessed=self.preprocessed)

    def _initialise_cache(self) -> None:
        self.cache.ensure()
        if self._legacy_migrated:
            return

        self._legacy_migrated = True
        self.cache.migrate_legacy()
        if self.preprocessed is not None:
            self.preprocessed.migrate_legacy()


def _describe_error(exc: Exception) -> str:
    """Include the exception chain: the useful cause is usually nested."""
    parts = [f"{type(exc).__name__}: {exc}"]
    cause = exc.__cause__
    while cause is not None:
        parts.append(f"caused by {type(cause).__name__}: {cause}")
        cause = cause.__cause__
    return " | ".join(parts)
