"""Video analysis through Google's File API (native video upload)."""

from __future__ import annotations

import logging
import time
from typing import Any

from analysis.video.base import VideoAnalysisError, VideoAnalyzer
from progress import reporter

_log = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 5
_ACTIVE_STATE = "ACTIVE"
_FAILED_STATES = {"FAILED"}
_TERMINAL_STATES = _FAILED_STATES | {_ACTIVE_STATE}


def _load_genai() -> Any:
    try:
        import google.generativeai as genai
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise VideoAnalysisError(
            "Native video upload requires the 'google-generativeai' package. "
            "Install the input-processor requirements."
        ) from exc
    return genai


class GeminiFileApiAnalyzer(VideoAnalyzer):
    """Upload the recording to Google, wait for processing, then analyse it.

    Large videos cannot travel inline: base64 encoding blows past the request
    size limit and the upload takes long enough to hit HTTP timeouts.
    """

    name = "gemini_file_api"

    def __init__(self, model: str, api_key: str, prompt: str, poll_interval: float = _POLL_INTERVAL_SECONDS) -> None:
        if not api_key:
            raise VideoAnalysisError(
                "Native video upload requires an API key for provider 'google_genai'."
            )
        self._model = model
        self._api_key = api_key
        self._prompt = prompt
        self._poll_interval = poll_interval

    def analyze(self, video_path) -> str:
        genai = _load_genai()
        genai.configure(api_key=self._api_key)

        reporter().stage("Uploading video to Gemini")
        _log.info("Uploading %s via the Gemini File API...", video_path.name)
        remote_file = genai.upload_file(path=str(video_path))

        try:
            ready = self._wait_until_ready(genai, remote_file)
            reporter().stage("Analysing video with Gemini")
            response = genai.GenerativeModel(self._model).generate_content(
                [ready, self._prompt]
            )
            return response.text
        finally:
            # Also runs when the conversion fails server-side: the upload
            # already exists and would otherwise linger until it expires.
            self._delete(genai, remote_file)

    def _wait_until_ready(self, genai: Any, remote_file: Any) -> Any:
        """Poll until Google finishes processing the upload."""
        while self._state_of(remote_file) not in _TERMINAL_STATES:
            reporter().stage("Waiting for Google to process the upload")
            time.sleep(self._poll_interval)
            remote_file = genai.get_file(remote_file.name)

        if self._state_of(remote_file) in _FAILED_STATES:
            raise VideoAnalysisError("Video processing failed on Google's servers.")

        return remote_file

    @staticmethod
    def _state_of(remote_file: Any) -> str:
        return getattr(getattr(remote_file, "state", None), "name", "")

    @staticmethod
    def _delete(genai: Any, remote_file: Any) -> None:
        try:
            genai.delete_file(remote_file.name)
        except Exception as exc:  # noqa: BLE001 - cleanup must never mask the result
            _log.warning("Failed to clean up remote video file: %s", exc)
