"""Frame extraction helpers for providers that analyse videos as images."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from utils.opencv import load_cv2

_log = logging.getLogger(__name__)

MAX_WIDTH = 480
JPEG_QUALITY = 70


def extract_frames(video_path: Path, interval_seconds: int = 2) -> list[str]:
    """Return base64-encoded JPEG frames sampled every ``interval_seconds``."""
    cv2 = load_cv2()
    video = cv2.VideoCapture(str(video_path))
    if not video.isOpened():
        _log.error("Could not open video file %s", video_path)
        return []

    fps = video.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30  # Default fallback for containers without a reported frame rate.

    frame_interval = max(int(fps * interval_seconds), 1)
    frames: list[str] = []
    index = 0

    try:
        while video.isOpened():
            ok, frame = video.read()
            if not ok:
                break
            if index % frame_interval == 0:
                frames.append(_encode_frame(cv2, frame))
            index += 1
    finally:
        video.release()

    return frames


def sample_evenly(frames: list[str], max_frames: int) -> list[str]:
    """Reduce ``frames`` to at most ``max_frames`` evenly spaced entries."""
    if max_frames <= 0 or len(frames) <= max_frames:
        return frames

    step = max(len(frames) // max_frames, 1)
    return frames[::step][:max_frames]


def _encode_frame(cv2: Any, frame: Any) -> str:
    height, width = frame.shape[:2]
    if width > MAX_WIDTH:
        scale = MAX_WIDTH / width
        frame = cv2.resize(frame, (MAX_WIDTH, int(height * scale)))

    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    if not ok:  # pragma: no cover - only reachable with a broken codec
        raise RuntimeError("Failed to encode a video frame as JPEG.")
    return base64.b64encode(buffer).decode("utf-8")
