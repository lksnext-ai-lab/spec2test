"""Typed application settings parsed once from the environment.

Only secrets and tuning knobs live here. Per-project choices (input,
preprocessed and cache paths, provider and model) come from ``projects.json``
through :mod:`projects.registry`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

_log = logging.getLogger(__name__)

DEFAULT_LLM_PROVIDER = "google_genai"
DEFAULT_PROJECTS_CONFIG = Path("/config/projects.json")
DEFAULT_PROJECTS_ROOT = Path("/projects")

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off", ""}


@dataclass(frozen=True)
class LlmSettings:
    """Which provider and model to use."""

    provider: str = DEFAULT_LLM_PROVIDER
    model: Optional[str] = None

    def merged_with(self, override: "Optional[LlmSettings]") -> "LlmSettings":
        """Return these settings with non-empty values of ``override`` applied."""
        if override is None:
            return self
        return LlmSettings(
            provider=override.provider or self.provider,
            model=override.model or self.model,
        )


@dataclass(frozen=True)
class VideoSettings:
    """Video analysis tuning knobs (provider independent)."""

    segment_seconds: int = 60
    split_min_mb: float = 12.0
    force_split: bool = False
    split_by_duration: bool = True
    require_audio: bool = True
    consolidate: bool = True
    frame_interval_seconds: int = 2
    max_frames: int = 20


@dataclass(frozen=True)
class Settings:
    """Everything the input processor reads from the environment."""

    video: VideoSettings = field(default_factory=VideoSettings)
    projects_config: Path = DEFAULT_PROJECTS_CONFIG
    projects_root: Path = DEFAULT_PROJECTS_ROOT
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            video=VideoSettings(
                segment_seconds=_get_int(env, "INPUT_PROCESSOR_VIDEO_SEGMENT_SECONDS", 60),
                split_min_mb=_get_float(env, "INPUT_PROCESSOR_VIDEO_SPLIT_MIN_MB", 12.0),
                force_split=_get_bool(env, "INPUT_PROCESSOR_VIDEO_FORCE_SPLIT", False),
                split_by_duration=_get_bool(env, "INPUT_PROCESSOR_VIDEO_SPLIT_BY_DURATION", True),
                require_audio=_get_bool(env, "INPUT_PROCESSOR_VIDEO_REQUIRE_AUDIO", True),
                consolidate=_get_bool(env, "INPUT_PROCESSOR_VIDEO_CONSOLIDATE", True),
                frame_interval_seconds=_get_int(env, "INPUT_PROCESSOR_VIDEO_FRAME_SECONDS", 2),
                max_frames=_get_int(env, "INPUT_PROCESSOR_VIDEO_MAX_FRAMES", 20),
            ),
            projects_config=Path(
                _get_str(env, "INPUT_PROCESSOR_PROJECTS_CONFIG", str(DEFAULT_PROJECTS_CONFIG))
            ),
            projects_root=Path(
                _get_str(env, "INPUT_PROCESSOR_PROJECTS_ROOT", str(DEFAULT_PROJECTS_ROOT))
            ),
            log_level=_get_str(env, "INPUT_PROCESSOR_LOG_LEVEL", "INFO").upper(),
            host=_get_str(env, "INPUT_PROCESSOR_HOST", "127.0.0.1"),
            port=_get_int(env, "INPUT_PROCESSOR_PORT", 8000),
        )


def _get_str(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key)
    return default if value is None or not value.strip() else value.strip()


def _get_bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    value = env.get(key)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in _TRUTHY:
        return True
    if normalized in _FALSY:
        return False
    _log.warning("Invalid boolean for %s: %r. Using %s.", key, value, default)
    return default


def _get_int(env: Mapping[str, str], key: str, default: int) -> int:
    value = env.get(key)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        _log.warning("Invalid integer for %s: %r. Using %s.", key, value, default)
        return default


def _get_float(env: Mapping[str, str], key: str, default: float) -> float:
    value = env.get(key)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        _log.warning("Invalid number for %s: %r. Using %s.", key, value, default)
        return default
