"""Handler interface: one strategy per supported file format."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from cache.preprocessed import PreprocessedStore
from cache.source import SourceFile


@dataclass(frozen=True)
class HandlerContext:
    """Per-request collaborators a handler may need while processing a file."""

    preprocessed: Optional[PreprocessedStore] = None


class FileHandler(ABC):
    """Produces the processed content of one input file."""

    name: str = ""
    extensions: tuple[str, ...] = ()

    @abstractmethod
    def handle(self, source: SourceFile, context: HandlerContext) -> str:
        """Return the processed content of ``source``."""

    def supports(self, suffix: str) -> bool:
        return suffix.lower() in self.extensions

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.name}{list(self.extensions)}"
