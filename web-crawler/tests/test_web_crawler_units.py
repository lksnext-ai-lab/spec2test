"""Unit tests for the crawler helpers that need no browser and no network."""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from crawler import web_crawler as crawler_module
from crawler.web_crawler import (
    build_replay_js,
    canonicalize_url,
    convert_localhost_url,
    extract_internal_links,
    get_xpath,
    load_auth_actions_file,
    split_actions_by_navigation,
)


# --- canonicalize_url --------------------------------------------------------


def test_canonicalize_url_strips_the_fragment() -> None:
    assert canonicalize_url("https://example.com/page#section") == "https://example.com/page"


def test_canonicalize_url_resolves_relative_paths() -> None:
    assert (
        canonicalize_url("/about", base_url="https://example.com/docs/intro")
        == "https://example.com/about"
    )


def test_canonicalize_url_rejects_non_http_schemes() -> None:
    assert canonicalize_url("mailto:team@example.com") is None
    assert canonicalize_url("javascript:void(0)") is None


def test_canonicalize_url_keeps_local_hosts_outside_docker(monkeypatch) -> None:
    monkeypatch.setattr(crawler_module, "is_running_in_docker", lambda: False)

    assert canonicalize_url("http://localhost:8080/app") == "http://localhost:8080/app"


def test_canonicalize_url_rewrites_local_hosts_inside_docker(monkeypatch) -> None:
    monkeypatch.setattr(crawler_module, "is_running_in_docker", lambda: True)

    assert (
        canonicalize_url("http://localhost:8080/app")
        == "http://host.docker.internal:8080/app"
    )


def test_convert_localhost_url_falls_back_to_the_original(monkeypatch) -> None:
    monkeypatch.setattr(crawler_module, "is_running_in_docker", lambda: False)

    assert convert_localhost_url("http://localhost:8080/app") == "http://localhost:8080/app"


# --- get_xpath ---------------------------------------------------------------


def test_get_xpath_uses_the_nearest_id() -> None:
    soup = BeautifulSoup('<div id="main"><a href="/x">Link</a></div>', "html.parser")

    assert get_xpath(soup.find("a")) == "//*[@id='main']/a[1]"


def test_get_xpath_falls_back_to_a_positional_path() -> None:
    soup = BeautifulSoup("<div><span>one</span><span>two</span></div>", "html.parser")

    assert get_xpath(soup.find_all("span")[1]).endswith("span[2]")


# --- extract_internal_links --------------------------------------------------


def test_extract_internal_links_keeps_only_same_host_http_links() -> None:
    html = (
        '<a href="/a">A</a>'
        '<a href="https://example.com/b?q=1#frag">B</a>'
        '<a href="https://other.example/c">C</a>'
        '<a href="mailto:team@example.com">D</a>'
        "<a>E</a>"
    )

    assert extract_internal_links(html, "https://example.com/page", "example.com") == [
        "https://example.com/a",
        "https://example.com/b?q=1",
    ]


# --- split_actions_by_navigation ---------------------------------------------


def test_split_actions_by_navigation_splits_on_navigation_timestamps() -> None:
    actions = [
        {"type": "fill", "timestamp": 100},
        {"type": "click", "timestamp": 250},
        {"type": "submit", "timestamp": 400},
    ]
    navigations = [
        {"timestamp": 0, "url": "https://example.com/login"},
        {"timestamp": 200, "url": "https://example.com/home"},
    ]

    stages = split_actions_by_navigation(actions, navigations)

    assert [stage["stage"] for stage in stages] == [1, 2]
    assert [len(stage["actions"]) for stage in stages] == [1, 2]
    assert stages[0]["url"] == "https://example.com/login"


def test_split_actions_without_navigations_returns_a_single_stage() -> None:
    stages = split_actions_by_navigation([{"type": "click", "timestamp": 1}], [])

    assert len(stages) == 1
    assert stages[0]["url"] is None
    assert len(stages[0]["actions"]) == 1


def test_split_actions_appends_actions_recorded_before_the_first_navigation() -> None:
    actions = [{"type": "click", "timestamp": 50}]
    navigations = [{"timestamp": 100, "url": "https://example.com/login"}]

    stages = split_actions_by_navigation(actions, navigations)

    assert [len(stage["actions"]) for stage in stages] == [1]


def test_split_actions_is_empty_safe() -> None:
    assert split_actions_by_navigation([], []) == []


# --- build_replay_js ---------------------------------------------------------


def test_build_replay_js_embeds_the_recorded_actions() -> None:
    js = build_replay_js([{"type": "fill", "selector": "#user", "value": "bob"}])

    assert "(async () => {" in js
    assert "#user" in js
    assert "bob" in js
    assert js.rstrip().endswith("})();")


def test_build_replay_js_handles_an_empty_action_list() -> None:
    assert build_replay_js([]).rstrip().endswith("})();")


# --- load_auth_actions_file --------------------------------------------------


def test_load_auth_actions_file_returns_none_when_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("CRAWLER_AUTH_ACTIONS_FILE", raising=False)

    assert load_auth_actions_file() is None


def test_load_auth_actions_file_reads_the_configured_file(tmp_path, monkeypatch) -> None:
    payload = {"actions": [{"type": "click"}], "navigations": []}
    path = tmp_path / "auth.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("CRAWLER_AUTH_ACTIONS_FILE", str(path))

    assert load_auth_actions_file() == payload


def test_load_auth_actions_file_returns_none_for_a_missing_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRAWLER_AUTH_ACTIONS_FILE", str(tmp_path / "missing.json"))

    assert load_auth_actions_file() is None
