"""Helpers shared across modules."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from utils.files import read_text_file
from utils.hashing import sha256_of, short_hash
from utils.media import guess_media_type
from utils.text import to_text


def test_to_text_flattens_the_shapes_providers_return() -> None:
    assert to_text("  hello  ") == "hello"
    assert to_text({"text": " from a block "}) == "from a block"
    assert to_text({"content": [{"text": "nested"}]}) == "nested"
    assert to_text([{"text": "one"}, {"text": "two"}]) == "one\ntwo"
    assert to_text([{"text": "one"}, "", None]) == "one"
    assert to_text(None) == ""
    assert to_text(42) == "42"


def test_to_text_handles_a_real_langchain_message() -> None:
    assert to_text(AIMessage(content="from langchain").content) == "from langchain"


def test_to_text_of_a_block_without_text_falls_back_to_repr() -> None:
    assert to_text({"type": "tool_use", "id": "1"}) == "{'type': 'tool_use', 'id': '1'}"


def test_sha256_of_matches_hashlib(tmp_path: Path) -> None:
    import hashlib

    path = tmp_path / "file.txt"
    path.write_bytes(b"content")

    digest = sha256_of(path)
    assert digest == hashlib.sha256(b"content").hexdigest()
    assert short_hash(digest) == digest[:8]


def test_read_text_file_replaces_undecodable_bytes(tmp_path: Path) -> None:
    path = tmp_path / "latin.txt"
    path.write_bytes(b"caf\xe9")

    assert read_text_file(path) == "caf�"


def test_read_text_file_reports_missing_files(tmp_path: Path) -> None:
    assert read_text_file(tmp_path / "missing.txt") == ""


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("shot.png", "image/png"),
        ("shot.jpeg", "image/jpeg"),
        ("shot.unknown-ext", "image/unknown-ext"),
        ("shot", "image/png"),
    ],
)
def test_guess_media_type(name: str, expected: str) -> None:
    assert guess_media_type(Path(name)) == expected
