"""Providers that speak the OpenAI protocol with a custom base URL.

Everything that only differs by base URL, API key variable and capabilities is
declared in ``catalog.json`` — adding one is a configuration change, not a code
change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from providers.base import Capabilities, LLMProvider, ProviderConfigurationError
from providers.chat_model import init_chat_model

_REQUIRED_KEYS = ("name", "base_url", "api_key_env", "default_model")


@dataclass(frozen=True)
class CatalogEntry:
    """One declarative OpenAI-compatible provider."""

    name: str
    base_url: str
    api_key_env: str
    default_model: str
    capabilities: Capabilities = field(default_factory=Capabilities)
    model_capabilities: Mapping[str, Capabilities] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "CatalogEntry":
        missing = [key for key in _REQUIRED_KEYS if not str(raw.get(key, "")).strip()]
        if missing:
            label = raw.get("name") or "<unnamed entry>"
            raise ProviderConfigurationError(
                f"Catalog entry '{label}' is missing required keys: {', '.join(missing)}"
            )

        model_capabilities = {
            str(model): Capabilities.from_names(names)
            for model, names in (raw.get("model_capabilities") or {}).items()
        }

        return cls(
            name=str(raw["name"]).strip(),
            base_url=str(raw["base_url"]).strip(),
            api_key_env=str(raw["api_key_env"]).strip(),
            default_model=str(raw["default_model"]).strip(),
            capabilities=Capabilities.from_names(raw.get("capabilities") or ["text"]),
            model_capabilities=model_capabilities,
        )

    def to_provider(self) -> "OpenAICompatibleProvider":
        return OpenAICompatibleProvider(self)


class OpenAICompatibleProvider(LLMProvider):
    """An ``LLMProvider`` backed by one :class:`CatalogEntry`."""

    def __init__(self, entry: CatalogEntry) -> None:
        self.entry = entry

    @property
    def name(self) -> str:  # type: ignore[override]
        return self.entry.name

    @property
    def default_model(self) -> str:  # type: ignore[override]
        return self.entry.default_model

    @property
    def api_key_env(self) -> str:  # type: ignore[override]
        return self.entry.api_key_env

    @property
    def capabilities(self) -> Capabilities:  # type: ignore[override]
        return self.entry.capabilities

    def capabilities_for(self, model: Optional[str] = None) -> Capabilities:
        """Per-model overrides win over the provider-wide capabilities."""
        if model and model in self.entry.model_capabilities:
            return self.entry.model_capabilities[model]
        return self.entry.capabilities

    def create_chat_model(self, model: str, api_key: Optional[str]) -> BaseChatModel:
        return init_chat_model(model, "openai", api_key, base_url=self.entry.base_url)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"OpenAICompatibleProvider({self.name} -> {self.entry.base_url})"


def load_catalog(path: Path) -> list[CatalogEntry]:
    """Read and validate a provider catalog file."""
    if not path.is_file():
        raise ProviderConfigurationError(f"Provider catalog not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProviderConfigurationError(f"Provider catalog {path} is not valid JSON: {exc}") from exc

    entries = raw.get("providers")
    if not isinstance(entries, list):
        raise ProviderConfigurationError(
            f"Provider catalog {path} must contain a 'providers' list."
        )

    return [CatalogEntry.from_dict(entry) for entry in entries]
