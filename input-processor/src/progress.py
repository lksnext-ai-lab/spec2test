"""Progress reporting and cancellation for long-running processing.

Processing code runs in a worker thread and knows nothing about MCP. It talks to
whatever :class:`ProgressReporter` is active in the current context; the MCP
layer installs one that forwards to the client, and everywhere else the default
reporter does nothing, so instrumented code needs no ``if reporter`` checks.
"""

from __future__ import annotations

import contextvars
import logging
import threading
from contextlib import contextmanager
from typing import Callable, Iterator, Optional

_log = logging.getLogger(__name__)

Sink = Callable[[str, Optional[float], Optional[float]], None]
"""``sink(message, progress, total)``: called for every stage/step update."""


class ProcessingCancelled(Exception):
    """Raised at a checkpoint when the client cancelled the request."""


class ProgressReporter:
    """Receives stage updates from processing code. The base class ignores them."""

    def stage(self, message: str) -> None:
        """A named stage without a known length, e.g. ``consolidating``."""

    def step(self, index: int, total: int, message: str) -> None:
        """Step ``index`` of ``total`` (1-based), e.g. ``segment 3/8``."""

    def check_cancelled(self) -> None:
        """Raise :class:`ProcessingCancelled` when the request was cancelled."""


class CallbackReporter(ProgressReporter):
    """Forwards updates to a sink and honours a cancellation event."""

    def __init__(self, sink: Sink, cancelled: Optional[threading.Event] = None) -> None:
        self._sink = sink
        self._cancelled = cancelled or threading.Event()

    def stage(self, message: str) -> None:
        self.check_cancelled()
        self._emit(message, None, None)

    def step(self, index: int, total: int, message: str) -> None:
        self.check_cancelled()
        self._emit(message, float(index), float(total))

    def check_cancelled(self) -> None:
        if self._cancelled.is_set():
            raise ProcessingCancelled("Processing was cancelled.")

    def _emit(self, message: str, progress: Optional[float], total: Optional[float]) -> None:
        try:
            self._sink(message, progress, total)
        except Exception:  # noqa: BLE001 - a broken client must not fail processing
            _log.debug("Progress sink failed", exc_info=True)


_NOOP = ProgressReporter()
_current: contextvars.ContextVar[ProgressReporter] = contextvars.ContextVar(
    "progress_reporter", default=_NOOP
)


def reporter() -> ProgressReporter:
    """The reporter active for the current request (a no-op outside one)."""
    return _current.get()


@contextmanager
def use_reporter(active: ProgressReporter) -> Iterator[ProgressReporter]:
    """Install ``active`` for the duration of the block."""
    token = _current.set(active)
    try:
        yield active
    finally:
        _current.reset(token)
