"""Per-project runtime: caches, LLM clients and the processing stack.

Every project gets its own instance, built on first use and cached afterwards.
Different projects share nothing but the provider registry, so they can be
processed concurrently; requests for the *same* project are serialized by the
project's lock.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Mapping, Optional

from analysis.document_summarizer import DocumentSummarizer
from analysis.image_describer import ImageDescriber
from analysis.video.factory import VIDEO_PROMPT_NAME, choose_video_analyzer
from cache.preprocessed import PreprocessedStore
from cache.repository import CacheRepository
from handlers.base import FileHandler
from handlers.markdown_handler import MarkdownHandler
from handlers.pdf_handler import PdfHandler
from handlers.registry import HandlerRegistry
from handlers.text_handler import TextHandler
from handlers.video_handler import VideoHandler
from preprocessing.markdown_images import MarkdownImageEnricher
from preprocessing.pdf_to_markdown import PdfToMarkdown
from processing_service import ProcessingService
from projects.model import Project
from projects.registry import ProjectRegistry
from prompts import load
from providers.base import LLMHandle
from providers.registry import ProviderRegistry
from settings import LlmSettings, Settings

_log = logging.getLogger(__name__)


class ProjectRuntime:
    """Everything needed to process one project's files."""

    def __init__(
        self,
        project: Project,
        providers: ProviderRegistry,
        env: Mapping[str, str],
        settings: Settings,
    ) -> None:
        self.project = project
        self.providers = providers
        self.settings = settings
        self._env = env
        self._handles: dict[tuple[str, str], LLMHandle] = {}
        self._service: Optional[ProcessingService] = None
        self._lock = threading.Lock()

    @property
    def lock(self) -> threading.Lock:
        """Guards this project's files: same project serial, others parallel."""
        return self._lock

    def handle_for(self, llm: LlmSettings) -> LLMHandle:
        """Chat model for these settings, cached per ``(provider, model)``."""
        provider = self.providers.get(llm.provider)
        model = provider.resolve_model(llm.model)
        key = (provider.name, model)

        if key not in self._handles:
            self._handles[key] = self.providers.resolve(
                LlmSettings(provider=provider.name, model=model), self._env
            )
        return self._handles[key]

    def main_handle(self) -> LLMHandle:
        return self.handle_for(self.project.llm)

    def vision_handle(self) -> Optional[LLMHandle]:
        """Model used to describe images, or ``None`` when none can.

        Defaults to the main model when it accepts images; a project can point
        at a different vision model explicitly.
        """
        if self.project.vision is not None:
            return self.handle_for(self.project.vision)

        main = self.main_handle()
        return main if main.capabilities.images else None

    def service(self) -> ProcessingService:
        """The processing stack, built once per project."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self) -> ProcessingService:
        main = self.main_handle()
        vision = self.vision_handle()
        if vision is None:
            _log.warning(
                "Project '%s': provider '%s' cannot describe images, so PDF and "
                "Markdown image enrichment is disabled.",
                self.project.name,
                main.provider_name,
            )

        summarizer = DocumentSummarizer(main.chat_model)
        describer = ImageDescriber(vision.chat_model) if vision else None
        store = PreprocessedStore.in_directory(self.project.preprocessed)

        handlers = HandlerRegistry(
            self._build_handlers(main, describer, summarizer, store)
        )

        _log.info(
            "Project '%s' ready: llm=%s vision=%s",
            self.project.name,
            main.label,
            vision.label if vision else "disabled",
        )

        return ProcessingService(
            input_dir=self.project.inputs,
            cache=CacheRepository(self.project.cache),
            handlers=handlers,
            provider=main.provider_name,
            model=main.model,
            preprocessed=store,
        )

    def _build_handlers(
        self,
        main: LLMHandle,
        describer: Optional[ImageDescriber],
        summarizer: DocumentSummarizer,
        store: PreprocessedStore,
    ) -> list[FileHandler]:
        vision = self.vision_handle()
        vision_provider = vision.provider_name if vision else ""
        vision_model = vision.model if vision else ""

        return [
            VideoHandler(
                choose_video_analyzer(
                    llm=main,
                    settings=self.settings.video,
                    work_dir=self.project.segments_dir,
                    prompt=load(VIDEO_PROMPT_NAME),
                )
            ),
            PdfHandler(
                summarizer,
                converter=PdfToMarkdown(store, describer, vision_provider, vision_model)
                if describer
                else None,
            ),
            MarkdownHandler(
                summarizer,
                enricher=MarkdownImageEnricher(store, describer, vision_provider, vision_model)
                if describer
                else None,
            ),
            TextHandler(summarizer),
        ]


class RuntimePool:
    """Keeps one :class:`ProjectRuntime` per configured project."""

    def __init__(
        self,
        projects: ProjectRegistry,
        providers: ProviderRegistry,
        env: Optional[Mapping[str, str]] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.projects = projects
        self.providers = providers
        self.settings = settings or Settings.from_env()
        self._env = os.environ if env is None else env
        self._runtimes: dict[str, ProjectRuntime] = {}
        self._lock = threading.Lock()

    def for_name(self, name: str) -> ProjectRuntime:
        """Runtime of the named project; raises when it is not configured."""
        return self.for_project(self.projects.get(name))

    def for_project(self, project: Project) -> ProjectRuntime:
        with self._lock:
            runtime = self._runtimes.get(project.name)
            if runtime is None:
                runtime = ProjectRuntime(project, self.providers, self._env, self.settings)
                self._runtimes[project.name] = runtime
            return runtime

    def project_names(self) -> tuple[str, ...]:
        return self.projects.names()
