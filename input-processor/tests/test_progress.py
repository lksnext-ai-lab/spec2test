"""Progress reporting: a silent default, forwarding, and cancellation."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

import progress
from analysis.video.factory import choose_video_analyzer
from progress import CallbackReporter, ProcessingCancelled, use_reporter
from providers.base import Capabilities, LLMHandle
from settings import VideoSettings
from support import StubChatModel


def test_the_default_reporter_ignores_everything() -> None:
    reporter = progress.reporter()

    reporter.stage("anything")
    reporter.step(1, 2, "anything")
    reporter.check_cancelled()


def test_use_reporter_installs_and_restores_the_reporter() -> None:
    events: list[tuple] = []
    default = progress.reporter()

    with use_reporter(CallbackReporter(lambda *event: events.append(event))):
        progress.reporter().stage("converting")
        progress.reporter().step(3, 8, "segment 3/8")

    assert events == [("converting", None, None), ("segment 3/8", 3.0, 8.0)]
    assert progress.reporter() is default


def test_a_cancelled_reporter_raises_at_the_next_checkpoint() -> None:
    cancelled = threading.Event()
    reporter = CallbackReporter(lambda *event: None, cancelled)
    reporter.stage("still running")

    cancelled.set()

    with pytest.raises(ProcessingCancelled):
        reporter.stage("next stage")
    with pytest.raises(ProcessingCancelled):
        reporter.check_cancelled()


def test_a_failing_sink_never_breaks_processing() -> None:
    def broken(*_event) -> None:
        raise RuntimeError("client went away")

    CallbackReporter(broken).stage("still fine")


def test_video_segments_are_written_directly_under_the_given_work_dir(tmp_path: Path) -> None:
    """The project already passes ``.../cache/_segments``; it must not nest."""
    handle = LLMHandle(
        provider_name="stub",
        model="stub",
        capabilities=Capabilities(text=True, images=True, video_inline=True),
        chat_model=StubChatModel("ok"),
    )

    analyzer = choose_video_analyzer(handle, VideoSettings(), tmp_path / "_segments", "prompt")

    assert analyzer._segmenter.work_dir == tmp_path / "_segments"
