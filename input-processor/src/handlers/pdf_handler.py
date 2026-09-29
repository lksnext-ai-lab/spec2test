"""Handler for PDF documents."""

from __future__ import annotations

from typing import Optional

from analysis.document_summarizer import DocumentSummarizer
from cache.source import SourceFile
from handlers.base import FileHandler, HandlerContext
from preprocessing.pdf_text import extract_text_with_pypdf2
from preprocessing.pdf_to_markdown import PdfToMarkdown

EMPTY_PDF_MESSAGE = (
    "No content could be extracted from this PDF. "
    "The file may be image-based or corrupted."
)


class PdfHandler(FileHandler):
    """Extracts a PDF's content and summarises it.

    With a vision model configured, the PDF first becomes enriched Markdown
    (text plus image descriptions); otherwise its plain text layer is used.
    """

    name = "pdf"
    extensions = (".pdf",)

    def __init__(
        self,
        summarizer: DocumentSummarizer,
        converter: Optional[PdfToMarkdown] = None,
    ) -> None:
        self._summarizer = summarizer
        self._converter = converter

    def handle(self, source: SourceFile, context: HandlerContext) -> str:
        text = self._extract(source, context)
        if not text.strip():
            return EMPTY_PDF_MESSAGE
        return self._summarizer.summarize(text, "PDF")

    def _extract(self, source: SourceFile, context: HandlerContext) -> str:
        if self._converter is not None and context.preprocessed is not None:
            return self._converter.convert(source)
        return extract_text_with_pypdf2(source.path)
