"""Handler for video recordings."""

from __future__ import annotations

from analysis.video.base import VideoAnalyzer
from cache.source import SourceFile
from handlers.base import FileHandler, HandlerContext


class VideoHandler(FileHandler):
    """Describes the browser session recorded in a video file."""

    name = "video"
    extensions = (".mp4",)

    def __init__(self, analyzer: VideoAnalyzer) -> None:
        self._analyzer = analyzer

    def handle(self, source: SourceFile, context: HandlerContext) -> str:
        return self._analyzer.analyze(source.path)

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"video via {self._analyzer.describe()}"
