"""Video analysis strategies and the factory that selects between them."""

from analysis.video.base import VideoAnalysisError, VideoAnalyzer
from analysis.video.factory import choose_video_analyzer

__all__ = ["VideoAnalysisError", "VideoAnalyzer", "choose_video_analyzer"]
