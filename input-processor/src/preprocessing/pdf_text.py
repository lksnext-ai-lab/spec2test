"""Plain-text extraction from PDFs with pypdf.

Fallback used when the PDF cannot be pre-processed into enriched Markdown
because no vision model is configured.
"""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger(__name__)


def extract_text_with_pypdf(pdf_path: Path) -> str:
    """Extract the text layer of a PDF, page by page."""
    try:
        import pypdf
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError(
            "Reading PDF text requires the 'pypdf' package. "
            "Install the input-processor requirements."
        ) from exc

    try:
        with open(pdf_path, "rb") as handle:
            reader = pypdf.PdfReader(handle)
            if reader.is_encrypted:
                _log.warning("PDF %s is encrypted, attempting to decrypt...", pdf_path.name)
                reader.decrypt("")
            return _extract_pages(reader)
    except Exception as exc:  # noqa: BLE001 - report the failure as content
        _log.exception("Could not read PDF %s", pdf_path.name)
        return f"Error processing PDF: {exc}"


def _extract_pages(reader) -> str:
    chunks: list[str] = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text()
        except Exception:  # noqa: BLE001 - a bad page must not stop the rest
            _log.exception("Could not extract text from page %s", number)
            continue
        if text and text.strip():
            chunks.append(f"--- Page {number} ---\n{text}\n")
    return "\n".join(chunks)
