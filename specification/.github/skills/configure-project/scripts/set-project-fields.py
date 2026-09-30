#!/usr/bin/env python3
"""Add an issue to a configured GitHub Project and update its fields."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
try:
    import project_config as pc  # noqa: E402
except ImportError as error:  # pragma: no cover - instalacion incompleta
    raise SystemExit(f"scripts/project_config.py is required next to .project.yml: {error}") from error

SELECT_FIELDS = ("Status", "Priority", "Size")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--repo", required=True, help="Alias declared in .project.yml")
    parser.add_argument("--status", help="Defaults to github_projects.fields.Status.default")
    parser.add_argument("--priority")
    parser.add_argument("--size")
    parser.add_argument("--estimate", type=int)
    parser.add_argument("--epic")
    parser.add_argument("--project-root", type=Path)
    return parser.parse_args(argv)


def load_configuration(config_path: Path, alias: str) -> dict[str, object]:
    try:
        config = pc.load_config_text(pc.read_text(config_path))
    except (OSError, pc.ConfigError) as error:
        raise SystemExit(f"Invalid .project.yml: {error}") from error
    if pc.get_bool(config, "github_projects.required") is not True:
        raise SystemExit("GitHub Projects is disabled in .project.yml")

    organization = pc.get_str(config, "github_projects.organization").strip()
    project_number = pc.get(config, "github_projects.number", "")
    repositories = pc.get(config, "repositories", []) or []
    entry = next(
        (item for item in repositories if isinstance(item, dict) and str(item.get("alias")) == alias),
        None,
    )
    if entry is None:
        raise SystemExit(f"Unknown repository alias: {alias}")
    if entry.get("enabled") is False:
        raise SystemExit(f"Repository alias is disabled in .project.yml (enabled: false): {alias}")
    slug = str(entry.get("slug") or "").strip()
    if any(pc.is_unresolved(value, config) for value in (organization, project_number, slug)):
        raise SystemExit("Configure github_projects and repositories in .project.yml")
    if isinstance(project_number, bool) or not re.fullmatch(r"\d+", str(project_number).strip()):
        raise SystemExit(f"github_projects.number must be a positive integer: {project_number}")

    def field_value(name: str, key: str, default=None):
        return pc.get(config, f"github_projects.fields.{name}.{key}", default)

    def field_list(name: str, key: str) -> list:
        value = field_value(name, key, [])
        return value if isinstance(value, list) else []

    status_default = field_value("Status", "default", None)
    scopes = pc.get(config, "integrations.github_cli.required_scopes", [])
    return {
        "organization": organization,
        "project_number": int(str(project_number).strip()),
        "repository_slug": slug,
        # Las opciones salen de github_projects.fields.<campo>.options, no de specification.
        "options": {name: [str(item) for item in field_list(name, "options")] for name in SELECT_FIELDS},
        "status_default": None if status_default is None else str(status_default),
        "estimate_values": [item for item in field_list("Estimate", "values") if isinstance(item, int)],
        # Un patron propio se respeta; el del kit (o su ausencia) sigue identifiers.epic.prefix.
        "epic_pattern": pc.prefix_pattern(config, "github_projects.fields.Epic.pattern"),
        "required_scopes": [str(scope) for scope in scopes] if isinstance(scopes, list) else [],
    }


def pattern_regex(pattern: str) -> re.Pattern[str] | None:
    """Turn an identifier pattern such as EPIC-N into a regex; N, M and K are numbers."""
    if not pattern:
        return None
    placeholder = re.compile(r"(?<![A-Za-z])([NMK])(?![A-Za-z])")
    parts = placeholder.split(pattern)
    body = "".join(r"\d+" if placeholder.fullmatch(part) else re.escape(part) for part in parts)
    return re.compile(f"^{body}$")


def default_fields(config: dict, requested: dict) -> dict:
    """Without --status, Status.default applies only to items newly added to the Project."""
    if requested.get("Status") is None and config.get("status_default"):
        return {"Status": config["status_default"]}
    return {}


def apply_defaults(config: dict, requested: dict) -> dict:
    """Requested fields plus the defaults for a new item (validation covers both)."""
    return {**requested, **default_fields(config, requested)}


def validate_requested(config: dict, requested: dict) -> None:
    for field_name in SELECT_FIELDS:
        value = requested.get(field_name)
        allowed = config["options"][field_name]
        if value is not None and allowed and value not in allowed:
            raise SystemExit(
                f"{field_name} is not defined in github_projects.fields.{field_name}.options: {value}"
            )
    estimate = requested.get("Estimate")
    if estimate is not None and config["estimate_values"] and estimate not in config["estimate_values"]:
        raise SystemExit(f"Estimate is not defined in .project.yml: {estimate}")
    epic = requested.get("Epic")
    regex = pattern_regex(str(config.get("epic_pattern") or ""))
    if epic is not None and regex is not None and not regex.match(epic):
        raise SystemExit(f"Epic must match {config['epic_pattern']}: {epic}")


def run_gh(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def token_scopes(auth_output: str) -> set[str] | None:
    """Scopes listed by ``gh auth status``; None when gh does not report them."""
    match = re.search(r"Token scopes:\s*(.*)", auth_output)
    if match is None:
        return None
    return {scope.strip(" '\"") for scope in match.group(1).split(",") if scope.strip(" '\"")}


def scope_satisfied(required: str, granted: set[str]) -> bool:
    if required in granted:
        return True
    # write:x y admin:x incluyen read:x; admin:x incluye write:x.
    if ":" in required:
        level, name = required.split(":", 1)
        stronger = {"read": ("write", "admin"), "write": ("admin",)}.get(level, ())
        return any(f"{candidate}:{name}" in granted for candidate in stronger)
    return False


def check_authentication(required_scopes: list[str]) -> None:
    status = run_gh(["auth", "status"], check=False)
    if status.returncode != 0:
        raise SystemExit("GitHub CLI is not authenticated; run: gh auth login")
    granted = token_scopes(f"{status.stdout}\n{status.stderr}")
    if not required_scopes:
        return
    if granted is None:
        print(
            "WARNING: gh auth status does not report token scopes; could not verify "
            f"integrations.github_cli.required_scopes ({', '.join(required_scopes)})",
            file=sys.stderr,
        )
        return
    missing = [scope for scope in required_scopes if not scope_satisfied(scope, granted)]
    if missing:
        raise SystemExit(
            "The GitHub token is missing required scopes from integrations.github_cli.required_scopes: "
            f"{', '.join(missing)}. Run: gh auth refresh -s {','.join(missing)}"
        )


def graphql(query: str, variables: dict[str, object]) -> dict:
    arguments = ["api", "graphql", "-f", f"query={query}"]
    for name, value in variables.items():
        flag = "-F" if isinstance(value, (int, float)) else "-f"
        arguments.extend((flag, f"{name}={value}"))
    result = run_gh(arguments, check=False)
    if result.returncode != 0:
        raise SystemExit(f"gh api graphql failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"gh returned invalid JSON: {error}") from error
    if response.get("errors"):
        raise SystemExit("GitHub GraphQL error: " + "; ".join(str(item.get("message")) for item in response["errors"]))
    return response


def find_option_id(field: dict, configured_value: str) -> str | None:
    """Exact option name only: a partial match could select the wrong option."""
    return next(
        (option["id"] for option in field.get("options", []) or [] if option.get("name") == configured_value),
        None,
    )


def resolve_updates(fields: dict, requested: dict) -> list[tuple[dict, object, str | None]]:
    """Resolves every requested field and option before any mutation."""
    resolved = []
    for field_name, value in requested.items():
        if value is None:
            continue
        field = fields.get(field_name)
        if field is None:
            raise SystemExit(f"Project field was not found: {field_name}")
        option_id = None
        if field.get("dataType") == "SINGLE_SELECT":
            option_id = find_option_id(field, str(value))
            if option_id is None:
                available = ", ".join(option.get("name", "") for option in field.get("options", []) or [])
                raise SystemExit(
                    f"Project option was not found: {field_name}={value} (exact match required; available: {available})"
                )
        resolved.append((field, value, option_id))
    return resolved


def update_field(project_id: str, item_id: str, field: dict, value: object, option_id: str | None = None) -> None:
    field_type = field.get("dataType")
    if field_type == "SINGLE_SELECT":
        option_id = option_id or find_option_id(field, str(value))
        if option_id is None:
            raise SystemExit(f"Project option was not found: {field['name']}={value}")
        value_type = "String"
        value_name = "optionId"
        value_object = "singleSelectOptionId: $optionId"
        graphql_value = option_id
    elif field_type == "NUMBER":
        value_type = "Float"
        value_name = "number"
        value_object = "number: $number"
        graphql_value = value
    else:
        value_type = "String"
        value_name = "text"
        value_object = "text: $text"
        graphql_value = str(value)

    mutation = f"""
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, ${value_name}: {value_type}!) {{
  updateProjectV2ItemFieldValue(input: {{
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: {{ {value_object} }}
  }}) {{ projectV2Item {{ id }} }}
}}
"""
    graphql(
        mutation,
        {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field["id"],
            value_name: graphql_value,
        },
    )


def main(argv: list[str] | None = None) -> int:
    pc.configure_stdio()
    args = parse_args(argv)
    project_root = (args.project_root or PROJECT_ROOT).resolve()
    config = load_configuration(project_root / ".project.yml", args.repo)

    requested_fields = {
        "Status": args.status,
        "Priority": args.priority,
        "Size": args.size,
        "Estimate": args.estimate,
        "Epic": args.epic,
    }
    # El Status.default se valida ya, pero solo se aplica si el item se anade ahora al Project:
    # un item existente conserva su Status (p. ej. "In progress") si no se pasa --status.
    new_item_defaults = default_fields(config, requested_fields)
    validate_requested(config, apply_defaults(config, requested_fields))

    if shutil.which("gh") is None:
        raise SystemExit("GitHub CLI (gh) is not installed")
    check_authentication(list(config.get("required_scopes") or []))

    repository_slug = str(config["repository_slug"])
    owner, repository = (
        repository_slug.split("/", 1)
        if "/" in repository_slug
        else (str(config["organization"]), repository_slug)
    )
    issue_query = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      id
      title
      projectItems(first: 100) { nodes { id project { id } } }
    }
  }
}
"""
    issue = graphql(
        issue_query,
        {"owner": owner, "repo": repository, "number": args.issue_number},
    )
    issue = ((issue.get("data") or {}).get("repository") or {}).get("issue")
    if issue is None:
        raise SystemExit(f"Issue #{args.issue_number} was not found in {repository_slug}")

    project_query = """
query($org: String!, $number: Int!) {
  organization(login: $org) {
    projectV2(number: $number) {
      id
      title
      fields(first: 100) {
        nodes {
          ... on ProjectV2Field { id name dataType }
          ... on ProjectV2SingleSelectField { id name dataType options { id name } }
        }
      }
    }
  }
}
"""
    project = graphql(
        project_query,
        {"org": config["organization"], "number": config["project_number"]},
    )
    project = ((project.get("data") or {}).get("organization") or {}).get("projectV2")
    if project is None:
        raise SystemExit(f"Project #{config['project_number']} was not found")

    fields = {
        field["name"]: field
        for field in ((project.get("fields") or {}).get("nodes") or [])
        if field and field.get("name")
    }
    # Se valida cada campo antes de mutar: un campo u opcion inexistente no deja el item a medias.
    updates = resolve_updates(fields, requested_fields)
    default_updates = resolve_updates(fields, new_item_defaults)

    item_id = next(
        (
            item["id"]
            for item in ((issue.get("projectItems") or {}).get("nodes") or [])
            if (item.get("project") or {}).get("id") == project["id"]
        ),
        None,
    )
    if item_id is None:
        add_mutation = """
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
    item { id }
  }
}
"""
        item_id = graphql(
            add_mutation,
            {"projectId": project["id"], "contentId": issue["id"]},
        )["data"]["addProjectV2ItemById"]["item"]["id"]
        updates = [*default_updates, *updates]

    for field, value, option_id in updates:
        update_field(project["id"], item_id, field, value, option_id)
        print(f"Configured {field['name']}: {value}")

    print(f"Project: https://github.com/orgs/{config['organization']}/projects/{config['project_number']}")
    print(f"Issue: https://github.com/{repository_slug}/issues/{args.issue_number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
