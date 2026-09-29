"""Name-based storage for processed artefacts.

One file per source file, named after it (``cache/login-demo.mp4.md``), with the
content digest kept in the front-matter. Compared to the original layout of
``cache/<sha256>.txt`` this keeps the cache readable and still detects changes,
because the digest travels inside the file instead of being its name.
"""

from __future__ import annotations

import csv
import logging
import os
import shutil
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from cache.entry import (
    SUFFIX,
    CacheEntry,
    entry_from_text,
    parse,
    render,
    timestamp_for_filename,
    utc_from_timestamp,
    utc_now,
)
from cache.index import CacheIndex
from cache.source import SourceFile

_log = logging.getLogger(__name__)

HISTORY_DIRNAME = ".history"
LEGACY_DIRNAME = "legacy"
_LEGACY_SUFFIX = ".txt"
_LEGACY_BANNER = "PROCESSED CONTENT:"


class CacheRepository:
    """Reads, writes, archives and migrates the cached artefacts of one project."""

    def __init__(self, directory: Path, history_dirname: str = HISTORY_DIRNAME) -> None:
        self.directory = Path(directory)
        self.history_dirname = history_dirname

    @property
    def history_dir(self) -> Path:
        return self.directory / self.history_dirname

    def ensure(self) -> None:
        """Create the cache and history directories if they do not exist."""
        self.directory.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, source_name: str) -> Path:
        """Path of the cache file belonging to ``source_name``."""
        if not source_name or Path(source_name).name != source_name:
            raise ValueError(f"Invalid source file name: {source_name!r}")
        return self.directory / f"{source_name}{SUFFIX}"

    def index(self) -> CacheIndex:
        """Scan the cache directory and index every readable entry."""
        if not self.directory.is_dir():
            return CacheIndex.build(())

        entries: list[CacheEntry] = []
        for path in sorted(self.directory.glob(f"*{SUFFIX}")):
            try:
                entries.append(entry_from_text(path.read_text(encoding="utf-8"), path))
            except (OSError, ValueError) as exc:
                _log.warning("Skipping unreadable cache file %s: %s", path.name, exc)

        index = CacheIndex.build(entries)
        self._warn_about_duplicates(index)
        return index

    def read(self, entry: CacheEntry) -> str:
        """Return the body of a cached artefact, without its front-matter."""
        _, body = parse(entry.path.read_text(encoding="utf-8"))
        return body

    def read_by_name(self, name: str) -> Optional[str]:
        """Return the body stored for ``name``, or ``None`` when absent."""
        try:
            path = self.path_for(name)
        except ValueError:
            return None
        if not path.is_file():
            return None

        try:
            _, body = parse(path.read_text(encoding="utf-8"))
        except OSError as exc:
            _log.warning("Could not read cache file %s: %s", path.name, exc)
            return None
        return body

    def write(
        self,
        source: SourceFile,
        content: str,
        provider: str,
        model: str,
        processed_at: Optional[str] = None,
    ) -> CacheEntry:
        """Store ``content`` for ``source``, replacing any previous version."""
        self.ensure()
        entry = CacheEntry(
            source=source.name,
            format=source.format,
            size=source.size,
            sha256=source.sha256,
            processed_at=processed_at or utc_now(),
            provider=provider,
            model=model,
            path=self.path_for(source.name),
        )
        self._write_entry(entry, content)
        _log.info("Cached %s at %s", source.name, entry.path.name)
        return entry

    def archive(self, entry: CacheEntry) -> Path:
        """Move an entry to ``.history`` so the previous version is not lost."""
        target = self._unique_history_path(entry)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(entry.path), str(target))
        _log.info("Archived previous version of %s at %s", entry.source, target)
        return target

    def rename(self, entry: CacheEntry, source: SourceFile) -> CacheEntry:
        """Re-key an entry after its source file was renamed.

        The content is reused as is — a rename cannot change the bytes, so no
        reprocessing is needed — but the recorded source metadata is rewritten.
        """
        target = self.path_for(source.name)
        body = self.read(entry)
        renamed = entry.with_source(source.name, source.format, source.size, target)
        self._write_entry(renamed, body)

        if entry.path != target and entry.path.is_file():
            entry.path.unlink()

        _log.info("Renamed cache entry %s -> %s", entry.source, source.name)
        return renamed

    def migrate_legacy(self) -> list[CacheEntry]:
        """Convert legacy ``<sha256>.txt`` files into named ``.md`` entries."""
        if not self.directory.is_dir():
            return []

        migrated: list[CacheEntry] = []
        for path in sorted(self.directory.glob(f"*{_LEGACY_SUFFIX}")):
            try:
                entry = self._migrate_one(path)
            except (OSError, ValueError) as exc:
                _log.warning("Could not migrate legacy cache file %s: %s", path.name, exc)
                continue
            if entry is not None:
                migrated.append(entry)

        if migrated:
            _log.info("Migrated %s legacy cache file(s).", len(migrated))
        return migrated

    def _migrate_one(self, path: Path) -> Optional[CacheEntry]:
        metadata, content = _split_legacy_file(path.read_text(encoding="utf-8", errors="replace"))
        if metadata is None:
            return None

        name = metadata.get("original_name") or f"{path.stem}{SUFFIX}"
        sha256 = metadata.get("hash") or path.stem
        target = self.path_for(name)

        if target.is_file():
            # Already migrated on an earlier run; only park the legacy file.
            _log.info("Legacy cache file %s already migrated to %s.", path.name, target.name)
            self._park_legacy(path, sha256)
            return None

        entry = CacheEntry(
            source=name,
            format=metadata.get("format") or Path(name).suffix.lower(),
            size=_as_int(metadata.get("file_size")),
            sha256=sha256,
            processed_at=_mtime_as_utc(path),
            provider=metadata.get("provider") or "legacy",
            model=metadata.get("model") or "unknown",
            path=target,
        )
        self._write_entry(entry, content)
        self._park_legacy(path, sha256)
        return entry

    def _park_legacy(self, path: Path, sha256: str) -> None:
        parked = self.history_dir / LEGACY_DIRNAME / f"{sha256}{_LEGACY_SUFFIX}"
        parked.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(parked))

    def _write_entry(self, entry: CacheEntry, content: str) -> None:
        entry.path.parent.mkdir(parents=True, exist_ok=True)
        document = render(entry.to_front_matter()) + _normalise_body(content)
        temporary = entry.path.with_name(f"{entry.path.name}.tmp")
        temporary.write_text(document, encoding="utf-8")
        os.replace(temporary, entry.path)

    def _unique_history_path(self, entry: CacheEntry) -> Path:
        stem = f"{entry.source}.{entry.short_hash}.{timestamp_for_filename(entry.processed_at)}"
        candidate = self.history_dir / f"{stem}{SUFFIX}"

        counter = 1
        while candidate.exists():
            candidate = self.history_dir / f"{stem}-{counter}{SUFFIX}"
            counter += 1
        return candidate

    def _warn_about_duplicates(self, index: CacheIndex) -> None:
        if len(index.by_source) != len(index.entries):
            _log.warning(
                "Cache directory %s contains duplicate source names; the newest file wins.",
                self.directory,
            )


def _normalise_body(content: str) -> str:
    """Keep exactly one blank line between front-matter and content."""
    return content.lstrip("\n") + ("\n" if not content.endswith("\n") else "")


def _split_legacy_file(text: str) -> tuple[Optional[dict[str, Any]], str]:
    """Parse the CSV header the original cache format used."""
    lines = text.split("\n")
    if len(lines) < 2:
        return None, ""

    reader = csv.reader(StringIO("\n".join(lines[:2])))
    rows = [row for row in reader if any(field.strip() for field in row)]
    if len(rows) < 2 or len(rows[0]) < 4:
        return None, ""

    metadata = dict(zip((field.strip() for field in rows[0]), rows[1]))
    if not metadata.get("hash"):
        return None, ""

    banner = next(
        (index for index, line in enumerate(lines) if line.startswith(_LEGACY_BANNER)),
        None,
    )
    content = "\n".join(lines[banner + 1 :]) if banner is not None else ""
    return metadata, content


def _as_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _mtime_as_utc(path: Path) -> str:
    return utc_from_timestamp(path.stat().st_mtime)
