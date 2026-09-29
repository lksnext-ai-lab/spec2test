"""Extension -> handler lookup, replacing the old if/elif chain."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

from handlers.base import FileHandler

_log = logging.getLogger(__name__)


class UnsupportedFormatError(ValueError):
    """Raised when no handler is registered for a file's format."""


class HandlerRegistry:
    """Maps file extensions to the handler that knows how to process them."""

    def __init__(self, handlers: Iterable[FileHandler] = ()) -> None:
        self._by_extension: dict[str, FileHandler] = {}
        for handler in handlers:
            self.register(handler)

    def register(self, handler: FileHandler, *, replace: bool = False) -> None:
        """Register a handler for every extension it declares."""
        if not handler.extensions:
            raise ValueError(f"Handler '{handler.name}' declares no extensions.")

        for extension in handler.extensions:
            suffix = extension.lower()
            if not suffix.startswith("."):
                raise ValueError(f"Extension {extension!r} must start with a dot.")

            if suffix in self._by_extension and not replace:
                raise ValueError(f"A handler is already registered for {suffix}.")
            self._by_extension[suffix] = handler

    def get(self, path: str | Path) -> FileHandler:
        """Return the handler for a file, by extension."""
        suffix = Path(path).suffix.lower()
        try:
            return self._by_extension[suffix]
        except KeyError:
            raise UnsupportedFormatError(
                f"No handler for {suffix or 'extensionless files'}. "
                f"Supported formats: {', '.join(self.extensions())}"
            ) from None

    def find(self, path: str | Path) -> Optional[FileHandler]:
        """Return the handler for a file, or ``None`` when unsupported."""
        return self._by_extension.get(Path(path).suffix.lower())

    def supports(self, path: str | Path) -> bool:
        return self.find(path) is not None

    def extensions(self) -> tuple[str, ...]:
        """Every supported extension, sorted."""
        return tuple(sorted(self._by_extension))

    def handlers(self) -> tuple[FileHandler, ...]:
        """Registered handlers, without duplicates."""
        unique: dict[str, FileHandler] = {}
        for handler in self._by_extension.values():
            unique.setdefault(handler.name, handler)
        return tuple(unique.values())
