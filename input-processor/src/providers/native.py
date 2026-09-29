"""Providers with a dedicated LangChain integration."""

from __future__ import annotations

from typing import ClassVar, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from providers.base import Capabilities, LLMProvider
from providers.chat_model import init_chat_model


class GoogleGenAIProvider(LLMProvider):
    """Google Gemini: text, images and native video upload via the File API."""

    name: ClassVar[str] = "google_genai"
    default_model: ClassVar[str] = "gemini-2.0-flash"
    api_key_env: ClassVar[Optional[str]] = "GOOGLE_API_KEY"
    capabilities: ClassVar[Capabilities] = Capabilities(
        text=True, images=True, video_upload=True
    )

    def create_chat_model(self, model: str, api_key: Optional[str]) -> BaseChatModel:
        return init_chat_model(model, "google_genai", api_key)


class OpenAIProvider(LLMProvider):
    """OpenAI chat models: text and images (videos are sampled into frames)."""

    name: ClassVar[str] = "openai"
    default_model: ClassVar[str] = "gpt-4o-mini"
    api_key_env: ClassVar[Optional[str]] = "OPENAI_API_KEY"
    capabilities: ClassVar[Capabilities] = Capabilities(text=True, images=True)

    def create_chat_model(self, model: str, api_key: Optional[str]) -> BaseChatModel:
        return init_chat_model(model, "openai", api_key)


class AnthropicProvider(LLMProvider):
    """Anthropic chat models: text and images (videos are sampled into frames)."""

    name: ClassVar[str] = "anthropic"
    default_model: ClassVar[str] = "claude-sonnet-5"
    api_key_env: ClassVar[Optional[str]] = "ANTHROPIC_API_KEY"
    capabilities: ClassVar[Capabilities] = Capabilities(text=True, images=True)

    def create_chat_model(self, model: str, api_key: Optional[str]) -> BaseChatModel:
        return init_chat_model(model, "anthropic", api_key)


NATIVE_PROVIDERS: tuple[LLMProvider, ...] = (
    GoogleGenAIProvider(),
    OpenAIProvider(),
    AnthropicProvider(),
)
