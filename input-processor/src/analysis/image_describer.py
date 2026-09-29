"""Describe images found in documents, using the configured vision model."""

from __future__ import annotations

import base64
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from prompts import load
from utils.text import to_text

_log = logging.getLogger(__name__)

DEFAULT_PROMPT_NAME = "image_description"


class ImageDescriptionError(RuntimeError):
    """Raised when the vision model returns nothing usable."""


class ImageDescriber:
    """Produces the alt text used to replace image references in documents."""

    def __init__(self, llm: BaseChatModel, prompt: str | None = None) -> None:
        self._llm = llm
        self._prompt = prompt if prompt is not None else load(DEFAULT_PROMPT_NAME)

    def describe(self, image_bytes: bytes, media_type: str) -> str:
        """Return a QA-oriented description of one image."""
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        messages = [
            SystemMessage(content=self._prompt),
            HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{encoded}"},
                    }
                ]
            ),
        ]

        response = self._llm.invoke(messages)
        description = to_text(response.content)
        if not description:
            raise ImageDescriptionError("The vision model returned an empty image description.")
        return description
