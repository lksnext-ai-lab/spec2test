"""Projects: configuration, header selection and per-project runtimes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from projects.headers import project_name_from_context, project_name_from_headers, project_name_from_request
from projects.model import Project, ProjectConfigError, llm_settings_from
from projects.registry import ProjectNotFoundError, ProjectRegistry, find_configuration
from projects.runtime import ProjectRuntime, RuntimePool
from providers.native import AnthropicProvider, GoogleGenAIProvider, OpenAIProvider
from providers.openai_compatible import OpenAICompatibleProvider
from providers.registry import ProviderRegistry, build_default_registry
from settings import LlmSettings, Settings
from support import StubChatModel

ENV = {
    "GOOGLE_API_KEY": "google-key",
    "OPENAI_API_KEY": "openai-key",
    "ANTHROPIC_API_KEY": "anthropic-key",
    "DEEPSEEK_API_KEY": "deepseek-key",
    "OPENROUTER_API_KEY": "openrouter-key",
    "DASHSCOPE_API_KEY": "dashscope-key",
}


@pytest.fixture(autouse=True)
def _no_real_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[str] = []

    for provider_class in (
        GoogleGenAIProvider,
        OpenAIProvider,
        AnthropicProvider,
        OpenAICompatibleProvider,
    ):
        monkeypatch.setattr(
            provider_class,
            "create_chat_model",
            lambda self, model, api_key=None: created.append(f"{self.name}:{model}")
            or StubChatModel(f"{self.name}:{model}"),
        )


def write_config(root: Path, payload: Any, name: str = "projects.json") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return path


def make_project(root: Path, name: str = "alpha", **extra: Any) -> dict[str, Any]:
    return {"name": name, **extra}


def registry_for(root: Path, payload: Any) -> ProjectRegistry:
    return ProjectRegistry(write_config(root, payload), root / "projects")


def mounted(root: Path, name: str = "alpha") -> Path:
    inputs = root / "projects" / name / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    return inputs


# --- the project model -------------------------------------------------------


def test_a_project_derives_its_paths_from_its_name(tmp_path: Path) -> None:
    project = Project.from_entry(make_project(tmp_path), tmp_path / "projects")

    assert project.name == "alpha"
    assert project.inputs == tmp_path / "projects" / "alpha" / "inputs"
    assert project.preprocessed == tmp_path / "projects" / "alpha" / "preprocessed"
    assert project.cache == tmp_path / "projects" / "alpha" / "cache"
    assert project.segments_dir == project.cache / "_segments"


@pytest.mark.parametrize("name", ["", "Upper", "-leading", "with space", "slash/name", "../escape"])
def test_invalid_project_names_are_refused(tmp_path: Path, name: str) -> None:
    with pytest.raises(ProjectConfigError, match="Invalid project name"):
        Project.from_entry(make_project(tmp_path, name), tmp_path)


def test_a_project_inherits_the_defaults_and_overrides_what_it_sets(tmp_path: Path) -> None:
    defaults = LlmSettings(provider="deepseek", model="deepseek-chat")

    project = Project.from_entry(
        make_project(tmp_path, llm={"provider": "openrouter"}, vision={"model": "qwen-vl"}),
        tmp_path,
        defaults,
        LlmSettings(provider="google_genai", model="gemini-2.0-flash"),
    )

    assert project.llm == LlmSettings(provider="openrouter", model="deepseek-chat")
    assert project.vision == LlmSettings(provider="google_genai", model="qwen-vl")


def test_a_project_without_defaults_uses_the_built_in_provider(tmp_path: Path) -> None:
    project = Project.from_entry(make_project(tmp_path), tmp_path)

    assert project.llm.provider == "google_genai"
    assert project.llm.model is None
    assert project.vision is None


def test_llm_settings_parsing() -> None:
    assert llm_settings_from({"provider": "qwen", "model": "qwen-vl"}) == LlmSettings("qwen", "qwen-vl")
    assert llm_settings_from({"provider": "qwen"}) == LlmSettings(provider="qwen")
    assert llm_settings_from({"model": "qwen-vl"}) == LlmSettings(provider="", model="qwen-vl")
    assert llm_settings_from({}) is None
    assert llm_settings_from(None) is None


def test_llm_settings_must_be_an_object() -> None:
    with pytest.raises(ProjectConfigError, match="must be an object"):
        llm_settings_from(["qwen"])


def test_describe_lists_paths_and_models(tmp_path: Path) -> None:
    project = Project.from_entry(
        make_project(tmp_path, llm={"provider": "deepseek"}), tmp_path, None, None
    )

    described = project.describe()

    assert described["name"] == "alpha"
    assert described["provider"] == "deepseek"
    assert described["vision_provider"] == ""
    assert described["inputs"].endswith("alpha/inputs")


def test_an_unmounted_project_explains_how_to_fix_it(tmp_path: Path) -> None:
    project = Project.from_entry(make_project(tmp_path), tmp_path / "projects")

    with pytest.raises(ProjectConfigError) as error:
        project.check_mount()

    message = str(error.value)
    assert str(project.inputs) in message
    assert "scripts/sync_projects.py" in message


# --- configuration file ------------------------------------------------------


def test_projects_are_read_from_the_configuration_file(tmp_path: Path) -> None:
    registry = registry_for(
        tmp_path,
        {
            "defaults": {"llm": {"provider": "deepseek", "model": "deepseek-chat"}},
            "projects": [{"name": "alpha"}, {"name": "beta", "llm": {"provider": "qwen"}}],
        },
    )

    alpha, beta = registry.load()

    assert registry.names() == ("alpha", "beta")
    assert alpha.llm == LlmSettings("deepseek", "deepseek-chat")
    assert beta.llm == LlmSettings("qwen", "deepseek-chat")


def test_the_configuration_is_re_read_on_every_call(tmp_path: Path) -> None:
    file = write_config(tmp_path, {"projects": [{"name": "alpha"}]})
    registry = ProjectRegistry(file, tmp_path / "projects")

    assert registry.names() == ("alpha",)
    write_config(tmp_path, {"projects": [{"name": "alpha"}, {"name": "beta"}]})
    assert registry.names() == ("alpha", "beta")


def test_a_missing_configuration_file_is_reported(tmp_path: Path) -> None:
    registry = ProjectRegistry(tmp_path / "projects.json", tmp_path)

    with pytest.raises(ProjectConfigError) as error:
        registry.load()

    assert "not found" in str(error.value)
    assert "docker compose up -d" in str(error.value)


def test_an_invalid_configuration_file_is_reported(tmp_path: Path) -> None:
    registry = registry_for(tmp_path, "{ not json }")

    with pytest.raises(ProjectConfigError, match="not valid JSON"):
        registry.load()


def test_the_configuration_must_be_an_object(tmp_path: Path) -> None:
    registry = registry_for(tmp_path, "[]")

    with pytest.raises(ProjectConfigError, match="must contain a JSON object"):
        registry.load()


@pytest.mark.parametrize("payload", [{}, {"projects": []}, {"projects": "alpha"}])
def test_the_projects_list_must_not_be_empty(tmp_path: Path, payload: Any) -> None:
    registry = registry_for(tmp_path, payload)

    with pytest.raises(ProjectConfigError, match="non-empty 'projects' list"):
        registry.load()


def test_defaults_must_be_an_object(tmp_path: Path) -> None:
    registry = registry_for(tmp_path, {"defaults": [], "projects": [{"name": "alpha"}]})

    with pytest.raises(ProjectConfigError, match="'defaults' must be an object"):
        registry.load()


def test_each_entry_must_be_an_object(tmp_path: Path) -> None:
    registry = registry_for(tmp_path, {"projects": ["alpha"]})

    with pytest.raises(ProjectConfigError, match="must be an object"):
        registry.load()


def test_duplicate_project_names_are_refused(tmp_path: Path) -> None:
    registry = registry_for(tmp_path, {"projects": [{"name": "alpha"}, {"name": "alpha"}]})

    with pytest.raises(ProjectConfigError, match="defined twice"):
        registry.load()


def test_get_refuses_unknown_projects(tmp_path: Path) -> None:
    mounted(tmp_path, "alpha")
    registry = registry_for(tmp_path, {"projects": [{"name": "alpha"}, {"name": "beta"}]})

    with pytest.raises(ProjectNotFoundError) as error:
        registry.get("gamma")

    assert "Unknown project 'gamma'" in str(error.value)
    assert "alpha, beta" in str(error.value)


def test_get_without_a_name_explains_the_header(tmp_path: Path) -> None:
    mounted(tmp_path, "alpha")
    registry = registry_for(tmp_path, {"projects": [{"name": "alpha"}]})

    with pytest.raises(ProjectNotFoundError, match="X-Spec2Test-Project"):
        registry.get("   ")


def test_get_without_a_name_reports_a_broken_configuration(tmp_path: Path) -> None:
    registry = registry_for(tmp_path, {"projects": []})

    with pytest.raises(ProjectNotFoundError, match="non-empty 'projects' list"):
        registry.get("")


def test_get_checks_that_the_project_is_mounted(tmp_path: Path) -> None:
    registry = registry_for(tmp_path, {"projects": [{"name": "alpha"}]})

    with pytest.raises(ProjectConfigError, match="sync_projects.py"):
        registry.get("alpha")

    mounted(tmp_path, "alpha")
    assert registry.get("alpha").name == "alpha"


def test_find_configuration_prefers_the_repository_root(tmp_path: Path) -> None:
    assert find_configuration(tmp_path) is None

    write_config(tmp_path, {"projects": [{"name": "alpha"}]}, "config/projects.json")
    assert find_configuration(tmp_path) == tmp_path / "config" / "projects.json"

    root_config = write_config(tmp_path, {"projects": [{"name": "alpha"}]})
    assert find_configuration(tmp_path) == root_config


# --- header selection --------------------------------------------------------


class FakeRequest:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


class FakeContext:
    def __init__(self, headers: dict[str, str] | None) -> None:
        self.request_context = (
            None if headers is None else type("RC", (), {"request": FakeRequest(headers)})()
        )


def test_the_project_header_is_read_case_insensitively() -> None:
    assert project_name_from_headers({"X-Spec2Test-Project": "alpha"}) == "alpha"
    assert project_name_from_headers({"x-spec2test-project": " alpha "}) == "alpha"


def test_a_missing_or_empty_header_means_no_project() -> None:
    assert project_name_from_headers(None) is None
    assert project_name_from_headers({}) is None
    assert project_name_from_headers({"X-Spec2Test-Project": "  "}) is None
    assert project_name_from_headers({"Other": "value"}) is None


def test_the_project_is_taken_from_a_request_and_from_a_tool_context() -> None:
    headers = {"X-Spec2Test-Project": "alpha"}

    assert project_name_from_request(FakeRequest(headers)) == "alpha"
    assert project_name_from_request(None) is None
    assert project_name_from_context(FakeContext(headers)) == "alpha"


def test_a_context_without_a_request_is_harmless() -> None:
    assert project_name_from_context(None) is None
    assert project_name_from_context(object()) is None
    assert project_name_from_context(FakeContext(None)) is None


# --- runtimes ----------------------------------------------------------------


def project_for(tmp_path: Path, name: str = "alpha", **extra: Any) -> Project:
    mounted(tmp_path, name)
    return Project.from_entry(make_project(tmp_path, name, **extra), tmp_path / "projects")


def runtime_for(tmp_path: Path, project: Project) -> ProjectRuntime:
    return ProjectRuntime(project, build_default_registry(), ENV, Settings())


def test_clients_are_cached_per_provider_and_model(tmp_path: Path) -> None:
    runtime = runtime_for(tmp_path, project_for(tmp_path))

    first = runtime.main_handle()
    again = runtime.main_handle()
    other = runtime.handle_for(LlmSettings(provider="openai"))

    assert first is again
    assert other is not first
    assert other.label == "openai:gpt-4o-mini"


def test_a_project_specific_model_is_honoured(tmp_path: Path) -> None:
    project = project_for(tmp_path, llm={"provider": "openrouter", "model": "qwen/qwen2.5-vl-72b-instruct"})

    assert runtime_for(tmp_path, project).main_handle().model == "qwen/qwen2.5-vl-72b-instruct"


def test_vision_falls_back_to_a_main_model_that_sees_images(tmp_path: Path) -> None:
    runtime = runtime_for(tmp_path, project_for(tmp_path))

    assert runtime.vision_handle() is runtime.main_handle()


def test_vision_is_disabled_for_a_text_only_model(tmp_path: Path) -> None:
    runtime = runtime_for(tmp_path, project_for(tmp_path, llm={"provider": "deepseek"}))

    assert runtime.vision_handle() is None


def test_an_explicit_vision_model_is_used(tmp_path: Path) -> None:
    project = project_for(
        tmp_path, llm={"provider": "deepseek"}, vision={"provider": "qwen", "model": "qwen-vl-max"}
    )

    vision = runtime_for(tmp_path, project).vision_handle()

    assert vision is not None
    assert vision.label == "qwen:qwen-vl-max"


def test_the_service_is_built_once_and_knows_its_project(tmp_path: Path) -> None:
    runtime = runtime_for(tmp_path, project_for(tmp_path))

    service = runtime.service()

    assert service is runtime.service()
    assert service.input_dir == runtime.project.inputs
    assert service.cache.directory == runtime.project.cache
    assert service.provider == "google_genai"
    assert service.extensions == (".md", ".mp4", ".pdf", ".txt")
    assert runtime.lock is runtime.lock


def test_a_text_only_project_disables_pdf_enrichment(tmp_path: Path) -> None:
    runtime = runtime_for(tmp_path, project_for(tmp_path, llm={"provider": "deepseek"}))

    service = runtime.service()
    pdf = service.handlers.get("specs.pdf")

    assert pdf._converter is None  # type: ignore[attr-defined]
    assert service.handlers.get("notes.md")._enricher is None  # type: ignore[attr-defined]


def test_each_project_gets_its_own_runtime_and_lock(tmp_path: Path) -> None:
    registry = registry_for(
        tmp_path, {"projects": [{"name": "alpha"}, {"name": "beta"}]}
    )
    mounted(tmp_path, "alpha")
    mounted(tmp_path, "beta")
    pool = RuntimePool(registry, build_default_registry(), ENV, Settings())

    alpha = pool.for_name("alpha")
    beta = pool.for_name("beta")

    assert alpha is pool.for_name("alpha")
    assert alpha is not beta
    assert alpha.lock is not beta.lock
    assert alpha.project.cache != beta.project.cache
    assert pool.project_names() == ("alpha", "beta")


def test_an_unconfigured_project_is_refused_by_the_pool(tmp_path: Path) -> None:
    mounted(tmp_path, "alpha")
    pool = RuntimePool(
        registry_for(tmp_path, {"projects": [{"name": "alpha"}]}),
        build_default_registry(),
        ENV,
        Settings(),
    )

    with pytest.raises(ProjectNotFoundError):
        pool.for_name("gamma")


def test_adding_a_project_does_not_disturb_the_running_one(tmp_path: Path) -> None:
    file = write_config(tmp_path, {"projects": [{"name": "alpha"}]})
    mounted(tmp_path, "alpha")
    pool = RuntimePool(ProjectRegistry(file, tmp_path / "projects"), build_default_registry(), ENV, Settings())
    alpha = pool.for_name("alpha")

    mounted(tmp_path, "beta")
    write_config(tmp_path, {"projects": [{"name": "alpha"}, {"name": "beta"}]})

    assert pool.for_name("alpha") is alpha
    assert pool.for_name("beta").project.name == "beta"


def test_a_registry_without_the_default_provider_still_builds(tmp_path: Path) -> None:
    """The pool takes any registry, which is what makes the providers pluggable."""
    runtime = ProjectRuntime(
        project_for(tmp_path, llm={"provider": "openai"}),
        ProviderRegistry([OpenAIProvider()]),
        ENV,
        Settings(),
    )

    assert runtime.main_handle().provider_name == "openai"
