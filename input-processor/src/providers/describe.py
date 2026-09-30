"""Describe the available providers for UIs: capabilities, models, key status.

API keys are never included, only whether the variable is set.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from providers.base import LLMProvider
from providers.openai_compatible import OpenAICompatibleProvider
from providers.registry import ProviderRegistry

NATIVE_METADATA_PATH = Path(__file__).resolve().parent / "native.json"


def _native_models() -> dict[str, tuple[str, ...]]:
    raw = json.loads(NATIVE_METADATA_PATH.read_text(encoding="utf-8"))
    return {item["name"]: tuple(item.get("models") or ()) for item in raw["providers"]}


def _curated_models(provider: LLMProvider, native: Mapping[str, tuple[str, ...]]) -> tuple[str, ...]:
    if isinstance(provider, OpenAICompatibleProvider):
        models = provider.entry.models
    else:
        models = native.get(provider.name, ())
    if provider.default_model and provider.default_model not in models:
        models = (provider.default_model, *models)
    return models


def describe_providers(registry: ProviderRegistry, env: Mapping[str, str]) -> list[dict[str, Any]]:
    """One entry per registered provider, alphabetically."""
    native = _native_models()
    result: list[dict[str, Any]] = []
    for name in registry.available():
        provider = registry.get(name)
        key_env = provider.api_key_env
        result.append(
            {
                "name": provider.name,
                "api_key_env": key_env,
                "api_key_set": bool(key_env and (env.get(key_env) or "").strip()),
                "default_model": provider.default_model,
                "capabilities": list(provider.capabilities.names()),
                "models": [
                    {
                        "id": model,
                        "capabilities": list(provider.capabilities_for(model).names()),
                    }
                    for model in _curated_models(provider, native)
                ],
            }
        )
    return result
