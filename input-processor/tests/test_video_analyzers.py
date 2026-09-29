"""The video analysis strategies, exercised without cameras or networks."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from analysis.video.base import VideoAnalysisError
from analysis.video.frame_sampling import FrameSamplingAnalyzer
from analysis.video.gemini_file_api import GeminiFileApiAnalyzer
from analysis.video.inline_video import InlineVideoAnalyzer
from analysis.video.segmenter import VideoSegmenter
from settings import VideoSettings
from support import FakeCv2, StubChatModel


class FakeSegmenter:
    """Stands in for ffmpeg/OpenCV splitting: real files, no encoding."""

    def __init__(self, directory: Path, durations: dict[str, int] | None = None) -> None:
        self.directory = directory
        self.durations = durations or {}
        self.split_calls: list[Path] = []
        self.cleaned: list[list[Path]] = []
        self.splits = True
        self.fail_split = False

    def should_split(self, video: Path, settings: VideoSettings) -> bool:
        return self.splits

    def split(self, video: Path, seconds: int) -> list[Path]:
        self.split_calls.append(video)
        if self.fail_split:
            raise RuntimeError("ffmpeg is not installed")
        self.directory.mkdir(parents=True, exist_ok=True)
        segments = []
        for index in (1, 2):
            segment = self.directory / f"part-{index}.mp4"
            segment.write_bytes(b"segment")
            segments.append(segment)
        return segments

    def duration_seconds(self, video: Path) -> int:
        return self.durations.get(video.name, 60)

    def cleanup(self, segments: list[Path]) -> None:
        self.cleaned.append(list(segments))


def video_in(tmp_path: Path, name: str = "session.mp4") -> Path:
    path = tmp_path / name
    path.write_bytes(b"video-bytes")
    return path


def test_inline_analysis_sends_a_data_url(tmp_path: Path) -> None:
    model = StubChatModel("the user logs in")
    segmenter = FakeSegmenter(tmp_path / "segments")
    segmenter.splits = False
    analyzer = InlineVideoAnalyzer(model, "prompt", VideoSettings(), segmenter)

    result = analyzer.analyze(video_in(tmp_path))

    assert result == "the user logs in"
    assert model.call_count == 1  # one call: no split, no consolidation
    content = model.calls[0][0].content
    assert content[0] == {"type": "text", "text": "prompt"}
    assert content[1]["video_url"]["url"].startswith("data:video/mp4;base64,")


def test_segments_are_summarised_with_offsets_and_consolidated(tmp_path: Path) -> None:
    """The second segment's timestamps are shifted by the first segment's length."""
    model = StubChatModel()

    def respond(messages, **kwargs):
        from langchain_core.messages import AIMessage

        model.calls.append(list(messages))
        content = messages[0].content
        text = content[0]["text"] if isinstance(content, list) else content
        if "Segment 1 of 2" in text:
            return AIMessage(content="Login at (0:05)")
        if "Segment 2 of 2" in text:
            return AIMessage(content="Checkout at (0:07)")
        return AIMessage(content="consolidated timeline")

    model.invoke = respond  # type: ignore[method-assign]
    segmenter = FakeSegmenter(tmp_path / "segments", {"part-1.mp4": 45})
    analyzer = InlineVideoAnalyzer(model, "prompt", VideoSettings(), segmenter)

    result = analyzer.analyze(video_in(tmp_path))

    assert result == "consolidated timeline"
    assert segmenter.cleaned and len(segmenter.cleaned[0]) == 2
    # part-1 lasts 45s, so the second segment's timestamps move by 45s.
    consolidation = model.calls[-1][0].content
    assert "Login at (0:05)" in consolidation
    assert "Checkout at (0:52)" in consolidation
    assert "[Segment 1]" in consolidation and "[Segment 2]" in consolidation


def test_segments_are_concatenated_when_consolidation_is_off(tmp_path: Path) -> None:
    model = StubChatModel("summary")
    analyzer = InlineVideoAnalyzer(
        model, "prompt", VideoSettings(consolidate=False), FakeSegmenter(tmp_path / "segments")
    )

    result = analyzer.analyze(video_in(tmp_path))

    assert result == "[Segment 1]\nsummary\n\n[Segment 2]\nsummary"
    assert model.call_count == 2  # one per segment, no consolidation call


def test_a_failing_split_falls_back_to_the_whole_video(tmp_path: Path) -> None:
    model = StubChatModel("whole video result")
    segmenter = FakeSegmenter(tmp_path / "segments")
    segmenter.fail_split = True
    analyzer = InlineVideoAnalyzer(model, "prompt", VideoSettings(), segmenter)

    result = analyzer.analyze(video_in(tmp_path))

    assert result == "whole video result"
    assert model.call_count == 1
    assert not segmenter.cleaned


def test_inline_video_without_segments_analyses_the_file(tmp_path: Path) -> None:
    class NoSegments(FakeSegmenter):
        def split(self, video: Path, seconds: int) -> list[Path]:
            return []

    model = StubChatModel("result")
    analyzer = InlineVideoAnalyzer(model, "prompt", VideoSettings(), NoSegments(tmp_path / "s"))

    assert analyzer.analyze(video_in(tmp_path)) == "result"
    assert analyzer.describe() == "inline_video (segment 60s)"


def test_the_real_segmenter_only_splits_when_it_should(tmp_path: Path) -> None:
    segmenter = VideoSegmenter(tmp_path / "segments")
    video = video_in(tmp_path, "small.mp4")

    # A tiny file is left alone, and duration is never consulted.
    assert segmenter.should_split(video, VideoSettings(split_by_duration=False)) is False
    assert segmenter.should_split(video, VideoSettings(force_split=True)) is True
    assert segmenter.should_split(
        video, VideoSettings(split_min_mb=0.000001)
    ) is True


def install_fake_cv2(monkeypatch: pytest.MonkeyPatch, cv2_module: Any) -> None:
    """Make ``load_cv2`` find ``cv2_module`` without OpenCV being installed."""
    monkeypatch.setitem(sys.modules, "cv2", cv2_module)


class Unopenable(FakeCv2):
    """OpenCV that refuses to open anything: a corrupt or unsupported codec."""

    def VideoCapture(self, path: str) -> Any:  # noqa: N802 - mirrors OpenCV
        return types.SimpleNamespace(isOpened=lambda: False)


def test_duration_is_read_through_opencv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_cv2(monkeypatch, FakeCv2(frame_count=900, fps=30.0))

    duration = VideoSegmenter(tmp_path / "segments").duration_seconds(video_in(tmp_path))

    assert duration == 30  # 900 frames at 30 fps


def test_an_unreadable_video_has_no_duration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_cv2(monkeypatch, Unopenable())
    segmenter = VideoSegmenter(tmp_path / "segments")

    assert segmenter.duration_seconds(video_in(tmp_path)) == 0
    assert segmenter.should_split(video_in(tmp_path), VideoSettings()) is False


def test_a_long_video_is_split_by_duration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_cv2(monkeypatch, FakeCv2(frame_count=600, fps=1.0))
    segmenter = VideoSegmenter(tmp_path / "segments")

    assert segmenter.should_split(video_in(tmp_path), VideoSettings(segment_seconds=60)) is True


def test_splitting_without_ffmpeg_explains_the_audio_tradeoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import analysis.video.segmenter as module

    monkeypatch.setattr(module, "shutil", types.SimpleNamespace(which=lambda name: None))
    segmenter = VideoSegmenter(tmp_path / "segments")

    with pytest.raises(RuntimeError, match="requires ffmpeg"):
        segmenter.split(video_in(tmp_path), segment_seconds=10)


def test_frame_sampling_sends_images_for_provider_without_video(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import analysis.video.frame_sampling as module

    model = StubChatModel("a login form then a dashboard")
    monkeypatch.setattr(module, "extract_frames", lambda path, interval_seconds: ["frame-a", "frame-b"])
    analyzer = FrameSamplingAnalyzer(model, "prompt", VideoSettings())

    result = analyzer.analyze(video_in(tmp_path))

    assert result == "a login form then a dashboard"
    content = model.calls[0][0].content
    assert content[0] == {"type": "text", "text": "prompt"}
    assert content[1]["image_url"]["url"] == "data:image/jpeg;base64,frame-a"
    assert len(content) == 3


def test_frame_sampling_explains_a_video_without_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import analysis.video.frame_sampling as module

    monkeypatch.setattr(module, "extract_frames", lambda path, interval_seconds: [])
    analyzer = FrameSamplingAnalyzer(StubChatModel(), "prompt", VideoSettings())

    with pytest.raises(VideoAnalysisError, match="No frames could be extracted"):
        analyzer.analyze(video_in(tmp_path))


def test_frame_sampling_limits_the_number_of_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import analysis.video.frame_sampling as module

    model = StubChatModel("many frames")
    monkeypatch.setattr(
        module, "extract_frames", lambda path, interval_seconds: [f"f{index}" for index in range(50)]
    )
    analyzer = FrameSamplingAnalyzer(model, "prompt", VideoSettings(max_frames=5))

    analyzer.analyze(video_in(tmp_path))

    assert analyzer.describe() == "frame_sampling (every 2s, max 5)"
    assert len(model.calls[0][0].content) == 6  # prompt + 5 frames


class FakeRemoteFile:
    def __init__(self, name: str, state: str) -> None:
        self.name = name
        self.state = types.SimpleNamespace(name=state)


class FakeGenAI:
    """A tiny google.generativeai, so the upload/poll/delete dance is testable."""

    def __init__(self, states: list[str], answer: str = "uploaded video summary") -> None:
        self.states = states
        self.answer = answer
        self.uploads: list[str] = []
        self.polls = 0
        self.deleted: list[str] = []
        self.configured_with: list[str] = []
        self.models: list[str] = []

    def configure(self, api_key: str) -> None:
        self.configured_with.append(api_key)

    def upload_file(self, path: str) -> FakeRemoteFile:
        self.uploads.append(path)
        return FakeRemoteFile("files/abc", self.states[0])

    def get_file(self, name: str) -> FakeRemoteFile:
        self.polls += 1
        state = self.states[min(self.polls, len(self.states) - 1)]
        return FakeRemoteFile(name, state)

    def GenerativeModel(self, model: str):  # noqa: N802 - mirrors the SDK
        self.models.append(model)
        return self

    def generate_content(self, parts: list[Any]) -> Any:
        self.parts = parts
        return types.SimpleNamespace(text=self.answer)

    def delete_file(self, name: str) -> None:
        self.deleted.append(name)


def install_fake_genai(monkeypatch: pytest.MonkeyPatch, fake: FakeGenAI) -> None:
    module = types.ModuleType("google.generativeai")
    module.configure = fake.configure  # type: ignore[attr-defined]
    module.upload_file = fake.upload_file  # type: ignore[attr-defined]
    module.get_file = fake.get_file  # type: ignore[attr-defined]
    module.delete_file = fake.delete_file  # type: ignore[attr-defined]
    module.GenerativeModel = fake.GenerativeModel  # type: ignore[attr-defined]
    parent = types.ModuleType("google")
    parent.generativeai = module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", parent)
    monkeypatch.setitem(sys.modules, "google.generativeai", module)


def analyzer_for(model: str = "gemini-2.0-flash") -> GeminiFileApiAnalyzer:
    return GeminiFileApiAnalyzer(
        model=model, api_key="key", prompt="prompt", poll_interval=0
    )


def test_uploaded_video_is_polled_analysed_and_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGenAI(states=["PROCESSING", "ACTIVE"])
    install_fake_genai(monkeypatch, fake)

    result = analyzer_for().analyze(video_in(tmp_path))

    assert result == "uploaded video summary"
    assert fake.configured_with == ["key"]
    assert fake.models == ["gemini-2.0-flash"]
    assert fake.polls == 1  # one poll was enough
    assert fake.deleted == ["files/abc"]


def test_a_failed_server_side_conversion_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGenAI(states=["FAILED"])
    install_fake_genai(monkeypatch, fake)

    with pytest.raises(VideoAnalysisError, match="failed on Google's servers"):
        analyzer_for().analyze(video_in(tmp_path))

    assert fake.uploads
    assert fake.deleted == ["files/abc"]  # the rejected upload is still cleaned up
    assert fake.models == []  # and no model was ever called


def test_the_remote_file_is_deleted_even_when_analysis_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGenAI(states=["ACTIVE"])

    def explode(parts: list[Any]) -> Any:
        raise RuntimeError("quota exceeded")

    fake.generate_content = explode  # type: ignore[method-assign]
    install_fake_genai(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="quota exceeded"):
        analyzer_for().analyze(video_in(tmp_path))

    assert fake.deleted == ["files/abc"]


def test_a_cleanup_failure_does_not_mask_the_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGenAI(states=["ACTIVE"])

    def refuse(name: str) -> None:
        raise RuntimeError("delete is not allowed")

    fake.delete_file = refuse  # type: ignore[method-assign]
    install_fake_genai(monkeypatch, fake)

    assert analyzer_for().analyze(video_in(tmp_path)) == "uploaded video summary"
