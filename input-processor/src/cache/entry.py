"""Cache entries and their YAML front-matter.

Every cached artefact is a Markdown file that starts with a small front-matter
block recording which source file produced it:

    ---
    source: "login-demo.mp4"
    format: ".mp4"
    size: 1234567
    sha256: "9f2c..."
    processed_at: "2026-09-29T10:00:00Z"
    provider: "google_genai"
    model: "gemini-2.5-flash"
    ---
    <processed content>

The source name makes the cache readable; the digest makes it verifiable. The
digest lives *inside* the file, so renaming a cache file by hand never breaks
change detection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

DELIMITER = "---"
SUFFIX = ".md"

_SOURCE_KEYS = ("source", "format", "size", "sha256", "processed_at", "provider", "model")


class FrontMatterError(ValueError):
    """Raised when a cache file's front-matter cannot be parsed."""


@dataclass(frozen=True)
class CacheEntry:
    """Metadata of one cached artefact."""

    source: str
    format: str
    size: int
    sha256: str
    processed_at: str
    provider: str
    model: str
    path: Path

    @property
    def name(self) -> str:
        """The source file name this entry belongs to."""
        return self.source

    @property
    def short_hash(self) -> str:
        return self.sha256[:8]

    def with_source(self, source: str, format: str, size: int, path: Path) -> "CacheEntry":
        return replace(self, source=source, format=format, size=size, path=path)

    def to_front_matter(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "format": self.format,
            "size": self.size,
            "sha256": self.sha256,
            "processed_at": self.processed_at,
            "provider": self.provider,
            "model": self.model,
        }


def utc_now() -> str:
    """Current UTC time as ``YYYY-MM-DDTHH:MM:SSZ``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_for_filename(moment: Optional[str] = None) -> str:
    """Filesystem-safe UTC timestamp (``20260929T100000Z``)."""
    value = moment or utc_now()
    return value.replace("-", "").replace(":", "")


def utc_from_timestamp(epoch_seconds: float) -> str:
    """Format a POSIX timestamp the same way as :func:`utc_now`."""
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render(mapping: Mapping[str, Any]) -> str:
    """Render a flat mapping as a front-matter block."""
    lines = [DELIMITER]
    lines.extend(f"{key}: {_encode(value)}" for key, value in mapping.items())
    lines.append(DELIMITER)
    return "\n".join(lines) + "\n"


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Split ``text`` into its front-matter mapping and its body."""
    if not text.startswith(f"{DELIMITER}\n"):
        return {}, text

    lines = text.split("\n")
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == DELIMITER:
            fields = _parse_fields(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return fields, body.lstrip("\n")

    raise FrontMatterError("Front-matter block is not terminated.")


def _parse_fields(lines: list[str]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for line in lines:
        if not line.strip():
            continue
        key, separator, raw_value = line.partition(":")
        if not separator:
            raise FrontMatterError(f"Invalid front-matter line: {line!r}")
        fields[key.strip()] = _decode(raw_value.strip())
    return fields


def entry_from_text(text: str, path: Path) -> CacheEntry:
    """Build a :class:`CacheEntry` from the contents of a cache file."""
    fields, _ = parse(text)
    missing = [key for key in _SOURCE_KEYS if str(fields.get(key, "")).strip() == ""]
    if missing:
        raise FrontMatterError(
            f"{path.name} is missing front-matter keys: {', '.join(missing)}"
        )

    try:
        size = int(str(fields["size"]).strip())
    except ValueError as exc:
        raise FrontMatterError(f"{path.name} has a non-numeric size: {fields['size']!r}") from exc

    return CacheEntry(
        source=str(fields["source"]),
        format=str(fields["format"]),
        size=size,
        sha256=str(fields["sha256"]),
        processed_at=str(fields["processed_at"]),
        provider=str(fields["provider"]),
        model=str(fields["model"]),
        path=path,
    )


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value))


def _decode(raw: str) -> Any:
    if raw.startswith('"'):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FrontMatterError(f"Invalid quoted front-matter value: {raw!r}") from exc
    if raw.isdigit():
        return int(raw)
    return raw
