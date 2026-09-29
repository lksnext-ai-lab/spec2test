"""Content hashing used to detect changed inputs."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 4096


def sha256_of(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's contents."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(digest: str, length: int = 8) -> str:
    """Return the leading characters of a digest, for logs and file names."""
    return digest[:length]
