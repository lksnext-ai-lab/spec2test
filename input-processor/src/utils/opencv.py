"""Lazy access to OpenCV.

``cv2`` is a heavy import and is only needed when a video is actually read, so
modules import it through this helper instead of at module scope. That keeps
import-time cheap and lets the test suite run without OpenCV installed.
"""

from __future__ import annotations

from typing import Any


def load_cv2() -> Any:
    """Import and return the ``cv2`` module."""
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError(
            "OpenCV is required for video frame extraction and splitting. "
            "Install the input-processor requirements (opencv-python-headless)."
        ) from exc
    return cv2
