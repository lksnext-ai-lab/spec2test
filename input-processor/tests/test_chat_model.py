"""The single place where LangChain chat models are built.

``langchain`` itself is not a test dependency: the module is imported through a
fake ``langchain.chat_models`` so the defaults and the error guidance can be
checked without any provider package installed.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from providers.base import ProviderConfigurationError
from providers.chat_model import DEFAULT_MODEL_KWARGS, init_chat_model
from utils.opencv import load_cv2


class Recorder:
    """Stand-in for ``langchain.chat_models.init_chat_model``."""

    def __init__(self, fail_with: Exception | None = None) -> None:
        self.fail_with = fail_with
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def __call__(self, model: str, model_provider: str = "", **kwargs: Any) -> str:
        if self.fail_with is not None:
            raise self.fail_with
        self.calls.append((model, model_provider, kwargs))
        return "chat-model"


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    recording = Recorder()
    module = types.ModuleType("langchain.chat_models")
    module.init_chat_model = recording  # type: ignore[attr-defined]
    parent = types.ModuleType("langchain")
    parent.chat_models = module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain", parent)
    monkeypatch.setitem(sys.modules, "langchain.chat_models", module)
    return recording


def test_generation_defaults_are_applied(recorder: Recorder) -> None:
    assert init_chat_model("gpt-4o-mini", "openai", api_key="secret") == "chat-model"

    model, provider, kwargs = recorder.calls[0]
    assert (model, provider) == ("gpt-4o-mini", "openai")
    assert kwargs == {**DEFAULT_MODEL_KWARGS, "api_key": "secret"}
    assert kwargs["temperature"] == 0
    assert kwargs["max_retries"] == 2


def test_callers_can_override_the_defaults(recorder: Recorder) -> None:
    init_chat_model("qwen-vl", "openai", api_key="k", base_url="https://x.test/v1", temperature=0.7)

    _, _, kwargs = recorder.calls[0]
    assert kwargs["base_url"] == "https://x.test/v1"
    assert kwargs["temperature"] == 0.7


def test_no_api_key_is_not_passed_on(recorder: Recorder) -> None:
    init_chat_model("gpt-4o-mini", "openai")

    assert "api_key" not in recorder.calls[0][2]


def test_a_missing_langchain_package_is_explained(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "langchain", None)
    monkeypatch.setitem(sys.modules, "langchain.chat_models", None)

    with pytest.raises(ProviderConfigurationError, match="'langchain' package is required"):
        init_chat_model("gpt-4o-mini", "openai")


def test_a_missing_provider_package_is_explained(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "langchain", None)
    recording = Recorder(fail_with=ImportError("no module named 'langchain_openai'"))
    module = types.ModuleType("langchain.chat_models")
    module.init_chat_model = recording  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain.chat_models", module)

    with pytest.raises(ProviderConfigurationError) as error:
        init_chat_model("gpt-4o-mini", "openai")

    assert "langchain_openai" in str(error.value)


def test_opencv_is_loaded_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "cv2", None)

    with pytest.raises(RuntimeError, match="OpenCV is required"):
        load_cv2()
