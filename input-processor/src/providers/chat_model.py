"""Single place where LangChain chat models are constructed.

Keeping the defaults here means every provider gets the same generation
settings (deterministic output, bounded retries) and providers only have to
declare *which* LangChain integration and base URL they use.
"""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from providers.base import ProviderConfigurationError

DEFAULT_MODEL_KWARGS: dict[str, Any] = {
    "temperature": 0,
    "max_tokens": None,
    "timeout": None,
    "max_retries": 2,
}


def init_chat_model(
    model: str,
    model_provider: str,
    api_key: Optional[str] = None,
    **overrides: Any,
) -> BaseChatModel:
    """Create a LangChain chat model, translating import errors into guidance."""
    try:
        from langchain.chat_models import init_chat_model as _init_chat_model
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ProviderConfigurationError(
            "The 'langchain' package is required to talk to LLM providers. "
            "Install the input-processor requirements."
        ) from exc

    kwargs = {**DEFAULT_MODEL_KWARGS, **overrides}
    if api_key:
        kwargs["api_key"] = api_key

    try:
        return _init_chat_model(model, model_provider=model_provider, **kwargs)
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ProviderConfigurationError(
            f"Provider '{model_provider}' requires an extra LangChain integration "
            f"package that is not installed: {exc}"
        ) from exc
