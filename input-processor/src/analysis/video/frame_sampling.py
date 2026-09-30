"""Video analysis by sampling frames and sending them as images."""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from analysis.video.base import VideoAnalysisError, VideoAnalyzer
from analysis.video.frames import extract_frames, sample_evenly
from progress import reporter
from settings import VideoSettings
from utils.text import to_text

_log = logging.getLogger(__name__)


class FrameSamplingAnalyzer(VideoAnalyzer):
    """Analyse a recording as a sequence of still frames.

    Used for providers that accept images but not video, where the interaction
    timeline is reconstructed from evenly spaced screenshots.
    """

    name = "frame_sampling"

    def __init__(self, llm: BaseChatModel, prompt: str, settings: VideoSettings) -> None:
        self._llm = llm
        self._prompt = prompt
        self._settings = settings

    def analyze(self, video_path: Path) -> str:
        reporter().stage("Extracting video frames")
        _log.info("Extracting frames from %s...", video_path.name)
        frames = extract_frames(video_path, interval_seconds=self._settings.frame_interval_seconds)
        if not frames:
            raise VideoAnalysisError(
                f"No frames could be extracted from {video_path.name}. "
                "The file may be corrupted or use an unsupported codec."
            )

        sampled = sample_evenly(frames, self._settings.max_frames)
        if len(sampled) != len(frames):
            _log.warning(
                "Too many frames (%s). Sampling down to %s.", len(frames), len(sampled)
            )
        reporter().stage(f"Analysing {len(sampled)} frames with the model")
        _log.info("Sending %s frames to the model.", len(sampled))

        return to_text(self._llm.invoke([HumanMessage(content=self._build_content(sampled))]).content)

    def describe(self) -> str:
        return f"{self.name} (every {self._settings.frame_interval_seconds}s, max {self._settings.max_frames})"

    def _build_content(self, frames: list[str]) -> list[dict]:
        content: list[dict] = [{"type": "text", "text": self._prompt}]
        content.extend(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame}"},
            }
            for frame in frames
        )
        return content
