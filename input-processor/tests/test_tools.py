"""The MCP tools: header -> project -> JSON payload.

``mcp`` is not a test dependency, so ``main`` is imported against a minimal
stand-in whose ``tool()`` decorator returns the function unchanged. That is
enough to exercise everything the tools actually do: resolve the project from
the request headers, call the service in a worker thread, and shape the answer.
"""

from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from projects.registry import ProjectRegistry
from projects.runtime import RuntimePool
from providers.native import AnthropicProvider, GoogleGenAIProvider, OpenAIProvider
from providers.openai_compatible import OpenAICompatibleProvider
from providers.registry import build_default_registry
from settings import Settings

ENV = {
    "GOOGLE_API_KEY": "google-key",
    "OPENAI_API_KEY": "openai-key",
    "ANTHROPIC_API_KEY": "anthropic-key",
    "DEEPSEEK_API_KEY": "deepseek-key",
    "OPENROUTER_API_KEY": "openrouter-key",
    "DASHSCOPE_API_KEY": "dashscope-key",
}


class FakeFastMCP:
    """Just enough of FastMCP: register the tool and keep the function."""

    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.tools: dict[str, Any] = {}

    def tool(self):
        def decorator(function):
            self.tools[function.__name__] = function
            return function

        return decorator


@pytest.fixture(autouse=True)
def _no_real_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never build a real LangChain client, and never touch the real mcp."""
    from support import StubChatModel

    for provider_class in (
        GoogleGenAIProvider,
        OpenAIProvider,
        AnthropicProvider,
        OpenAICompatibleProvider,
    ):
        monkeypatch.setattr(
            provider_class,
            "create_chat_model",
            lambda self, model, api_key=None: StubChatModel(f"{self.name} response"),
        )

    module = types.ModuleType("mcp.server.fastmcp")
    module.Context = object  # type: ignore[attr-defined]
    module.FastMCP = FakeFastMCP  # type: ignore[attr-defined]
    parent = types.ModuleType("mcp.server")
    parent.fastmcp = module  # type: ignore[attr-defined]
    top = types.ModuleType("mcp")
    top.server = parent  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mcp", top)
    monkeypatch.setitem(sys.modules, "mcp.server", parent)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", module)


def write_projects(root: Path, names: tuple[str, ...]) -> Path:
    """Create the config and the inputs folder of every named project."""
    projects = []
    for name in names:
        (root / "projects" / name / "inputs").mkdir(parents=True, exist_ok=True)
        projects.append({"name": name})
    config = root / "projects.json"
    config.write_text(json.dumps({"projects": projects}), encoding="utf-8")
    return config


def pool_for(root: Path, names: tuple[str, ...] = ("alpha", "beta")) -> RuntimePool:
    return RuntimePool(
        ProjectRegistry(write_projects(root, names), root / "projects"),
        build_default_registry(),
        ENV,
        Settings(),
    )


@pytest.fixture
def tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Import ``main`` with two mounted projects and return its tool functions."""
    import main

    monkeypatch.setattr(main, "settings", Settings())
    monkeypatch.setattr(main, "pool", pool_for(tmp_path))
    return main


def inputs_of(root: Path, project: str) -> Path:
    return root / "projects" / project / "inputs"


def context_for(project: str = "alpha") -> Any:
    """A stand-in for the MCP Context of a request with the project header."""
    headers = {} if project is None else {"X-Spec2Test-Project": project}
    request = types.SimpleNamespace(headers=headers)
    return types.SimpleNamespace(request_context=types.SimpleNamespace(request=request))


def call(tool, *args, **kwargs) -> str:
    return asyncio.run(tool(*args, **kwargs))


def write_input(root: Path, project: str, name: str, content: str = "hello") -> Path:
    path = inputs_of(root, project) / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def populated(tools, tmp_path: Path):
    """The imported main, with one processed file in the alpha project."""
    write_input(tmp_path, "alpha", "notes.txt", "alpha requirements")
    call(tools.process_files, context_for("alpha"))
    return tools


# --- current_project ---------------------------------------------------------


def test_current_project_reports_the_active_project(tools, tmp_path: Path) -> None:
    payload = json.loads(call(tools.current_project, context_for("alpha")))

    assert payload["name"] == "alpha"
    assert Path(payload["inputs"]) == inputs_of(tmp_path, "alpha")
    assert Path(payload["cache"]).name == "cache"
    assert payload["provider"] == "google_genai"


def test_a_missing_header_is_explained(tools) -> None:
    payload = json.loads(call(tools.current_project, context_for(None)))

    assert "X-Spec2Test-Project" in payload["error"]
    assert "alpha, beta" in payload["error"]


def test_an_unknown_project_is_explained(tools) -> None:
    payload = json.loads(call(tools.current_project, context_for("gamma")))

    assert "Unknown project 'gamma'" in payload["error"]


# --- process_files -----------------------------------------------------------


def test_process_files_reports_the_documented_fields(tools, tmp_path: Path) -> None:
    write_input(tmp_path, "alpha", "notes.txt", "alpha requirements")

    payload = json.loads(call(tools.process_files, context_for("alpha")))

    assert len(payload) == 1
    entry = payload[0]
    assert set(entry) == {"name", "format", "size", "sha256", "status", "processed_at"}
    assert entry["name"] == "notes.txt"
    assert entry["format"] == ".txt"
    assert entry["status"] == "new"


def test_process_files_skips_unchanged_files(populated) -> None:
    payload = json.loads(call(populated.process_files, context_for("alpha")))

    assert [item["status"] for item in payload] == ["cached"]


def test_process_files_reports_orphans(populated, tmp_path: Path) -> None:
    (tmp_path / "projects" / "alpha" / "inputs" / "notes.txt").unlink()

    payload = json.loads(call(populated.process_files, context_for("alpha")))

    assert [item["status"] for item in payload] == ["orphaned"]
    assert payload[0]["name"] == "notes.txt"


def test_process_files_returns_an_error_when_the_project_is_unmounted(
    tools, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project whose inputs folder was never mounted fails with the fix."""
    config = tmp_path / "projects.json"
    config.write_text(json.dumps({"projects": [{"name": "gamma"}]}), encoding="utf-8")
    monkeypatch.setattr(
        tools,
        "pool",
        RuntimePool(
            ProjectRegistry(config, tmp_path / "projects"),
            build_default_registry(),
            ENV,
            Settings(),
        ),
    )

    payload = json.loads(call(tools.process_files, context_for("gamma")))

    assert "sync_projects.py" in payload["error"]


# --- list / get --------------------------------------------------------------


def test_list_processed_files_lists_names_and_digests(populated, tmp_path: Path) -> None:
    payload = json.loads(call(populated.list_processed_files, context_for("alpha")))

    assert len(payload) == 1
    assert set(payload[0]) == {"name", "sha256", "processed_at"}
    assert payload[0]["name"] == "notes.txt"
    assert payload[0]["processed_at"].endswith("Z")


def test_get_processed_content_by_name(populated) -> None:
    content = call(
        populated.get_processed_content, context_for("alpha"), file_name="notes.txt"
    )

    assert content.strip() == "google_genai response"


def test_get_processed_content_by_hash_still_works(populated) -> None:
    listed = json.loads(call(populated.list_processed_files, context_for("alpha")))

    content = call(
        populated.get_processed_content, context_for("alpha"), file_hash=listed[0]["sha256"]
    )

    assert content.strip() == "google_genai response"


def test_get_processed_content_requires_a_key(populated) -> None:
    answer = call(populated.get_processed_content, context_for("alpha"))

    assert "a file name is required" in answer


def test_get_processed_content_explains_an_unknown_name(populated) -> None:
    answer = call(populated.get_processed_content, context_for("alpha"), file_name="ghost.txt")

    assert "No cached content for 'ghost.txt'" in answer


def test_get_all_processed_content_returns_every_file(populated) -> None:
    payload = json.loads(call(populated.get_all_processed_content, context_for("alpha")))

    assert [item["name"] for item in payload] == ["notes.txt"]
    assert payload[0]["content"].strip() == "google_genai response"
    assert payload[0]["sha256"]


def test_projects_do_not_see_each_others_files(tools, tmp_path: Path) -> None:
    """One container, two workspaces: the header decides which files are in play."""
    write_input(tmp_path, "alpha", "alpha.txt", "a")
    write_input(tmp_path, "beta", "beta.txt", "b")

    call(tools.process_files, context_for("alpha"))
    call(tools.process_files, context_for("beta"))

    alpha = json.loads(call(tools.list_processed_files, context_for("alpha")))
    beta = json.loads(call(tools.list_processed_files, context_for("beta")))

    assert [item["name"] for item in alpha] == ["alpha.txt"]
    assert [item["name"] for item in beta] == ["beta.txt"]
    cached = [path.name for path in (tmp_path / "projects" / "alpha" / "cache").glob("*.md")]
    assert cached == ["alpha.txt.md"]


# --- progress, process_file, list_input_files, list_providers ------------------


def recording_context(project: str = "alpha") -> Any:
    """A context that records the progress notifications and log lines."""
    context = context_for(project)
    context.progress = []
    context.logs = []

    async def report_progress(progress, total=None, message=None):
        context.progress.append((progress, message))

    async def info(message):
        context.logs.append(message)

    context.report_progress = report_progress
    context.info = info
    return context


def test_process_files_streams_progress_to_the_client(tools, tmp_path: Path) -> None:
    write_input(tmp_path, "alpha", "a.txt", "one")
    write_input(tmp_path, "alpha", "b.txt", "two")
    context = recording_context()

    call(tools.process_files, context)

    assert context.logs == ["File 1/2: a.txt", "File 2/2: b.txt"]
    assert [value for value, _ in context.progress] == [1, 2]


def test_list_input_files_reports_cache_state_without_processing(populated, tmp_path: Path) -> None:
    write_input(tmp_path, "alpha", "fresh.txt", "new file")
    write_input(tmp_path, "alpha", "notes.txt", "alpha requirements, edited")

    payload = json.loads(call(populated.list_input_files, context_for("alpha")))

    assert {item["name"]: item["cache_status"] for item in payload} == {
        "fresh.txt": "new",
        "notes.txt": "stale",
    }
    # Nothing was processed by looking.
    assert not (tmp_path / "projects" / "alpha" / "cache" / "fresh.txt.md").exists()


def test_list_input_files_marks_up_to_date_files_as_cached(populated) -> None:
    payload = json.loads(call(populated.list_input_files, context_for("alpha")))

    assert [(item["name"], item["cache_status"]) for item in payload] == [("notes.txt", "cached")]
    assert payload[0]["processed_at"]


def test_process_file_processes_one_file_and_reuses_the_cache(tools, tmp_path: Path) -> None:
    write_input(tmp_path, "alpha", "a.txt", "one")
    write_input(tmp_path, "alpha", "b.txt", "two")

    first = json.loads(call(tools.process_file, context_for("alpha"), "a.txt"))
    again = json.loads(call(tools.process_file, context_for("alpha"), "a.txt"))

    assert (first["name"], first["status"]) == ("a.txt", "new")
    assert again["status"] == "cached"
    cache = tmp_path / "projects" / "alpha" / "cache"
    assert (cache / "a.txt.md").is_file()
    assert not (cache / "b.txt.md").exists()


def test_process_file_force_reprocesses_and_archives_the_previous_result(populated, tmp_path: Path) -> None:
    payload = json.loads(call(populated.process_file, context_for("alpha"), "notes.txt", True))

    assert payload["status"] == "updated"
    history = tmp_path / "projects" / "alpha" / "cache" / ".history"
    assert any(history.glob("notes.txt.*.md"))


@pytest.mark.parametrize("name", ["", "../secret.txt", "sub/notes.txt", "missing.txt", "image.png"])
def test_process_file_rejects_names_it_cannot_process(tools, tmp_path: Path, name: str) -> None:
    write_input(tmp_path, "alpha", "image.png", "not supported")

    payload = json.loads(call(tools.process_file, context_for("alpha"), name))

    assert "error" in payload


def test_process_file_streams_progress_and_reports_the_file(tools, tmp_path: Path) -> None:
    write_input(tmp_path, "alpha", "a.txt", "one")
    context = recording_context()

    call(tools.process_file, context, "a.txt")

    # A single text file has no sub-steps, so only the result is reported.
    assert context.progress == []


def test_list_providers_never_returns_key_values(tools, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "super-secret-value")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    raw = call(tools.list_providers, context_for("alpha"))
    providers = {item["name"]: item for item in json.loads(raw)}

    assert "super-secret-value" not in raw
    assert providers["google_genai"]["api_key_set"] is True
    assert providers["openai"]["api_key_set"] is False
    assert providers["google_genai"]["api_key_env"] == "GOOGLE_API_KEY"
    assert providers["openrouter"]["models"], "catalog providers list curated models"
    assert {"id", "capabilities"} <= set(providers["google_genai"]["models"][0])


def test_a_cancelled_request_stops_the_worker_at_its_next_checkpoint(tools) -> None:
    import threading
    import time

    import progress

    started = threading.Event()
    outcome: dict[str, bool] = {}

    def work() -> None:
        started.set()
        for _ in range(300):
            time.sleep(0.01)
            try:
                progress.reporter().stage("working")
            except progress.ProcessingCancelled:
                outcome["cancelled"] = True
                raise

    async def scenario() -> None:
        task = asyncio.create_task(tools._run_reported(context_for("alpha"), work))
        await asyncio.to_thread(started.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.3)

    asyncio.run(scenario())

    assert outcome == {"cancelled": True}


# --- listen address ------------------------------------------------------------


@pytest.mark.parametrize(
    ("host_env", "container_marker", "expected"),
    [
        ("10.1.2.3", False, "10.1.2.3"),  # an explicit HOST always wins
        ("127.0.0.1", True, "127.0.0.1"),
        (None, True, "0.0.0.0"),  # in a container: reachable through the published port
        (None, False, "127.0.0.1"),  # on a workstation: loopback only
    ],
)
def test_bind_host(tools, monkeypatch: pytest.MonkeyPatch, host_env, container_marker, expected) -> None:
    if host_env is None:
        monkeypatch.delenv("HOST", raising=False)
    else:
        monkeypatch.setenv("HOST", host_env)
    monkeypatch.setattr(tools.os.path, "exists", lambda path: container_marker and path == "/.dockerenv")

    assert tools.bind_host() == expected
