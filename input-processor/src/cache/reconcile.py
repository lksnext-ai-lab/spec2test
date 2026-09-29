"""Reconciliation between the input directory and the cache.

For every input file exactly one of five things is true:

===========================  ==========================================  =========
Situation                    Action                                      Status
===========================  ==========================================  =========
same name, same digest       reuse the cached content                    ``cached``
same name, other digest      archive the old file, process again         ``updated``
digest matches another name  re-key the file to the new name, no LLM     ``renamed``
nothing matches              process                                     ``new``
cached entry, source gone    keep it untouched, report it                ``orphaned``
===========================  ==========================================  =========

``renamed`` is what makes moving or renaming a file cheap: the bytes did not
change, so the analysis is still valid and only the bookkeeping is updated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Optional

from cache.entry import CacheEntry
from cache.index import CacheIndex
from cache.repository import CacheRepository
from cache.source import SourceFile

_log = logging.getLogger(__name__)


class CacheStatus(str, Enum):
    """Outcome of reconciling one input file with the cache."""

    NEW = "new"
    CACHED = "cached"
    UPDATED = "updated"
    RENAMED = "renamed"
    ORPHANED = "orphaned"
    ERROR = "error"  # not a reconciliation outcome: the handler raised

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.value


@dataclass(frozen=True)
class Reconciliation:
    """What happened (or would happen) to one input file."""

    status: CacheStatus
    entry: Optional[CacheEntry] = None
    archived: Optional[CacheEntry] = None
    content: Optional[str] = None
    previous: Optional[CacheEntry] = None
    """The entry a rename replaced, still holding its old source name."""

    @property
    def is_reuse(self) -> bool:
        """True when no analysis was produced by this run."""
        return self.status in {CacheStatus.CACHED, CacheStatus.RENAMED}


class CacheReconciler:
    """Decides the fate of each input file and keeps the index in step."""

    def __init__(self, repository: CacheRepository, index: Optional[CacheIndex] = None) -> None:
        self.repository = repository
        self._entries: dict[str, CacheEntry] = dict((index or repository.index()).by_source)

    @property
    def index(self) -> CacheIndex:
        return CacheIndex.build(self._entries.values())

    def plan(self, source: SourceFile) -> Reconciliation:
        """Decide what should happen to ``source`` without touching anything."""
        current = self._entries.get(source.name)

        if current is not None:
            if current.sha256 == source.sha256:
                return Reconciliation(
                    CacheStatus.CACHED, entry=current, content=self.repository.read(current)
                )
            return Reconciliation(CacheStatus.UPDATED, entry=current)

        twin = self.index.find_by_sha(source.sha256)
        if twin is not None and twin.format == source.format:
            return Reconciliation(CacheStatus.RENAMED, entry=twin)

        if twin is not None:
            _log.info(
                "%s matches the content of %s but changes format, reprocessing.",
                source.name,
                twin.source,
            )
        return Reconciliation(CacheStatus.NEW)

    def apply(
        self,
        source: SourceFile,
        produce: Callable[[], str],
        provider: str,
        model: str,
    ) -> Reconciliation:
        """Carry out :meth:`plan`, calling ``produce`` only when needed."""
        decision = self.plan(source)

        if decision.status is CacheStatus.CACHED:
            _log.info("Cache hit for %s", source.name)
            return decision

        if decision.status is CacheStatus.RENAMED:
            assert decision.entry is not None
            previous = decision.entry
            renamed = self.repository.rename(previous, source)
            self._entries.pop(previous.source, None)
            self._entries[renamed.source] = renamed
            return Reconciliation(
                CacheStatus.RENAMED,
                entry=renamed,
                content=self.repository.read(renamed),
                previous=previous,
            )

        archived: Optional[CacheEntry] = None
        if decision.entry is not None:
            archived = decision.entry
            self.repository.archive(archived)
            self._entries.pop(archived.source, None)

        content = produce()
        entry = self.repository.write(source, content, provider, model)
        self._entries[entry.source] = entry

        return Reconciliation(decision.status, entry=entry, archived=archived, content=content)

    def orphans(self, present_sources: Iterable[str]) -> tuple[CacheEntry, ...]:
        """Cached entries whose source file is no longer in the input directory."""
        return self.index.orphaned(present_sources)
