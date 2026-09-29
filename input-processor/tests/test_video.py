"""Video strategies are chosen by capability, and their logic is testable."""

from __future__ import annotations

from pathlib import Path

import pytest

from analysis.video.base import VideoAnalysisError
from analysis.video.factory import choose_video_analyzer
from analysis.video.frame_sampling import FrameSamplingAnalyzer
from analysis.video.gemini_file_api import GeminiFileApiAnalyzer
from analysis.video.inline_video import InlineVideoAnalyzer
from analysis.video.metadata_only import MetadataOnlyAnalyzer
from analysis.video.segmenter import VideoSegmenter, format_mmss, offset_timestamps
from analysis.video.frames import sample_evenly
from providers.base import Capabilities, LLMHandle
from settings import VideoSettings
from support import FakeCv2, StubChatModel


def handle(capabilities: Capabilities, model: str = "model") -> LLMHandle:
    return LLMHandle(
        provider_name="stub",
        model=model,
        capabilities=capabilities,
        chat_model=StubChatModel(),
        api_key="key",
    )


@pytest.mark.parametrize(
    ("capabilities", "expected"),
    [
        (Capabilities(text=True, images=True, video_upload=True), GeminiFileApiAnalyzer),
        (Capabilities(text=True, images=True, video_inline=True), InlineVideoAnalyzer),
        (Capabilities(text=True, images=True), FrameSamplingAnalyzer),
        (Capabilities(text=True), MetadataOnlyAnalyzer),
    ],
)
def test_factory_selects_by_capability(tmp_path: Path, capabilities, expected) -> None:
    analyzer = choose_video_analyzer(
        handle(capabilities), VideoSettings(), tmp_path, prompt="prompt"
    )

    assert isinstance(analyzer, expected)


def test_video_upload_wins_over_inline(tmp_path: Path) -> None:
    analyzer = choose_video_analyzer(
        handle(Capabilities(text=True, images=True, video_inline=True, video_upload=True)),
        VideoSettings(),
        tmp_path,
        prompt="prompt",
    )

    assert isinstance(analyzer, GeminiFileApiAnalyzer)


def test_gemini_analyzer_requires_a_key() -> None:
    with pytest.raises(VideoAnalysisError, match="requires an API key"):
        GeminiFileApiAnalyzer(model="gemini", api_key="", prompt="prompt")


def test_segmenter_work_dir_is_derived_from_the_project(tmp_path: Path) -> None:
    analyzer = choose_video_analyzer(
        handle(Capabilities(text=True, video_inline=True)),
        VideoSettings(),
        tmp_path,
        prompt="prompt",
    )

    assert isinstance(analyzer, InlineVideoAnalyzer)
    assert analyzer.describe().startswith("inline_video (segment")


@pytest.mark.parametrize(
    ("seconds", "expected"), [(0, "0:00"), (59, "0:59"), (60, "1:00"), (3599, "59:59")]
)
def test_format_mmss(seconds: int, expected: str) -> None:
    assert format_mmss(seconds) == expected


def test_offset_timestamps_shifts_single_and_range_markers() -> None:
    text = "Intro (0:00) then (0:08-0:15) and a final note (1:05)."

    shifted = offset_timestamps(text, 60)

    assert shifted == "Intro (1:00) then (1:08-1:15) and a final note (2:05)."


def test_offset_timestamps_ignores_parentheses_that_are_not_timestamps() -> None:
    text = "A note (see figure 2) and (12) alone."

    assert offset_timestamps(text, 30) == text


def test_offset_timestamps_without_offset_is_identity() -> None:
    text = "Action (0:03)"

    assert offset_timestamps(text, 0) is text


def test_sample_evenly_keeps_short_lists_untouched() -> None:
    frames = ["a", "b", "c"]

    assert sample_evenly(frames, 5) == frames
    assert sample_evenly(frames, 0) == frames


def test_sample_evenly_reduces_long_lists() -> None:
    frames = [str(index) for index in range(100)]

    sampled = sample_evenly(frames, 20)

    assert len(sampled) == 20
    assert sampled[0] == "0"
    assert sampled[1] == "5"


@pytest.mark.parametrize(
    ("settings", "size_mb", "duration", "expected"),
    [
        (VideoSettings(), 1.0, 10, False),
        (VideoSettings(), 20.0, 10, True),
        (VideoSettings(), 1.0, 120, True),
        (VideoSettings(split_by_duration=False), 1.0, 120, False),
        (VideoSettings(force_split=True), 1.0, 10, True),
    ],
)
def test_should_split(tmp_path, monkeypatch, settings, size_mb, duration, expected) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x" * int(size_mb * 1024 * 1024))
    segmenter = VideoSegmenter(tmp_path / "segments")

    monkeypatch.setattr(
        VideoSegmenter, "duration_seconds", lambda self, path: duration
    )

    assert segmenter.should_split(video, settings) is expected


def test_frames_are_extracted_at_the_configured_interval(monkeypatch, tmp_path) -> None:
    import analysis.video.frames as frames_module

    fake = FakeCv2(frame_count=20, fps=10)  # 2s interval -> every 20th frame
    monkeypatch.setattr(frames_module, "load_cv2", lambda: fake)
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")

    frames = frames_module.extract_frames(video, interval_seconds=2)

    assert frames == ["anBlZw=="]  # base64 of the faked JPEG bytes


def test_metadata_analysis_reports_resolution_changes(monkeypatch, tmp_path) -> None:
    import analysis.video.metadata_only as metadata_module

    resolutions = [(640, 480)] * 10 + [(800, 600)] * 10
    fake = FakeCv2(fps=1, resolutions=resolutions)  # 2s interval -> every 2nd frame
    monkeypatch.setattr(metadata_module, "load_cv2", lambda: fake)
    video = tmp_path / "session.mp4"
    video.write_bytes(b"video")

    report = MetadataOnlyAnalyzer(provider_name="deepseek", settings=VideoSettings()).analyze(video)

    assert "VIDEO METADATA ANALYSIS" in report
    assert "does not support vision" in report
    assert "(resolution change from 640x480)" in report
    assert "deepseek" in report
    assert "Sampled frames (every 2s): 10" in report
