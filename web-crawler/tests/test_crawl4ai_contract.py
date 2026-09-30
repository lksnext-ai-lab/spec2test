"""Contract tests for the crawl4ai API surface the crawler depends on.

``crawler.web_crawler`` builds its crawl4ai objects by hand, so an upgrade can
break the crawler without any import error. These tests construct the exact
objects the crawler constructs, so such a change fails loudly here instead of
at crawl time.
"""

from __future__ import annotations

import pytest
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.cache_context import CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


def markdown_generator() -> DefaultMarkdownGenerator:
    """The generator the crawler builds for every run."""
    return DefaultMarkdownGenerator(options={"citations": True})


def test_the_crawler_class_is_importable_from_the_package_root() -> None:
    assert AsyncWebCrawler is not None


def test_page_config_accepts_the_options_the_crawler_sets() -> None:
    config = CrawlerRunConfig(
        session_id="auth_crawl_session",
        markdown_generator=markdown_generator(),
        cache_mode=CacheMode.BYPASS,
        verbose=True,
    )

    assert config.session_id == "auth_crawl_session"
    assert config.markdown_generator is not None


def test_login_config_accepts_the_options_the_crawler_sets() -> None:
    config = CrawlerRunConfig(
        session_id=None,
        js_code="(async () => {})();",
        wait_for="() => true",
        cache_mode=CacheMode.BYPASS,
        verbose=True,
        page_timeout=60000,
        delay_before_return_html=2.0,
    )

    assert config.page_timeout == 60000
    assert config.delay_before_return_html == 2.0


def test_run_config_accepts_the_options_the_non_docker_path_sets() -> None:
    config = CrawlerRunConfig(
        session_id=None,
        exclude_external_links=True,
        markdown_generator=markdown_generator(),
        deep_crawl_strategy=DFSDeepCrawlStrategy(
            max_depth=2,
            include_external=False,
            max_pages=50,
        ),
        cache_mode=CacheMode.BYPASS,
        verbose=True,
    )

    assert config.deep_crawl_strategy is not None


def test_browser_config_accepts_the_options_the_crawler_sets() -> None:
    config = BrowserConfig(verbose=True, headless=True)

    assert config.headless is True


@pytest.mark.parametrize("strategy", [BFSDeepCrawlStrategy, DFSDeepCrawlStrategy])
def test_deep_crawl_strategies_accept_the_options_the_crawler_sets(strategy) -> None:
    """DFS subclasses BFS and forwards ``*args, **kwargs``."""
    strategy(max_depth=3, include_external=False, max_pages=100)
