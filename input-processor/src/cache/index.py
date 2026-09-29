"""Lookup tables built from the front-matter of every cache file."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional

from cache.entry import CacheEntry


@dataclass(frozen=True)
class CacheIndex:
    """Cache entries indexed by source name and by content digest."""

    entries: tuple[CacheEntry, ...] = ()
    by_source: Mapping[str, CacheEntry] = field(default_factory=dict)
    by_sha: Mapping[str, CacheEntry] = field(default_factory=dict)

    @classmethod
    def build(cls, entries: Iterable[CacheEntry]) -> "CacheIndex":
        by_source: dict[str, CacheEntry] = {}
        by_sha: dict[str, CacheEntry] = {}
        ordered: list[CacheEntry] = []

        for entry in entries:
            ordered.append(entry)
            by_source[entry.source] = entry
            by_sha.setdefault(entry.sha256, entry)

        return cls(entries=tuple(ordered), by_source=by_source, by_sha=by_sha)

    def find_by_source(self, name: str) -> Optional[CacheEntry]:
        return self.by_source.get(name)

    def find_by_sha(self, sha256: str) -> Optional[CacheEntry]:
        return self.by_sha.get(sha256)

    def with_subset(self, entries: Iterable[CacheEntry]) -> "CacheIndex":
        return CacheIndex.build(entries)

    def orphaned(self, present_sources: Iterable[str]) -> tuple[CacheEntry, ...]:
        """Entries whose source file is no longer in the input directory."""
        present = set(present_sources)
        return tuple(entry for entry in self.entries if entry.source not in present)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)
