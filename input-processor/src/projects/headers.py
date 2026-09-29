"""Project selection through a per-workspace HTTP header.

Each editor workspace points at one project by sending
``X-Spec2Test-Project: <name>``, so the same container can serve several
projects at once without any shared state.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

PROJECT_HEADER = "X-Spec2Test-Project"


def project_name_from_headers(headers: Optional[Mapping[str, Any]]) -> Optional[str]:
    """Return the project named by the header, if present."""
    if not headers:
        return None

    lookups = (headers.get(PROJECT_HEADER), _case_insensitive_get(headers))
    for candidate in lookups:
        if candidate:
            return str(candidate).strip() or None
    return None


def project_name_from_request(request: Any) -> Optional[str]:
    """Return the project named by an HTTP request's headers."""
    if request is None:
        return None
    return project_name_from_headers(getattr(request, "headers", None))


def project_name_from_context(context: Any) -> Optional[str]:
    """Return the project named by an MCP tool context."""
    request_context = getattr(context, "request_context", None)
    return project_name_from_request(getattr(request_context, "request", None))


def _case_insensitive_get(headers: Mapping[str, Any]) -> Optional[str]:
    """Header maps are case-insensitive in practice, but fakes in tests are not."""
    try:
        items = headers.items()
    except AttributeError:  # pragma: no cover - defensive
        return None

    wanted = PROJECT_HEADER.lower()
    for key, value in items:
        if str(key).lower() == wanted:
            return value
    return None
