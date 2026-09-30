"""Provider abstraction: capabilities, chat model construction, API keys.

Every provider knows which modalities it supports. The rest of the code base
never asks *which* provider is configured — only what it can do — so adding a
provider never means editing an ``if provider == ...`` branch elsewhere.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Iterable, Mapping, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel


class ProviderConfigurationError(ValueError):
    """Raised for an unknown provider or a missing API key."""


@dataclass(frozen=True)
class Capabilities:
    """The modalities a provider/model combination accepts as input."""

    text: bool = True
    images: bool = False
    video_inline: bool = False
    video_upload: bool = False

    _NAMES: ClassVar[Sequence[str]] = ("text", "images", "video_inline", "video_upload")

    @classmethod
    def from_names(cls, names: Iterable[str]) -> "Capabilities":
        """Build capabilities from declarative names (e.g. a catalog entry)."""
        known = dict.fromkeys(cls._NAMES, False)
        for raw_name in names:
            name = str(raw_name).strip().lower()
            if name not in known:
                raise ProviderConfigurationError(
                    f"Unknown capability '{raw_name}'. Known capabilities: "
                    f"{', '.join(cls._NAMES)}"
                )
            known[name] = True
        return cls(**known)

    def names(self) -> tuple[str, ...]:
        """Capability names that are enabled, in a stable order."""
        return tuple(name for name in self._NAMES if getattr(self, name))

    def __str__(self) -> str:
        return ", ".join(self.names()) or "none"


@dataclass(frozen=True)
class LLMHandle:
    """A chat model together with the metadata that describes it."""

    provider_name: str
    model: str
    capabilities: Capabilities
    chat_model: BaseChatModel
    api_key: Optional[str] = None

    @property
    def label(self) -> str:
        """Human readable identifier used in logs and cache front-matter."""
        return f"{self.provider_name}:{self.model}"


class LLMProvider(ABC):
    """Base class for every provider.

    Subclasses declare their identity and capabilities as class attributes and
    implement :meth:`create_chat_model`. Instances are stateless, which keeps
    them cheap to share and easy to register.
    """

    name: ClassVar[str] = ""
    default_model: ClassVar[str] = ""
    api_key_env: ClassVar[Optional[str]] = None
    capabilities: ClassVar[Capabilities] = Capabilities()

    def capabilities_for(self, model: Optional[str] = None) -> Capabilities:
        """Capabilities of this provider, optionally refined for one model."""
        return self.capabilities

    def resolve_model(self, model: Optional[str]) -> str:
        """Return the configured model, falling back to the provider default."""
        resolved = (model or "").strip() or self.default_model
        if not resolved:
            raise ProviderConfigurationError(f"Provider '{self.name}' has no default model.")
        return resolved

    def resolve_api_key(self, env: Mapping[str, str]) -> Optional[str]:
        """Return the API key from ``env``, or ``None`` for keyless providers."""
        if self.api_key_env is None:
            return None

        key = (env.get(self.api_key_env) or "").strip()
        if not key:
            raise ProviderConfigurationError(
                f"Missing API key for provider '{self.name}': "
                f"set {self.api_key_env} in your .env file."
            )
        return key

    @abstractmethod
    def create_chat_model(self, model: str, api_key: Optional[str]) -> BaseChatModel:
        """Build the LangChain chat model for ``model``."""
