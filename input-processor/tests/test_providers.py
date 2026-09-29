"""The registry resolves providers, capabilities and API keys."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providers.base import Capabilities, LLMProvider, ProviderConfigurationError
from providers.native import AnthropicProvider, GoogleGenAIProvider, OpenAIProvider
from providers.openai_compatible import CatalogEntry, OpenAICompatibleProvider, load_catalog
from providers.registry import ProviderRegistry, build_default_registry
from settings import LlmSettings
from support import StubChatModel

ENV_WITH_KEYS = {
    "GOOGLE_API_KEY": "google-key",
    "OPENAI_API_KEY": "openai-key",
    "ANTHROPIC_API_KEY": "anthropic-key",
    "DEEPSEEK_API_KEY": "deepseek-key",
    "OPENROUTER_API_KEY": "openrouter-key",
    "DASHSCOPE_API_KEY": "dashscope-key",
}


@pytest.fixture(autouse=True)
def _no_real_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never build real LangChain clients in the test suite."""
    for provider_class in (
        GoogleGenAIProvider,
        OpenAIProvider,
        AnthropicProvider,
        OpenAICompatibleProvider,
    ):
        monkeypatch.setattr(
            provider_class,
            "create_chat_model",
            lambda self, model, api_key=None: StubChatModel(f"{self.name}:{model}"),
        )


def test_default_registry_contains_natives_and_catalog() -> None:
    registry = build_default_registry()

    assert registry.available() == (
        "anthropic",
        "deepseek",
        "google_genai",
        "openai",
        "openrouter",
        "qwen",
    )


def test_unknown_provider_lists_the_available_ones() -> None:
    registry = build_default_registry()

    with pytest.raises(ProviderConfigurationError) as error:
        registry.get("gemini")

    message = str(error.value)
    assert "Unknown LLM provider 'gemini'" in message
    assert "google_genai" in message and "qwen" in message


def test_empty_provider_name_is_reported() -> None:
    with pytest.raises(ProviderConfigurationError, match="No provider configured"):
        build_default_registry().get("")


def test_missing_api_key_names_the_variable() -> None:
    registry = build_default_registry()

    with pytest.raises(ProviderConfigurationError) as error:
        registry.resolve(LlmSettings(provider="deepseek"), {})

    assert "DEEPSEEK_API_KEY" in str(error.value)


def test_resolve_returns_a_handle_with_capabilities() -> None:
    registry = build_default_registry()

    handle = registry.resolve(LlmSettings(provider="google_genai"), ENV_WITH_KEYS)

    assert handle.provider_name == "google_genai"
    assert handle.model == "gemini-2.0-flash"
    assert handle.capabilities.video_upload is True
    assert handle.api_key == "google-key"
    assert handle.label == "google_genai:gemini-2.0-flash"


def test_resolve_uses_the_configured_model() -> None:
    registry = build_default_registry()

    handle = registry.resolve(
        LlmSettings(provider="openrouter", model="qwen/qwen2.5-vl-72b-instruct"), ENV_WITH_KEYS
    )

    assert handle.model == "qwen/qwen2.5-vl-72b-instruct"
    assert handle.capabilities.video_inline is True


@pytest.mark.parametrize(
    ("provider", "model", "expected"),
    [
        ("deepseek", None, ("text",)),
        ("openrouter", None, ("text", "images", "video_inline")),
        ("openrouter", "deepseek/deepseek-chat", ("text",)),
        ("openrouter", "qwen/qwen2.5-vl-72b-instruct", ("text", "images", "video_inline")),
        ("qwen", None, ("text", "images")),
        ("openai", None, ("text", "images")),
        ("anthropic", None, ("text", "images")),
        ("google_genai", None, ("text", "images", "video_upload")),
    ],
)
def test_capabilities_per_provider_and_model(
    provider: str, model: str | None, expected: tuple[str, ...]
) -> None:
    capabilities = build_default_registry().capabilities_for(
        LlmSettings(provider=provider, model=model)
    )

    assert capabilities.names() == expected


def test_registering_the_same_provider_twice_is_refused() -> None:
    registry = ProviderRegistry()

    registry.register(OpenAIProvider())
    with pytest.raises(ProviderConfigurationError, match="already registered"):
        registry.register(OpenAIProvider())


def test_register_can_replace_on_request() -> None:
    registry = ProviderRegistry([OpenAIProvider()])
    replacement = GoogleGenAIProvider()

    registry.register(replacement, replace=True)

    assert registry.get("google_genai") is replacement


def test_a_provider_without_extensions_is_rejected() -> None:
    class NamelessProvider(LLMProvider):
        def create_chat_model(self, model, api_key):  # pragma: no cover - never called
            raise AssertionError

    with pytest.raises(ProviderConfigurationError, match="must declare a name"):
        ProviderRegistry().register(NamelessProvider())


def test_provider_without_a_default_model_fails_clearly() -> None:
    class KeylessProvider(LLMProvider):
        name = "keyless"

        def create_chat_model(self, model, api_key):  # pragma: no cover - never called
            raise AssertionError

    registry = ProviderRegistry([KeylessProvider()])

    with pytest.raises(ProviderConfigurationError, match="no default model"):
        registry.resolve(LlmSettings(provider="keyless"), {})


def test_capabilities_from_names_rejects_unknown_names() -> None:
    with pytest.raises(ProviderConfigurationError) as error:
        Capabilities.from_names(["text", "audio"])

    message = str(error.value)
    assert "Unknown capability 'audio'" in message
    assert "video_upload" in message


def test_capabilities_are_printable() -> None:
    assert str(Capabilities.from_names(["text", "images"])) == "text, images"
    assert str(Capabilities()) == "text"  # text-only by default
    assert str(Capabilities(text=False)) == "none"


def test_catalog_entry_requires_its_keys() -> None:
    with pytest.raises(ProviderConfigurationError, match="missing required keys: default_model"):
        CatalogEntry.from_dict({"name": "x", "base_url": "u", "api_key_env": "K"})


def test_catalog_file_is_valid() -> None:
    entries = load_catalog(Path(__file__).resolve().parents[1] / "src" / "providers" / "catalog.json")

    assert {entry.name for entry in entries} == {"deepseek", "openrouter", "qwen"}
    assert all(entry.base_url.startswith("https://") for entry in entries)


def test_catalog_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ProviderConfigurationError, match="catalog not found"):
        load_catalog(tmp_path / "nope.json")


def test_catalog_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text("{ not json }", encoding="utf-8")

    with pytest.raises(ProviderConfigurationError, match="not valid JSON"):
        load_catalog(path)


def test_catalog_requires_a_providers_list(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"other": []}), encoding="utf-8")

    with pytest.raises(ProviderConfigurationError, match="'providers' list"):
        load_catalog(path)


def test_catalog_capabilities_must_be_known(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "name": "custom",
                        "base_url": "https://example.test/v1",
                        "api_key_env": "CUSTOM_KEY",
                        "default_model": "custom-1",
                        "capabilities": ["text", "hearing"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProviderConfigurationError, match="Unknown capability 'hearing'"):
        load_catalog(path)
