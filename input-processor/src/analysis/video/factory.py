"""Choose a video analysis strategy from capabilities, not provider names."""

from __future__ import annotations

import logging
from pathlib import Path

from analysis.video.base import VideoAnalyzer
from analysis.video.frame_sampling import FrameSamplingAnalyzer
from analysis.video.gemini_file_api import GeminiFileApiAnalyzer
from analysis.video.inline_video import InlineVideoAnalyzer
from analysis.video.metadata_only import MetadataOnlyAnalyzer
from analysis.video.segmenter import VideoSegmenter
from providers.base import Capabilities, LLMHandle
from settings import VideoSettings

_log = logging.getLogger(__name__)

VIDEO_PROMPT_NAME = "video"


def choose_video_analyzer(
    llm: LLMHandle,
    settings: VideoSettings,
    work_dir: Path,
    prompt: str,
) -> VideoAnalyzer:
    """Pick the best strategy for these capabilities.

    Preference order: native upload, then inline video, then frame sampling,
    and metadata-only as the last resort for text-only providers.
    """
    analyzer = _select(llm.capabilities, llm, settings, work_dir, prompt)
    _log.info("Video analysis strategy: %s", analyzer.describe())
    return analyzer


def _select(
    capabilities: Capabilities,
    llm: LLMHandle,
    settings: VideoSettings,
    work_dir: Path,
    prompt: str,
) -> VideoAnalyzer:
    if capabilities.video_upload:
        return GeminiFileApiAnalyzer(
            model=llm.model,
            api_key=llm.api_key or "",
            prompt=prompt,
        )

    if capabilities.video_inline:
        return InlineVideoAnalyzer(
            llm=llm.chat_model,
            prompt=prompt,
            settings=settings,
            segmenter=VideoSegmenter(
                work_dir=work_dir,
                require_audio=settings.require_audio,
            ),
        )

    if capabilities.images:
        return FrameSamplingAnalyzer(llm=llm.chat_model, prompt=prompt, settings=settings)

    return MetadataOnlyAnalyzer(provider_name=llm.provider_name, settings=settings)
