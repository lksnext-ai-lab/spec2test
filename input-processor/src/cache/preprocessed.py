"""Store for artefacts derived from an input file.

PDFs and Markdown files are pre-processed before summarisation: PDFs become
enriched Markdown plus an images folder, Markdown files get descriptions
injected into their image references. Both live here, named after their source
and kept in step with it by the same reconciliation rules as the main cache.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Callable, Optional

from cache.entry import timestamp_for_filename
from cache.reconcile import CacheReconciler, CacheStatus
from cache.repository import CacheRepository
from cache.source import SourceFile

_log = logging.getLogger(__name__)

IMAGES_SUFFIX = "_images"


class PreprocessedStore:
    """Name-based store for enriched Markdown and extracted images."""

    def __init__(self, repository: CacheRepository) -> None:
        self.repository = repository
        self._reconciler: Optional[CacheReconciler] = None

    @classmethod
    def in_directory(cls, directory: Path) -> "PreprocessedStore":
        return cls(CacheRepository(directory))

    @property
    def directory(self) -> Path:
        return self.repository.directory

    @property
    def reconciler(self) -> CacheReconciler:
        if self._reconciler is None:
            self._reconciler = CacheReconciler(self.repository)
        return self._reconciler

    def refresh(self) -> None:
        """Forget the cached index so the next call re-reads the directory."""
        self._reconciler = None

    def images_dir(self, source: SourceFile) -> Path:
        """Directory holding the images extracted from ``source``."""
        return self.directory / f"{source.name}{IMAGES_SUFFIX}"

    def ensure(
        self,
        source: SourceFile,
        build: Callable[[Path], str],
        provider: str,
        model: str,
    ) -> tuple[str, CacheStatus]:
        """Return enriched Markdown for ``source``, building it when needed.

        ``build`` receives the images directory to write extracted images into;
        it is only called when the cache cannot satisfy the request.
        """
        produced: dict[str, str] = {}

        def produce() -> str:
            content = build(self.images_dir(source))
            produced["content"] = content
            return content

        result = self.reconciler.apply(source, produce, provider, model)

        if result.status is CacheStatus.UPDATED and result.archived is not None:
            self._archive_images(result.archived.source, result.archived.short_hash,
                                 result.archived.processed_at)

        if result.status is CacheStatus.RENAMED and result.previous is not None:
            self._move_images(result.previous.source, source.name)

        if result.status is CacheStatus.CACHED:
            return result.content or "", result.status

        content = produced.get("content")
        if content is None and result.entry is not None:
            content = self.repository.read(result.entry)
        return content or "", result.status

    def _move_images(self, old_name: str, new_name: str) -> None:
        """Follow a rename, so the layout keeps one image folder per source."""
        source_dir = self.directory / f"{old_name}{IMAGES_SUFFIX}"
        target = self.directory / f"{new_name}{IMAGES_SUFFIX}"
        if source_dir.is_dir() and not target.exists():
            shutil.move(str(source_dir), str(target))
            _log.info("Moved images of %s to %s", old_name, target.name)

    def cached(self, source: SourceFile) -> Optional[str]:
        """Return the stored Markdown for this exact content, if any."""
        return self.repository.read_by_name(source.name)

    def migrate_legacy(self) -> None:
        """Bring legacy ``<sha256>`` artefacts over to the name-based layout."""
        for entry in self.repository.migrate_legacy():
            legacy_images = self.directory / f"{entry.sha256}{IMAGES_SUFFIX}"
            if legacy_images.is_dir():
                target = self.directory / f"{entry.source}{IMAGES_SUFFIX}"
                if not target.exists():
                    shutil.move(str(legacy_images), str(target))
                    _log.info("Moved legacy image folder for %s to %s", entry.source, target.name)

    def _archive_images(self, source_name: str, short_hash: str, processed_at: str) -> None:
        images = self.directory / f"{source_name}{IMAGES_SUFFIX}"
        if not images.is_dir():
            return

        target = (
            self.repository.history_dir
            / f"{source_name}{IMAGES_SUFFIX}.{short_hash}.{timestamp_for_filename(processed_at)}"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(images), str(target))
        _log.info("Archived previous images of %s at %s", source_name, target.name)
