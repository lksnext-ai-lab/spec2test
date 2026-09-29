"""Resolving what a caller means by "the file".

Content is addressed by source name (``login-demo.mp4``). Digests and unique
prefixes keep working so older callers and automation do not break.
"""

from __future__ import annotations

from typing import Optional

from cache.entry import SUFFIX, CacheEntry
from cache.index import CacheIndex


class CacheLookupError(ValueError):
    """Raised when a key does not identify exactly one cached file."""


def resolve(index: CacheIndex, key: str) -> CacheEntry:
    """Find the single entry identified by ``key``."""
    wanted = (key or "").strip()
    if not wanted:
        raise CacheLookupError(
            "No file specified. Use list_processed_files to see the available names."
        )

    exact = index.find_by_source(wanted) or index.find_by_source(_strip_suffix(wanted))
    if exact is not None:
        return exact

    by_digest = index.find_by_sha(wanted)
    if by_digest is not None:
        return by_digest

    matches = _prefix_matches(index, wanted)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(sorted(entry.source for entry in matches))
        raise CacheLookupError(
            f"'{wanted}' matches several files: {names}. Use the full name."
        )

    raise CacheLookupError(
        f"No cached content for '{wanted}'. Use list_processed_files to see "
        "the available names."
    )


def _strip_suffix(key: str) -> str:
    return key[: -len(SUFFIX)] if key.endswith(SUFFIX) else key


def _prefix_matches(index: CacheIndex, key: str) -> tuple[CacheEntry, ...]:
    return tuple(
        entry
        for entry in index.entries
        if entry.sha256.startswith(key) or entry.source.startswith(key)
    )


def find(index: CacheIndex, key: str) -> Optional[CacheEntry]:
    """Like :func:`resolve`, but returns ``None`` instead of raising."""
    try:
        return resolve(index, key)
    except CacheLookupError:
        return None
