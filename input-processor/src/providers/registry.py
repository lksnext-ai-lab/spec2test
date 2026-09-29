"""Provider registry: name -> provider, and name/model -> usable chat model."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Mapping, Optional

from settings import LlmSettings

from providers.base import Capabilities, LLMHandle, LLMProvider, ProviderConfigurationError
from providers.native import NATIVE_PROVIDERS
from providers.openai_compatible import load_catalog

_log = logging.getLogger(__name__)

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"


class ProviderRegistry:
    """Looks up providers by name and builds their chat models."""

    def __init__(self, providers: Iterable[LLMProvider] = ()) -> None:
        self._providers: dict[str, LLMProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: LLMProvider, *, replace: bool = False) -> None:
        """Add a provider, refusing silent duplicates."""
        name = provider.name
        if not name:
            raise ProviderConfigurationError("A provider must declare a name.")
        if name in self._providers and not replace:
            raise ProviderConfigurationError(
                f"Provider '{name}' is already registered. "
                "Pass replace=True to override it deliberately."
            )
        self._providers[name] = provider

    def get(self, name: str) -> LLMProvider:
        """Return the provider registered under ``name``."""
        key = (name or "").strip()
        if not key:
            raise ProviderConfigurationError(
                f"No provider configured. Available providers: {self._available_text()}"
            )
        try:
            return self._providers[key]
        except KeyError:
            raise ProviderConfigurationError(
                f"Unknown LLM provider '{name}'. Available providers: {self._available_text()}"
            ) from None

    def available(self) -> tuple[str, ...]:
        """Registered provider names, alphabetically."""
        return tuple(sorted(self._providers))

    def capabilities_for(self, llm: LlmSettings) -> Capabilities:
        """Capabilities of the configured provider/model pair."""
        provider = self.get(llm.provider)
        return provider.capabilities_for(provider.resolve_model(llm.model))

    def resolve(self, llm: LlmSettings, env: Mapping[str, str]) -> LLMHandle:
        """Build the chat model for ``llm``, checking its API key first."""
        provider = self.get(llm.provider)
        model = provider.resolve_model(llm.model)
        api_key = provider.resolve_api_key(env)
        capabilities = provider.capabilities_for(model)

        _log.info(
            "Using provider '%s' with model '%s' (capabilities: %s)",
            provider.name,
            model,
            capabilities,
        )
        chat_model = provider.create_chat_model(model, api_key)
        return LLMHandle(
            provider_name=provider.name,
            model=model,
            capabilities=capabilities,
            chat_model=chat_model,
            api_key=api_key,
        )

    def _available_text(self) -> str:
        names = self.available()
        return ", ".join(names) if names else "none registered"


def build_default_registry(catalog_path: Optional[Path] = None) -> ProviderRegistry:
    """Registry with the native integrations plus every catalog entry."""
    registry = ProviderRegistry(NATIVE_PROVIDERS)
    for entry in load_catalog(catalog_path or DEFAULT_CATALOG_PATH):
        # A catalog entry may deliberately redefine a native provider.
        registry.register(entry.to_provider(), replace=True)
    return registry
