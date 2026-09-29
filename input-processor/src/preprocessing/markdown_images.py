"""Enrich Markdown documents by describing their local images."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from analysis.image_describer import ImageDescriber
from cache.preprocessed import PreprocessedStore
from cache.reconcile import CacheStatus
from cache.source import SourceFile
from utils.media import guess_media_type

_log = logging.getLogger(__name__)

IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]+)\)")


class MarkdownImageEnricher:
    """Rewrites ``![alt](target)`` for local images with generated alt text."""

    def __init__(
        self,
        store: PreprocessedStore,
        describer: ImageDescriber,
        provider: str = "",
        model: str = "",
    ) -> None:
        self._store = store
        self._describer = describer
        self._provider = provider
        self._model = model

    def enrich(self, source: SourceFile) -> str:
        """Return the Markdown with image alt text filled in."""
        content, status = self._store.ensure(
            source,
            lambda _images_dir: self._build(source),
            self._provider,
            self._model,
        )
        if status is CacheStatus.CACHED:
            _log.info("Pre-processed Markdown cache hit for %s", source.name)
        return content

    def _build(self, source: SourceFile) -> str:
        markdown = source.path.read_text(encoding="utf-8", errors="replace")
        return IMAGE_RE.sub(lambda match: self._describe_match(source.path, match), markdown)

    def _describe_match(self, markdown_path: Path, match: re.Match[str]) -> str:
        target = match.group("target")
        image_path = resolve_image_path(markdown_path, target)
        if image_path is None or not image_path.is_file():
            if image_path is not None:
                _log.warning("Markdown image not found for %s: %s", markdown_path.name, image_path)
            return match.group(0)

        try:
            description = self._describer.describe(
                image_path.read_bytes(), guess_media_type(image_path)
            )
        except Exception as exc:  # noqa: BLE001 - one bad image must not fail the file
            _log.warning("Skipping image description for %s: %s", image_path, exc)
            return match.group(0)

        return f"![Image description: {description}]({target})"


def resolve_image_path(markdown_path: Path, target: str) -> Optional[Path]:
    """Resolve a Markdown image target to a local file path.

    Returns ``None`` for remote or inline targets, which cannot be described.
    """
    cleaned = target.strip()
    if cleaned.startswith("<") and cleaned.endswith(">"):
        cleaned = cleaned[1:-1].strip()

    path_match = re.match(r'(?P<path>\S+)(?:\s+["\'][^"\']*["\'])?$', cleaned)
    if path_match:
        cleaned = path_match.group("path")

    if cleaned.startswith(("http://", "https://", "data:")):
        return None

    image_path = Path(cleaned)
    if not image_path.is_absolute():
        image_path = markdown_path.parent / image_path
    return image_path.resolve()
