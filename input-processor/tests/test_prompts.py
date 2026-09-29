"""Prompt templates live beside the code as Markdown files."""

from __future__ import annotations

import pytest

from prompts import PROMPTS_DIR, PromptNotFoundError, load, render

PLACEHOLDERS = {
    "document_summary": {"content": "the requirements text"},
    "video_segment": {"index": 1, "total": 3, "offset": "1:00"},
    "video_consolidation": {"segments": "[Segment 1]\nintro"},
}


@pytest.mark.parametrize("name", sorted(PLACEHOLDERS) + ["image_description", "video"])
def test_every_prompt_used_by_the_code_exists(name: str) -> None:
    content = load(name)

    assert content
    assert not content.startswith("---")


def test_an_unknown_prompt_lists_the_available_ones() -> None:
    with pytest.raises(PromptNotFoundError) as error:
        load("nope")

    message = str(error.value)
    assert "Unknown prompt 'nope'" in message
    assert "document_summary" in message


def test_prompts_are_loaded_once() -> None:
    assert load("video") is load("video")


@pytest.mark.parametrize("name", sorted(PLACEHOLDERS))
def test_templates_render_their_placeholders(name: str) -> None:
    values = PLACEHOLDERS[name]

    rendered = render(name, **values)

    for value in values.values():
        assert str(value) in rendered
    assert "{" not in rendered


def test_the_summary_prompt_is_filled_with_the_document_content() -> None:
    rendered = render("document_summary", content="a very specific sentence")

    assert "a very specific sentence" in rendered
