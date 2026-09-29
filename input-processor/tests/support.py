"""Test doubles shared by several test modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import AIMessage, BaseMessage

from cache.source import SourceFile
from handlers.base import FileHandler, HandlerContext


class StubChatModel:
    """Stand-in for a LangChain chat model that records what it was asked.

    Only ``invoke`` is exercised by the code under test, so a small proxy is
    enough — and it keeps the suite independent of any provider package.
    """

    def __init__(self, response: str = "stub response", fail_with: Optional[Exception] = None) -> None:
        self.response = response
        self.fail_with = fail_with
        self.calls: list[list[BaseMessage]] = []

    def invoke(self, messages: Any, **kwargs: Any) -> AIMessage:
        self.calls.append(list(messages) if isinstance(messages, (list, tuple)) else [messages])
        if self.fail_with is not None:
            raise self.fail_with
        return AIMessage(content=self.response)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def prompt_text(self, index: int = -1) -> str:
        """Flatten the messages of one call into text."""
        messages = self.calls[index]
        parts = []
        for message in messages:
            content = message.content
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                parts.extend(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
        return "\n".join(parts)


class RecordingHandler(FileHandler):
    """Handler that returns whatever its chat model produced."""

    name = "recording"
    extensions = (".txt", ".md", ".pdf")

    def __init__(self, chat_model: StubChatModel, output: Optional[str] = None) -> None:
        self.chat_model = chat_model
        self.output = output

    def handle(self, source: SourceFile, context: HandlerContext) -> str:
        if self.output is not None:
            return self.output
        return self.chat_model.invoke(str(source.name)).content


class FailingHandler(FileHandler):
    """Handler that always raises, to exercise error reporting."""

    name = "failing"
    extensions = (".bin",)

    def handle(self, source: SourceFile, context: HandlerContext) -> str:
        raise RuntimeError("cannot process this file")


def source_for(path: Path) -> SourceFile:
    return SourceFile.from_path(path)


class FakeFrame:
    """Just enough of an OpenCV frame for shape inspection and encoding."""

    def __init__(self, width: int, height: int) -> None:
        self.shape = (height, width, 3)


class FakeVideoCapture:
    """A video whose frames can change resolution midway, like a page change."""

    def __init__(self, cv2: "FakeCv2") -> None:
        self._cv2 = cv2
        self._index = 0

    def isOpened(self) -> bool:
        return True

    def get(self, prop: int) -> float:
        return {
            self._cv2.CAP_PROP_FPS: self._cv2.fps,
            self._cv2.CAP_PROP_FRAME_COUNT: len(self._cv2.resolutions),
            self._cv2.CAP_PROP_FRAME_WIDTH: self._cv2.resolutions[0][0],
            self._cv2.CAP_PROP_FRAME_HEIGHT: self._cv2.resolutions[0][1],
        }.get(prop, 0)

    def read(self) -> tuple[bool, Optional[FakeFrame]]:
        if self._index >= len(self._cv2.resolutions):
            return False, None

        width, height = self._cv2.resolutions[self._index]
        self._index += 1
        return True, FakeFrame(width, height)

    def release(self) -> None:  # pragma: no cover - nothing to release
        return None


class FakeCv2:
    """Minimal stand-in for OpenCV, so video logic is testable without it."""

    CAP_PROP_FPS = 5
    CAP_PROP_FRAME_COUNT = 7
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    IMWRITE_JPEG_QUALITY = 1

    def __init__(
        self,
        frame_count: int = 20,
        fps: float = 10.0,
        resolutions: Optional[list[tuple[int, int]]] = None,
    ) -> None:
        self.fps = fps
        self.resolutions = resolutions or [(640, 480)] * frame_count

    def VideoCapture(self, path: str) -> FakeVideoCapture:  # noqa: N802 - mirrors OpenCV
        return FakeVideoCapture(self)

    def imencode(self, extension: str, frame: FakeFrame, params: Any = None):
        return True, b"jpeg"

    def resize(self, frame: FakeFrame, size: tuple[int, int]) -> FakeFrame:
        return FakeFrame(size[0], size[1])
