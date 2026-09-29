"""Project lookup, re-read from disk on every request.

``projects.json`` is mounted read-only into the container, so reading it per
request means a edit plus ``sync_projects.py`` takes effect without rebuilding
the image.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping, Optional

from projects.model import Project, ProjectConfigError, llm_settings_from
from settings import LlmSettings

_log = logging.getLogger(__name__)


class ProjectNotFoundError(ProjectConfigError):
    """Raised when a request names a project that is not configured."""


class ProjectRegistry:
    """Loads and validates the configured projects."""

    def __init__(self, config_path: Path, projects_root: Path) -> None:
        self.config_path = Path(config_path)
        self.projects_root = Path(projects_root)

    def load(self) -> tuple[Project, ...]:
        """Read the configuration file and return every defined project."""
        raw = self._read_config()
        defaults_section = raw.get("defaults")
        if defaults_section is not None and not isinstance(defaults_section, Mapping):
            raise ProjectConfigError("'defaults' must be an object.")

        defaults_section = defaults_section or {}
        defaults = llm_settings_from(defaults_section.get("llm"))
        default_vision = llm_settings_from(defaults_section.get("vision"))

        entries = raw.get("projects")
        if not isinstance(entries, list) or not entries:
            raise ProjectConfigError(
                f"{self.config_path} must define a non-empty 'projects' list. "
                "See projects.example.json."
            )

        projects = tuple(
            _build(entry, self.projects_root, defaults, default_vision) for entry in entries
        )

        seen: set[str] = set()
        for project in projects:
            if project.name in seen:
                raise ProjectConfigError(f"Project '{project.name}' is defined twice.")
            seen.add(project.name)

        return projects

    def names(self) -> tuple[str, ...]:
        return tuple(project.name for project in self.load())

    def all(self) -> tuple[Project, ...]:
        return self.load()

    def get(self, name: str) -> Project:
        """Return one project by name, checking that its folder is mounted."""
        wanted = (name or "").strip()
        if not wanted:
            raise ProjectNotFoundError(self._missing_name_message())

        for project in self.load():
            if project.name == wanted:
                project.check_mount()
                return project

        raise ProjectNotFoundError(
            f"Unknown project '{wanted}'. Configured projects: "
            f"{', '.join(self.names())}."
        )

    def _read_config(self) -> Mapping[str, Any]:
        if not self.config_path.is_file():
            raise ProjectConfigError(
                f"Project configuration not found at {self.config_path}. "
                "Run 'python scripts/sync_projects.py' on the host and then "
                "'docker compose up -d'."
            )

        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProjectConfigError(
                f"{self.config_path} is not valid JSON: {exc}"
            ) from exc

        if not isinstance(raw, Mapping):
            raise ProjectConfigError(f"{self.config_path} must contain a JSON object.")
        return raw

    def _missing_name_message(self) -> str:
        try:
            configured = ", ".join(self.names())
        except ProjectConfigError as exc:
            return str(exc)
        return (
            "No project selected. Send the 'X-Spec2Test-Project' header with one of "
            f"the configured projects: {configured}."
        )


def _build(
    entry: Any,
    root: Path,
    defaults: Optional[LlmSettings],
    default_vision: Optional[LlmSettings],
) -> Project:
    if not isinstance(entry, Mapping):
        raise ProjectConfigError(f"Each project entry must be an object, got {type(entry).__name__}.")
    return Project.from_entry(entry, root, defaults, default_vision)


def find_configuration(root: Path) -> Optional[Path]:
    """Return the first ``projects.json`` found in the usual locations."""
    for candidate in (root / "projects.json", root / "config" / "projects.json"):
        if candidate.is_file():
            return candidate
    return None
