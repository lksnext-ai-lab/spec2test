"""File reading helpers."""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger(__name__)


def read_text_file(path: Path) -> str:
    """Read a UTF-8 text file, replacing undecodable bytes rather than failing."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.error("Could not read %s: %s", path.name, exc)
        return ""
