"""The project model: one input/output triple plus its LLM choices."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from settings import LlmSettings

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

INPUTS_DIRNAME = "inputs"
PREPROCESSED_DIRNAME = "preprocessed"
CACHE_DIRNAME = "cache"
SEGMENTS_DIRNAME = "_segments"

_HELP = (
    "Run 'python scripts/sync_projects.py' on the host and then "
    "'docker compose up -d' so the project folders are mounted."
)


class ProjectConfigError(ValueError):
    """Raised when projects.json is missing, malformed or inconsistent."""


@dataclass(frozen=True)
class Project:
    """One project: where its files live and which models to use."""

    name: str
    inputs: Path
    preprocessed: Path
    cache: Path
    llm: LlmSettings
    vision: Optional[LlmSettings] = None

    @classmethod
    def from_entry(
        cls,
        raw: Mapping[str, Any],
        root: Path,
        defaults: Optional[LlmSettings] = None,
        default_vision: Optional[LlmSettings] = None,
    ) -> "Project":
        """Build a project from one ``projects.json`` entry."""
        name = str(raw.get("name", "")).strip()
        if not SLUG_RE.match(name):
            raise ProjectConfigError(
                f"Invalid project name {name!r}. Use lowercase letters, digits, "
                "dots, dashes or underscores, starting with a letter or digit."
            )

        base = Path(root) / name
        return cls(
            name=name,
            inputs=base / INPUTS_DIRNAME,
            preprocessed=base / PREPROCESSED_DIRNAME,
            cache=base / CACHE_DIRNAME,
            llm=(defaults or LlmSettings()).merged_with(llm_settings_from(raw.get("llm"))),
            vision=_merge_optional(default_vision, llm_settings_from(raw.get("vision"))),
        )

    @property
    def segments_dir(self) -> Path:
        """Scratch space for video segments (never read by the agent)."""
        return self.cache / SEGMENTS_DIRNAME

    def check_mount(self) -> None:
        """Fail early and helpfully when the project folder is not mounted."""
        if not self.inputs.is_dir():
            raise ProjectConfigError(
                f"Project '{self.name}' expects inputs at {self.inputs}, but that "
                f"directory does not exist. {_HELP}"
            )

    def describe(self) -> dict[str, str]:
        """Paths and models, for the ``current_project`` tool."""
        return {
            "name": self.name,
            "inputs": str(self.inputs),
            "preprocessed": str(self.preprocessed),
            "cache": str(self.cache),
            "provider": self.llm.provider,
            "model": self.llm.model or "",
            "vision_provider": self.vision.provider if self.vision else "",
            "vision_model": (self.vision.model or "") if self.vision else "",
        }


def _merge_optional(
    default: Optional[LlmSettings], override: Optional[LlmSettings]
) -> Optional[LlmSettings]:
    """Merge an optional override onto an optional default, staying ``None``."""
    if override is None:
        return default
    if default is None:
        return override
    return default.merged_with(override)


def llm_settings_from(raw: Any) -> Optional[LlmSettings]:
    """Parse an optional ``{"provider": ..., "model": ...}`` block."""
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ProjectConfigError(f"'llm'/'vision' must be an object, got {type(raw).__name__}.")

    provider = str(raw.get("provider", "")).strip()
    model = str(raw.get("model", "")).strip()
    if not provider and not model:
        return None
    return LlmSettings(provider=provider, model=model or None)
