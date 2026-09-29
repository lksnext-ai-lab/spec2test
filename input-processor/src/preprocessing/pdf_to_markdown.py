"""PDF -> enriched Markdown via PyMuPDF4LLM plus image descriptions.

The extracted images keep the placeholders PyMuPDF4LLM writes, but their alt
text is replaced with a description produced by the vision model, so the
downstream summary can talk about screenshots and diagrams it cannot see.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from analysis.image_describer import ImageDescriber
from cache.preprocessed import PreprocessedStore
from cache.reconcile import CacheStatus
from cache.source import SourceFile

_log = logging.getLogger(__name__)

PLACEHOLDER_RE = re.compile(r"!\[\]\((.*?)\)")


class PdfConversionError(RuntimeError):
    """Raised when a PDF cannot be converted to Markdown."""


class PdfToMarkdown:
    """Converts PDFs into Markdown and caches the result per content digest."""

    def __init__(
        self,
        store: PreprocessedStore,
        describer: Optional[ImageDescriber] = None,
        provider: str = "",
        model: str = "",
    ) -> None:
        self._store = store
        self._describer = describer
        self._provider = provider
        self._model = model

    def convert(self, source: SourceFile) -> str:
        """Return the enriched Markdown for ``source``, converting if needed."""
        content, status = self._store.ensure(
            source,
            lambda images_dir: self._build(source, images_dir),
            self._provider,
            self._model,
        )
        if status is CacheStatus.CACHED:
            _log.info("Pre-processed Markdown cache hit for %s", source.name)
        return content

    def _build(self, source: SourceFile, images_dir: Path) -> str:
        images_dir.mkdir(parents=True, exist_ok=True)
        pre_existing = {item.name for item in images_dir.glob("*")}

        try:
            markdown = _to_markdown(source.path, images_dir)
            if self._describer is None:
                return markdown
            return self._inject_image_descriptions(source.path, markdown, images_dir)
        except Exception:
            self._drop_new_files(images_dir, pre_existing)
            raise

    def _inject_image_descriptions(
        self, pdf_path: Path, markdown: str, images_dir: Path
    ) -> str:
        """Replace ``![](...)`` placeholders with described alt text.

        Placeholders are matched to the extracted images in document order. If
        the counts disagree the surplus placeholders are left untouched.
        """
        placeholders = PLACEHOLDER_RE.findall(markdown)
        if not placeholders:
            return markdown

        images = _extract_images_in_order(pdf_path)
        replacements = min(len(placeholders), len(images))
        if len(placeholders) != len(images):
            _log.warning(
                "Image count mismatch for %s: markdown=%d extracted=%d",
                pdf_path.name,
                len(placeholders),
                len(images),
            )

        assert self._describer is not None
        for index in range(replacements):
            placeholder_path = placeholders[index]
            image_bytes, media_type = images[index]
            description = self._describer.describe(image_bytes, media_type)

            image_path = images_dir / Path(placeholder_path).name
            markdown = markdown.replace(
                f"![]({placeholder_path})",
                f"![Image description: {description}]({_as_posix(image_path)})",
                1,
            )

        return markdown

    @staticmethod
    def _drop_new_files(images_dir: Path, pre_existing: set[str]) -> None:
        """Remove only the files this run created, keeping older ones intact."""
        for item in images_dir.glob("*"):
            if item.name in pre_existing:
                continue
            try:
                item.unlink()
            except OSError as exc:  # pragma: no cover - best effort cleanup
                _log.debug("Could not remove %s: %s", item, exc)


def _to_markdown(pdf_path: Path, images_dir: Path) -> str:
    """Convert one PDF with PyMuPDF4LLM, writing its images to ``images_dir``."""
    try:
        import pymupdf4llm
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise PdfConversionError(
            "PDF preprocessing requires the 'pymupdf4llm' package. "
            "Install the input-processor requirements."
        ) from exc

    try:
        return pymupdf4llm.to_markdown(
            str(pdf_path), write_images=True, image_path=str(images_dir)
        )
    except Exception as exc:
        raise PdfConversionError(f"Could not convert {pdf_path.name} to Markdown: {exc}") from exc


def _extract_images_in_order(pdf_path: Path) -> list[tuple[bytes, str]]:
    """Return every embedded image of the PDF, in document order."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise PdfConversionError(
            "PDF image extraction requires the 'pymupdf' package. "
            "Install the input-processor requirements."
        ) from exc

    images: list[tuple[bytes, str]] = []
    document = fitz.open(str(pdf_path))
    try:
        for page in document:
            for image in page.get_images(full=True):
                extracted = document.extract_image(image[0])
                data: Any = extracted.get("image")
                if not data:
                    continue
                extension = (extracted.get("ext") or "png").lower()
                images.append((data, "image/jpeg" if extension == "jpg" else f"image/{extension}"))
    finally:
        document.close()

    return images


def _as_posix(path: Path) -> str:
    return str(path).replace("\\", "/")
