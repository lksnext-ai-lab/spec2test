"""Handler for plain text documents."""

from __future__ import annotations

from analysis.document_summarizer import DocumentSummarizer
from cache.source import SourceFile
from handlers.base import FileHandler, HandlerContext
from utils.files import read_text_file

EMPTY_TEXT_MESSAGE = "No content could be extracted from this {format} file."


class TextHandler(FileHandler):
    """Reads a plain text file and summarises it."""

    name = "text"
    extensions = (".txt",)

    def __init__(self, summarizer: DocumentSummarizer) -> None:
        self._summarizer = summarizer

    def handle(self, source: SourceFile, context: HandlerContext) -> str:
        text = read_text_file(source.path)
        if not text.strip():
            return EMPTY_TEXT_MESSAGE.format(format=source.format)
        return self._summarizer.summarize(text, "text")
