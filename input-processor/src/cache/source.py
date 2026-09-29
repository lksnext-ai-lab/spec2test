"""Description of an input file as it is being processed."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from utils.hashing import sha256_of


@dataclass(frozen=True)
class SourceFile:
    """An input file plus the metadata the cache needs to record."""

    path: Path
    name: str
    format: str
    size: int
    sha256: str

    @classmethod
    def from_path(cls, path: Path) -> "SourceFile":
        """Hash and describe ``path``."""
        path = Path(path)
        return cls(
            path=path,
            name=path.name,
            format=path.suffix.lower(),
            size=path.stat().st_size,
            sha256=sha256_of(path),
        )

    @property
    def short_hash(self) -> str:
        return self.sha256[:8]

    def __str__(self) -> str:
        return f"{self.name} ({self.short_hash})"
