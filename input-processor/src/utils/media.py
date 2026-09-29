"""Media type helpers shared by the image description code paths."""

from __future__ import annotations

import mimetypes
from pathlib import Path


def guess_media_type(path: Path) -> str:
    """Best-effort media type for an image file."""
    media_type, _ = mimetypes.guess_type(path.name)
    if media_type:
        return media_type

    suffix = path.suffix.lower().lstrip(".") or "png"
    if suffix == "jpg":
        return "image/jpeg"
    return f"image/{suffix}"
