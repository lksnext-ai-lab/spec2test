"""Handler for Markdown documents."""

from __future__ import annotations

from typing import Optional

from analysis.document_summarizer import DocumentSummarizer
from cache.source import SourceFile
from handlers.base import FileHandler, HandlerContext
from handlers.text_handler import EMPTY_TEXT_MESSAGE
from preprocessing.markdown_images import MarkdownImageEnricher
from utils.files import read_text_file


class MarkdownHandler(FileHandler):
    """Summarises Markdown, describing local images when a vision model exists."""

    name = "markdown"
    extensions = (".md",)

    def __init__(
        self,
        summarizer: DocumentSummarizer,
        enricher: Optional[MarkdownImageEnricher] = None,
    ) -> None:
        self._summarizer = summarizer
        self._enricher = enricher

    def handle(self, source: SourceFile, context: HandlerContext) -> str:
        text = self._read(source, context)
        if not text.strip():
            return EMPTY_TEXT_MESSAGE.format(format=source.format)
        return self._summarizer.summarize(text, "Markdown")

    def _read(self, source: SourceFile, context: HandlerContext) -> str:
        if self._enricher is not None and context.preprocessed is not None:
            return self._enricher.enrich(source)
        return read_text_file(source.path)
