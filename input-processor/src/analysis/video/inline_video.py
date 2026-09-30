"""Video analysis by sending the recording inline as a ``video_url`` block."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from analysis.video.base import VideoAnalyzer
from analysis.video.segmenter import VideoSegmenter, format_mmss, offset_timestamps
from progress import reporter
from prompts import render
from settings import VideoSettings
from utils.text import to_text

_log = logging.getLogger(__name__)


class InlineVideoAnalyzer(VideoAnalyzer):
    """Send the video as base64, splitting it first when it is too large."""

    name = "inline_video"

    def __init__(
        self,
        llm: BaseChatModel,
        prompt: str,
        settings: VideoSettings,
        segmenter: VideoSegmenter,
    ) -> None:
        self._llm = llm
        self._prompt = prompt
        self._settings = settings
        self._segmenter = segmenter

    def analyze(self, video_path: Path) -> str:
        if not self._segmenter.should_split(video_path, self._settings):
            return self._analyze_inline(video_path, self._prompt)

        _log.info(
            "Splitting %s into %ss segments before inline analysis.",
            video_path.name,
            self._settings.segment_seconds,
        )
        return self._analyze_segments(video_path)

    def describe(self) -> str:
        return f"{self.name} (segment {self._settings.segment_seconds}s)"

    def _analyze_inline(self, video_path: Path, prompt: str) -> str:
        encoded = base64.b64encode(video_path.read_bytes()).decode("utf-8")
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "video_url",
                    "video_url": {"url": f"data:video/mp4;base64,{encoded}"},
                },
            ]
        )
        return to_text(self._llm.invoke([message]).content)

    def _analyze_segments(self, video_path: Path) -> str:
        reporter().stage("Splitting video into segments")
        try:
            segments = self._segmenter.split(video_path, self._settings.segment_seconds)
        except Exception as exc:  # noqa: BLE001 - fall back to the whole file
            _log.warning("Video split failed, processing the whole file: %s", exc)
            return self._analyze_inline(video_path, self._prompt)

        if not segments:
            return self._analyze_inline(video_path, self._prompt)

        try:
            summaries = self._summarize_segments(segments)
        finally:
            self._segmenter.cleanup(segments)

        return self._consolidate(summaries)

    def _summarize_segments(self, segments: Sequence[Path]) -> list[str]:
        summaries: list[str] = []
        offset_seconds = 0
        total = len(segments)

        for index, segment in enumerate(segments, start=1):
            prompt = f"{self._prompt}\n\n" + render(
                "video_segment",
                index=index,
                total=total,
                offset=format_mmss(offset_seconds),
            )
            reporter().step(index, total, f"Analysing video segment {index}/{total}")
            _log.info("Processing segment %s/%s: %s", index, total, segment.name)
            summary = self._analyze_inline(segment, prompt)
            if offset_seconds > 0:
                summary = offset_timestamps(summary, offset_seconds)
            summaries.append(summary)

            duration = self._segmenter.duration_seconds(segment)
            offset_seconds += duration if duration > 0 else self._settings.segment_seconds

        return summaries

    def _consolidate(self, summaries: list[str]) -> str:
        merged = "\n\n".join(
            f"[Segment {index + 1}]\n{summary}" for index, summary in enumerate(summaries)
        )
        if not self._settings.consolidate:
            return merged

        reporter().stage("Consolidating segment summaries")
        message = HumanMessage(content=render("video_consolidation", segments=merged))
        return to_text(self._llm.invoke([message]).content)
