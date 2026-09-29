"""Structural video analysis for text-only providers.

Text-only APIs cannot look at a recording at all. Rather than failing, this
strategy reports what can be measured without vision: duration, resolution,
resolution changes (a proxy for page transitions) and a sampled frame
timeline. That is enough to anchor test scenarios in time, and the report says
explicitly that visual analysis was skipped.
"""

from __future__ import annotations

import logging
from pathlib import Path

from analysis.video.base import VideoAnalysisError, VideoAnalyzer
from settings import VideoSettings
from utils.opencv import load_cv2

_log = logging.getLogger(__name__)

_DEFAULT_FPS = 30
_RECOMMENDED_PROVIDERS = "google_genai (native upload) or openai (frame sampling)"


class MetadataOnlyAnalyzer(VideoAnalyzer):
    name = "metadata_only"

    def __init__(self, provider_name: str, settings: VideoSettings) -> None:
        self._provider_name = provider_name
        self._settings = settings

    def describe(self) -> str:
        return f"{self.name} ({self._provider_name} has no vision support)"

    def analyze(self, video_path: Path) -> str:
        cv2 = load_cv2()
        video = cv2.VideoCapture(str(video_path))
        if not video.isOpened():
            raise VideoAnalysisError(f"Could not open video file {video_path.name}")

        try:
            fps = video.get(cv2.CAP_PROP_FPS) or _DEFAULT_FPS
            if fps <= 0:
                fps = _DEFAULT_FPS
            total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            timeline = self._sample_timeline(cv2, video, fps)
        finally:
            video.release()

        return self._render(video_path, fps, total_frames, width, height, timeline)

    def _sample_timeline(self, cv2, video, fps: float) -> list[str]:
        """Frame timestamps and resolution changes, one entry per sampled frame."""
        interval = max(int(fps * self._settings.frame_interval_seconds), 1)
        entries: list[str] = []
        previous_resolution: str | None = None
        index = 0

        while True:
            ok, frame = video.read()
            if not ok:
                break

            if index % interval == 0:
                height, width = frame.shape[:2]
                resolution = f"{width}x{height}"
                change = (
                    f" (resolution change from {previous_resolution})"
                    if previous_resolution and resolution != previous_resolution
                    else ""
                )
                timestamp = index / fps
                entries.append(
                    f"({int(timestamp // 60):02d}:{int(timestamp % 60):02d}) "
                    f"Frame {index}: {resolution}{change}"
                )
                previous_resolution = resolution

            index += 1

        return entries

    def _render(
        self,
        video_path: Path,
        fps: float,
        total_frames: int,
        width: int,
        height: int,
        timeline: list[str],
    ) -> str:
        duration_seconds = total_frames / fps if fps > 0 else 0
        size_mb = video_path.stat().st_size / (1024 * 1024)

        return (
            "VIDEO METADATA ANALYSIS (text-only — provider does not support vision)\n"
            f"{'=' * 60}\n"
            f"File: {video_path.name}\n"
            f"Duration: {int(duration_seconds // 60)}m {int(duration_seconds % 60)}s "
            f"({total_frames} frames @ {fps:.1f} fps)\n"
            f"Resolution: {width}x{height}\n"
            f"File Size: {size_mb:.1f} MB\n"
            f"Sampled frames (every {self._settings.frame_interval_seconds}s): {len(timeline)}\n"
            f"{'=' * 60}\n\n"
            f"FRAME TIMELINE:\n"
            f"{chr(10).join(timeline)}\n\n"
            f"NOTE: This is a structural-only analysis. The configured provider "
            f"('{self._provider_name}') does not support vision/multimodal inputs. "
            f"For full visual analysis (UI elements, workflows, interactions), use "
            f"{_RECOMMENDED_PROVIDERS}.\n"
        )
