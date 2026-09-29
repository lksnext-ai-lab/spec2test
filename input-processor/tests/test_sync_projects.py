"""The host-side script that turns projects.json into a compose override."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import sync_projects  # noqa: E402

from projects.model import SLUG_RE  # noqa: E402


def write_config(root: Path, payload: Any) -> Path:
    path = root / "projects.json"
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return path


def project_entry(root: Path, name: str = "shop-app", **extra: Any) -> dict[str, Any]:
    inputs = root / name / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    return {"name": name, "inputs": str(inputs), **extra}


def test_paths_are_read_from_the_configuration_file(tmp_path: Path) -> None:
    inputs = tmp_path / "specs" / "inputs"
    inputs.mkdir(parents=True)
    config = write_config(
        tmp_path,
        {
            "projects": [
                {
                    "name": "shop-app",
                    "inputs": "specs/inputs",
                    "preprocessed": "output/preprocessed",
                    "cache": "output/cache",
                }
            ]
        },
    )

    (project,) = sync_projects.load_config(config)

    assert project.inputs == inputs.resolve()
    assert project.preprocessed == (tmp_path / "output" / "preprocessed").resolve()
    assert project.cache == (tmp_path / "output" / "cache").resolve()


def test_output_folders_default_to_a_hidden_data_directory(tmp_path: Path) -> None:
    config = write_config(tmp_path, {"projects": [project_entry(tmp_path)]})

    (project,) = sync_projects.load_config(config)

    assert project.preprocessed == tmp_path / ".spec2test-data" / "shop-app" / "preprocessed"
    assert project.cache == tmp_path / ".spec2test-data" / "shop-app" / "cache"


def test_a_missing_configuration_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(sync_projects.ConfigError, match="not found"):
        sync_projects.load_config(tmp_path / "projects.json")


def test_an_invalid_configuration_file_is_reported(tmp_path: Path) -> None:
    config = write_config(tmp_path, "{ not json }")

    with pytest.raises(sync_projects.ConfigError, match="not valid JSON"):
        sync_projects.load_config(config)


def test_the_configuration_must_be_an_object(tmp_path: Path) -> None:
    config = write_config(tmp_path, "[]")

    with pytest.raises(sync_projects.ConfigError, match="must contain a JSON object"):
        sync_projects.load_config(config)


@pytest.mark.parametrize("payload", [{}, {"projects": []}, {"projects": "shop-app"}])
def test_the_projects_list_must_not_be_empty(tmp_path: Path, payload: Any) -> None:
    config = write_config(tmp_path, payload)

    with pytest.raises(sync_projects.ConfigError, match="non-empty 'projects' list"):
        sync_projects.load_config(config)


def test_each_entry_must_be_an_object(tmp_path: Path) -> None:
    config = write_config(tmp_path, {"projects": ["shop-app"]})

    with pytest.raises(sync_projects.ConfigError, match="must be an object"):
        sync_projects.load_config(config)


def test_invalid_names_are_refused(tmp_path: Path) -> None:
    config = write_config(tmp_path, {"projects": [{"name": "Shop App", "inputs": str(tmp_path)}]})

    with pytest.raises(sync_projects.ConfigError, match="Invalid project name"):
        sync_projects.load_config(config)


def test_duplicate_names_are_refused(tmp_path: Path) -> None:
    config = write_config(
        tmp_path, {"projects": [project_entry(tmp_path), project_entry(tmp_path)]}
    )

    with pytest.raises(sync_projects.ConfigError, match="defined twice"):
        sync_projects.load_config(config)


@pytest.mark.parametrize(
    ("name", "accepted"),
    [
        ("shop-app", True),
        ("shop_app", True),
        ("app2", True),
        ("a.b", True),
        ("Shop-App", False),
        ("-shop", False),
        ("", False),
        ("shop app", False),
        ("shop/app", False),
    ],
)
def test_the_name_rule_matches_the_container(name: str, accepted: bool) -> None:
    """The host script and the container must not drift apart."""
    assert bool(sync_projects.SLUG_RE.match(name)) is accepted
    assert bool(SLUG_RE.match(name)) is accepted


def test_missing_inputs_are_reported_together(tmp_path: Path) -> None:
    config = write_config(
        tmp_path,
        {
            "projects": [
                {"name": "alpha", "inputs": str(tmp_path / "nope-a")},
                {"name": "beta", "inputs": str(tmp_path / "nope-b")},
            ]
        },
    )
    projects = sync_projects.load_config(config)

    with pytest.raises(sync_projects.ConfigError) as error:
        sync_projects.check_paths(projects)

    message = str(error.value)
    assert "alpha" in message and "beta" in message
    assert "nope-a" in message and "nope-b" in message


def test_output_folders_are_created(tmp_path: Path) -> None:
    projects = sync_projects.load_config(
        write_config(tmp_path, {"projects": [project_entry(tmp_path)]})
    )

    sync_projects.create_output_folders(projects)

    assert projects[0].preprocessed.is_dir()
    assert projects[0].cache.is_dir()


def test_services_are_read_from_the_base_compose_file(tmp_path: Path) -> None:
    compose = tmp_path / "docker-compose.yaml"
    compose.write_text(
        "name: Spec2Test\n\nservices:\n  crawler:\n    image: x\n  input-processor:\n"
        "    image: y\n  filesystem-mcp:\n    image: z\n\nnetworks:\n  net:\n"
        "    driver: bridge\n",
        encoding="utf-8",
    )

    # The crawler is defined by the base file, but it has no use for the project
    # folders, so it is not handed any.
    assert sync_projects.configured_services(compose) == ("input-processor", "filesystem-mcp")

    assert sync_projects.configured_services(tmp_path / "missing.yaml") == sync_projects.SERVICES


def test_a_compose_file_without_our_services_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    compose = tmp_path / "docker-compose.yaml"
    compose.write_text("services:\n  crawler:\n    image: x\n", encoding="utf-8")
    config = write_config(tmp_path, {"projects": [project_entry(tmp_path)]})

    assert sync_projects.main(compose_args(tmp_path, config)) == 1

    assert "defines none of the services" in capsys.readouterr().err
    assert not (tmp_path / "docker-compose.override.yaml").exists()


def test_the_override_mounts_every_project_into_both_services(tmp_path: Path) -> None:
    config = write_config(
        tmp_path,
        {"projects": [project_entry(tmp_path, "alpha"), project_entry(tmp_path, "beta")]},
    )
    projects = sync_projects.load_config(config)

    override = sync_projects.render_override(projects, config, ("input-processor", "filesystem-mcp"))

    parsed = yaml.safe_load(override)
    assert set(parsed["services"]) == {"input-processor", "filesystem-mcp"}

    volumes = parsed["services"]["input-processor"]["volumes"]
    for name in ("alpha", "beta"):
        assert f"{tmp_path / name / 'inputs'}:/projects/{name}/inputs:ro" in volumes
        assert (
            f"{tmp_path / '.spec2test-data' / name / 'preprocessed'}"
            f":/projects/{name}/preprocessed"
        ) in volumes
        assert f"{tmp_path / '.spec2test-data' / name / 'cache'}:/projects/{name}/cache" in volumes
    assert f"{config.resolve()}:/config/projects.json:ro" in volumes
    assert parsed["services"]["filesystem-mcp"]["volumes"] == volumes


def test_the_override_is_header_commentated(tmp_path: Path) -> None:
    projects = sync_projects.load_config(
        write_config(tmp_path, {"projects": [project_entry(tmp_path)]})
    )

    override = sync_projects.render_override(projects, tmp_path / "projects.json", ("input-processor",))

    assert override.startswith("# Generated by scripts/sync_projects.py")
    assert "sync_projects.py" in override


def compose_args(tmp_path: Path, config: Path, *extra: str) -> list[str]:
    return [
        "--config",
        str(config),
        "--output",
        str(tmp_path / "docker-compose.override.yaml"),
        "--compose",
        str(tmp_path / "docker-compose.yaml"),
        *extra,
    ]


def test_main_writes_the_override_and_the_folders(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    config = write_config(tmp_path, {"projects": [project_entry(tmp_path)]})

    exit_code = sync_projects.main(compose_args(tmp_path, config))

    assert exit_code == 0
    output = tmp_path / "docker-compose.override.yaml"
    assert output.is_file()
    assert "input-processor" in output.read_text(encoding="utf-8")
    assert (tmp_path / ".spec2test-data" / "shop-app" / "cache").is_dir()
    assert "Next: docker compose up -d" in capsys.readouterr().out


def test_main_quiet_only_writes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    config = write_config(tmp_path, {"projects": [project_entry(tmp_path)]})

    assert sync_projects.main(compose_args(tmp_path, config, "--quiet")) == 0

    assert capsys.readouterr().out == ""
    assert (tmp_path / "docker-compose.override.yaml").is_file()


def test_check_validates_without_writing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    config = write_config(tmp_path, {"projects": [project_entry(tmp_path)]})

    assert sync_projects.main(compose_args(tmp_path, config, "--check")) == 0

    assert "Would write" in capsys.readouterr().out
    assert not (tmp_path / "docker-compose.override.yaml").exists()
    assert not (tmp_path / ".spec2test-data").exists()


def test_main_reports_missing_inputs_without_writing_anything(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    entry = {"name": "alpha", "inputs": str(tmp_path / "gone")}
    config = write_config(tmp_path, {"projects": [entry]})

    assert sync_projects.main(compose_args(tmp_path, config)) == 1

    assert "gone" in capsys.readouterr().err
    assert not (tmp_path / "docker-compose.override.yaml").exists()


def test_the_committed_example_is_valid() -> None:
    """projects.example.json must stay loadable: it is the copy-paste starting point."""
    example = Path(sync_projects.REPO_ROOT) / sync_projects.EXAMPLE_CONFIG

    projects = sync_projects.load_config(example)

    assert [project.name for project in projects] == ["shop-app", "admin-portal"]
    assert all(project.inputs.is_absolute() for project in projects)


def test_a_missing_configuration_file_exits_with_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    assert sync_projects.main(compose_args(tmp_path, tmp_path / "projects.json")) == 1

    assert "projects.example.json" in capsys.readouterr().err
