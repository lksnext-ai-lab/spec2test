"""Settings are parsed once, typed, and tolerate bad values."""

from __future__ import annotations

from pathlib import Path

from settings import LlmSettings, Settings, VideoSettings


def test_defaults_without_environment() -> None:
    settings = Settings.from_env({})

    assert settings.video.segment_seconds == 60
    assert settings.video.max_frames == 20
    assert settings.projects_config == Path("/config/projects.json")
    assert settings.projects_root == Path("/projects")


def test_environment_overrides_every_knob() -> None:
    settings = Settings.from_env(
        {
            "INPUT_PROCESSOR_VIDEO_SEGMENT_SECONDS": "30",
            "INPUT_PROCESSOR_VIDEO_SPLIT_MIN_MB": "8.5",
            "INPUT_PROCESSOR_VIDEO_FORCE_SPLIT": "true",
            "INPUT_PROCESSOR_VIDEO_SPLIT_BY_DURATION": "0",
            "INPUT_PROCESSOR_VIDEO_REQUIRE_AUDIO": "no",
            "INPUT_PROCESSOR_VIDEO_CONSOLIDATE": "false",
            "INPUT_PROCESSOR_VIDEO_FRAME_SECONDS": "5",
            "INPUT_PROCESSOR_VIDEO_MAX_FRAMES": "12",
            "INPUT_PROCESSOR_PROJECTS_CONFIG": "/config/other.json",
            "INPUT_PROCESSOR_PROJECTS_ROOT": "/srv/projects",
            "INPUT_PROCESSOR_LOG_LEVEL": "debug",
        }
    )

    assert settings.video == VideoSettings(
        segment_seconds=30,
        split_min_mb=8.5,
        force_split=True,
        split_by_duration=False,
        require_audio=False,
        consolidate=False,
        frame_interval_seconds=5,
        max_frames=12,
    )
    assert settings.projects_config == Path("/config/other.json")
    assert settings.projects_root == Path("/srv/projects")
    assert settings.log_level == "DEBUG"


def test_invalid_values_fall_back_to_defaults() -> None:
    settings = Settings.from_env(
        {
            "INPUT_PROCESSOR_VIDEO_SEGMENT_SECONDS": "not-a-number",
            "INPUT_PROCESSOR_VIDEO_SPLIT_MIN_MB": "",
            "INPUT_PROCESSOR_VIDEO_CONSOLIDATE": "maybe",
        }
    )

    assert settings.video.segment_seconds == 60
    assert settings.video.split_min_mb == 12.0
    assert settings.video.consolidate is True


def test_llm_choices_are_not_read_from_the_environment() -> None:
    """Provider and model come from projects.json, not from .env."""
    settings = Settings.from_env(
        {"INPUT_PROCESSOR_PROVIDER": "qwen", "INPUT_PROCESSOR_MODEL": "qwen-vl-max"}
    )

    assert not hasattr(settings, "llm")


def test_llm_settings_merge_prefers_overrides() -> None:
    base = LlmSettings(provider="google_genai", model="gemini-2.0-flash")

    assert base.merged_with(None) == base
    assert base.merged_with(LlmSettings(provider="qwen", model=None)) == LlmSettings(
        provider="qwen", model="gemini-2.0-flash"
    )
    assert base.merged_with(LlmSettings(provider="", model="qwen-vl-max")) == LlmSettings(
        provider="google_genai", model="qwen-vl-max"
    )
