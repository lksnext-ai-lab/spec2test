"""Strategy interface for video analysis."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class VideoAnalysisError(RuntimeError):
    """Raised when a video cannot be analyzed at all."""


class VideoAnalyzer(ABC):
    """Turns a video file into a textual description of the recorded session."""

    name: str = ""

    @abstractmethod
    def analyze(self, video_path: Path) -> str:
        """Return the analysis of ``video_path``."""

    def describe(self) -> str:
        """One-line description used in logs."""
        return self.name
