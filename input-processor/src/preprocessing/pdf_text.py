"""Plain-text extraction from PDFs with PyMuPDF.

Fallback used when the PDF cannot be pre-processed into enriched Markdown
because no vision model is configured.
"""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger(__name__)


def extract_text_with_pymupdf(pdf_path: Path) -> str:
    """Extract the text layer of a PDF, page by page."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError(
            "Reading PDF text requires the 'pymupdf' package. "
            "Install the input-processor requirements."
        ) from exc

    try:
        with fitz.open(str(pdf_path)) as document:
            if document.needs_pass:
                _log.warning("PDF %s is encrypted, attempting to decrypt...", pdf_path.name)
                document.authenticate("")
            return _extract_pages(document)
    except Exception as exc:  # noqa: BLE001 - report the failure as content
        _log.exception("Could not read PDF %s", pdf_path.name)
        return f"Error processing PDF: {exc}"


def _extract_pages(document) -> str:
    chunks: list[str] = []
    for number, page in enumerate(document, start=1):
        try:
            text = page.get_text()
        except Exception:  # noqa: BLE001 - a bad page must not stop the rest
            _log.exception("Could not extract text from page %s", number)
            continue
        if text and text.strip():
            chunks.append(f"--- Page {number} ---\n{text}\n")
    return "\n".join(chunks)
