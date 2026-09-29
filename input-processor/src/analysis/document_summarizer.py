"""Summarise extracted document text into test-generation-friendly notes."""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from prompts import load
from utils.text import to_text

_log = logging.getLogger(__name__)

DEFAULT_PROMPT_NAME = "document_summary"


class DocumentSummarizer:
    """Turns raw document text into a structured summary."""

    def __init__(self, llm: BaseChatModel, prompt: str | None = None) -> None:
        self._llm = llm
        self._prompt = prompt if prompt is not None else load(DEFAULT_PROMPT_NAME)

    def summarize(self, text: str, source_label: str) -> str:
        """Summarise ``text``; ``source_label`` only appears in the logs."""
        if not text.strip():
            raise ValueError(f"No content to summarize from the {source_label} source.")

        _log.info("Summarizing %s characters of %s content.", len(text), source_label)
        message = HumanMessage(content=self._render_prompt(text))
        return to_text(self._llm.invoke([message]).content)

    def _render_prompt(self, text: str) -> str:
        if "{content}" in self._prompt:
            return self._prompt.replace("{content}", text)
        return f"{self._prompt}\n\nDocument content:\n{text}"
