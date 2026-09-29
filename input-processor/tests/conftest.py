"""Shared fixtures.

The suite runs without API keys, without network access and without the heavy
video/PDF dependencies: providers are replaced by stubs and the modules that
need OpenCV, PyMuPDF or the Google SDK import them lazily.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cache.preprocessed import PreprocessedStore  # noqa: E402
from cache.repository import CacheRepository  # noqa: E402
from handlers.registry import HandlerRegistry  # noqa: E402
from processing_service import ProcessingService  # noqa: E402
from support import RecordingHandler, StubChatModel  # noqa: E402


@pytest.fixture
def inputs_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "inputs"
    directory.mkdir()
    return directory


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "cache"
    directory.mkdir()
    return directory


@pytest.fixture
def preprocessed_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "preprocessed"
    directory.mkdir()
    return directory


@pytest.fixture
def chat_model() -> StubChatModel:
    return StubChatModel("processed content")


@pytest.fixture
def cache(cache_dir: Path) -> CacheRepository:
    return CacheRepository(cache_dir)


@pytest.fixture
def preprocessed(preprocessed_dir: Path) -> PreprocessedStore:
    return PreprocessedStore.in_directory(preprocessed_dir)


@pytest.fixture
def service(inputs_dir: Path, cache: CacheRepository, chat_model: StubChatModel) -> ProcessingService:
    return ProcessingService(
        input_dir=inputs_dir,
        cache=cache,
        handlers=HandlerRegistry([RecordingHandler(chat_model)]),
        provider="stub",
        model="stub-model",
    )


def write_input(directory: Path, name: str, content: str = "hello") -> Path:
    """Create a file with the given content and return its path."""
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path
