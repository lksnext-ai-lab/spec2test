"""Splitting long videos into segments, and realigning their timestamps.

Used by providers that accept a video inline: those requests are limited by
payload size, so a large or long recording is cut into pieces, analysed one by
one, and the piece summaries are merged with continuous timestamps.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from settings import VideoSettings
from utils.opencv import load_cv2

_log = logging.getLogger(__name__)

_TIMESTAMP_RE = re.compile(r"\((\d{1,2}):(\d{2})(?:\s*-\s*(\d{1,2}):(\d{2}))?\)")
_DEFAULT_FPS = 30


def format_mmss(seconds: int) -> str:
    """Format ``seconds`` as ``MM:SS``."""
    return f"{seconds // 60}:{seconds % 60:02d}"


def offset_timestamps(text: str, offset_seconds: int) -> str:
    """Shift every ``(MM:SS)`` or ``(MM:SS-MM:SS)`` marker in ``text``.

    Segment summaries carry timestamps relative to their own start; this maps
    them back onto the timeline of the full recording.
    """
    if offset_seconds == 0:
        return text

    def shift(match: re.Match[str]) -> str:
        start = int(match.group(1)) * 60 + int(match.group(2)) + offset_seconds
        start_text = format_mmss(start)
        if match.group(3) is None:
            return f"({start_text})"

        end = int(match.group(3)) * 60 + int(match.group(4)) + offset_seconds
        return f"({start_text}-{format_mmss(end)})"

    return _TIMESTAMP_RE.sub(shift, text)


class VideoSegmenter:
    """Splits videos on disk and reports whether a split is worthwhile."""

    def __init__(self, work_dir: Path, require_audio: bool = True) -> None:
        self.work_dir = Path(work_dir)
        self.require_audio = require_audio
        self._seen_stems: set[str] = set()

    def should_split(self, video_path: Path, settings: VideoSettings) -> bool:
        """True when the recording is big or long enough to need segmenting."""
        if settings.force_split:
            return True

        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb >= settings.split_min_mb:
            return True

        if not settings.split_by_duration:
            return False

        duration = self.duration_seconds(video_path)
        return duration > 0 and duration > settings.segment_seconds

    def duration_seconds(self, video_path: Path) -> int:
        """Duration of ``video_path`` in seconds, or 0 when it is unknown."""
        cv2 = load_cv2()
        video = cv2.VideoCapture(str(video_path))
        if not video.isOpened():
            return 0

        try:
            fps = video.get(cv2.CAP_PROP_FPS) or _DEFAULT_FPS
            if fps <= 0:
                fps = _DEFAULT_FPS
            total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        finally:
            video.release()

        if total_frames <= 0:
            return 0
        return int(round(total_frames / fps))

    def split(self, video_path: Path, segment_seconds: int) -> list[Path]:
        """Split ``video_path`` and return the segment paths in order.

        ffmpeg is preferred because it preserves audio without re-encoding;
        OpenCV is the fallback and drops the audio track.
        """
        segment_dir = self._prepare_dir(video_path)
        self._seen_stems.add(video_path.stem)

        if self._split_with_ffmpeg(video_path, segment_dir, segment_seconds):
            segments = sorted(segment_dir.glob("*.mp4"))
            if segments:
                return segments

        if self.require_audio:
            raise RuntimeError(
                "Audio-preserving splitting requires ffmpeg. Install ffmpeg or "
                "set INPUT_PROCESSOR_VIDEO_REQUIRE_AUDIO=false to allow "
                "OpenCV splitting (audio is dropped)."
            )

        return self._split_with_cv2(video_path, segment_dir, segment_seconds)

    def cleanup(self, segments: list[Path]) -> None:
        """Delete segment files and their directory."""
        parent: Optional[Path] = None
        for segment in segments:
            parent = segment.parent
            try:
                segment.unlink()
            except OSError as exc:
                _log.debug("Could not remove segment %s: %s", segment, exc)

        if parent is not None:
            try:
                parent.rmdir()
            except OSError as exc:
                _log.debug("Could not remove segment directory %s: %s", parent, exc)

    def _prepare_dir(self, video_path: Path) -> Path:
        segment_dir = self.work_dir / video_path.stem
        segment_dir.mkdir(parents=True, exist_ok=True)
        for stale in segment_dir.glob("*.mp4"):
            try:
                stale.unlink()
            except OSError as exc:
                _log.debug("Could not remove stale segment %s: %s", stale, exc)
        return segment_dir

    def _split_with_ffmpeg(self, video_path: Path, segment_dir: Path, segment_seconds: int) -> bool:
        if shutil.which("ffmpeg") is None:
            return False

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-c",
            "copy",
            "-map",
            "0",
            "-f",
            "segment",
            "-segment_time",
            str(segment_seconds),
            "-reset_timestamps",
            "1",
            str(segment_dir / f"{video_path.stem}_%03d.mp4"),
        ]

        try:
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            _log.warning("ffmpeg split failed, falling back to OpenCV: %s", exc)
            return False

        return True

    def _split_with_cv2(self, video_path: Path, segment_dir: Path, segment_seconds: int) -> list[Path]:
        cv2 = load_cv2()
        video = cv2.VideoCapture(str(video_path))
        if not video.isOpened():
            raise RuntimeError(f"Could not open video file {video_path.name}")

        try:
            fps = video.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = _DEFAULT_FPS
            frames_per_segment = max(int(fps * segment_seconds), 1)
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

            _log.info("Splitting %s with OpenCV (audio will be dropped).", video_path.name)
            segments = self._write_segments(
                cv2, video, segment_dir, video_path.stem, frames_per_segment, fps, width, height
            )
        finally:
            video.release()

        if not segments:
            raise RuntimeError("No segments were created for the video.")
        return segments

    @staticmethod
    def _write_segments(
        cv2,
        video,
        segment_dir: Path,
        stem: str,
        frames_per_segment: int,
        fps: float,
        width: int,
        height: int,
    ) -> list[Path]:
        segments: list[Path] = []
        writer = None
        frame_index = 0

        try:
            while True:
                ok, frame = video.read()
                if not ok:
                    break

                if frame_index % frames_per_segment == 0:
                    if writer is not None:
                        writer.release()
                    segment_path = segment_dir / f"{stem}_part{len(segments) + 1:03d}.mp4"
                    writer = cv2.VideoWriter(
                        str(segment_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
                    )
                    if not writer.isOpened():
                        raise RuntimeError("Failed to open video writer for segment output.")
                    segments.append(segment_path)

                writer.write(frame)
                frame_index += 1
        finally:
            if writer is not None:
                writer.release()

        return segments
