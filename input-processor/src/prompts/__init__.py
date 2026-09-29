"""Prompt templates kept as Markdown files next to the code that uses them."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


class PromptNotFoundError(FileNotFoundError):
    """Raised when a prompt template is missing."""


@lru_cache(maxsize=None)
def load(name: str) -> str:
    """Return the stripped contents of ``prompts/<name>.md``."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        available = ", ".join(sorted(p.stem for p in PROMPTS_DIR.glob("*.md")))
        raise PromptNotFoundError(f"Unknown prompt '{name}'. Available prompts: {available}")
    return path.read_text(encoding="utf-8").strip()


def render(name: str, **values: object) -> str:
    """Return ``prompts/<name>.md`` with ``{placeholder}`` values substituted."""
    return load(name).format(**values)
