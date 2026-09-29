"""Normalisation helpers for LLM content payloads."""

from __future__ import annotations

from typing import Any


def to_text(content: Any) -> str:
    """Flatten a LangChain message payload into plain text.

    Provider responses arrive as a string, a single content block or a list of
    blocks (``{"type": "text", "text": ...}``, nested tool blocks, ...). Every
    caller only ever wants the text.
    """
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text.strip()
        if "content" in content:
            return to_text(content["content"])
        return str(content).strip()

    if isinstance(content, (list, tuple)):
        parts = (to_text(item) for item in content)
        return "\n".join(part for part in parts if part).strip()

    if content is None:
        return ""

    return str(content).strip()
