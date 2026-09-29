from collections import deque
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
from bs4 import BeautifulSoup
import re
import os
import json
from dotenv import load_dotenv
from urllib.parse import urlparse, urljoin

# Load environment variables
load_dotenv()

def is_running_in_docker():
    """Check if we're running inside a Docker container."""
    return os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"}

def canonicalize_url(url: str, base_url: str | None = None) -> str | None:
    """Normalize URLs and rewrite local hosts to host.docker.internal inside Docker."""
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    host = parsed.hostname or ""
    if is_running_in_docker() and host in LOCAL_HOSTS:
        host = "host.docker.internal"
        netloc = f"{host}:{parsed.port}" if parsed.port else host
        parsed = parsed._replace(netloc=netloc)

    parsed = parsed._replace(fragment="")
    return parsed.geturl()

def convert_localhost_url(url: str) -> str:
    """Convert local hosts to host.docker.internal when running in Docker."""
    converted = canonicalize_url(url)
    if converted and converted != url:
        print(f"  Docker detected: Converting {url} -> {converted}")
    return converted or url


def split_actions_by_navigation(actions: list, navigations: list) -> list:
    """
    Split recorded actions into stages bounded by recorded navigation timestamps.
    Each stage can be replayed on its corresponding navigation URL, allowing
    multi-page auth flows to continue after page transitions.
    """
    if not actions:
        return []

    sorted_actions = sorted(actions, key=lambda a: a.get("timestamp", 0))
    sorted_navs = sorted(navigations or [], key=lambda n: n.get("timestamp", 0))

    if not sorted_navs:
        return [{"stage": 1, "url": None, "actions": sorted_actions}]

    stages = []
    for index, nav in enumerate(sorted_navs):
        start_ts = nav.get("timestamp", 0)
        end_ts = sorted_navs[index + 1].get("timestamp", float("inf")) if index + 1 < len(sorted_navs) else float("inf")
        stage_actions = [a for a in sorted_actions if start_ts <= a.get("timestamp", 0) < end_ts]
        stages.append({
            "stage": index + 1,
            "url": nav.get("url"),
            "actions": stage_actions,
            "start_ts": start_ts,
            "end_ts": end_ts,
        })

    assigned_ids = {id(a) for s in stages for a in s["actions"]}
    unassigned_actions = [a for a in sorted_actions if id(a) not in assigned_ids]
    if unassigned_actions:
        if stages:
            stages[-1]["actions"].extend(unassigned_actions)
        else:
            stages.append({"stage": 1, "url": None, "actions": unassigned_actions})

    return stages

def get_xpath(element):
    components = []
    current = element
    
    # Traverse up the DOM tree
    while current and current.name != '[document]':
        # Check if element has an id
        if current.get('id'):
            # Return xpath with id but continue to include parent path for more precision
            id_path = f"//*[@id='{current['id']}']"
            # Find position among siblings of same type
            siblings = current.find_previous_siblings(current.name)
            position = len(siblings) + 1
            
            # Insert remaining components after the id-based element
            if components:
                return f"{id_path}/{'/'.join(components)}"
            else:
                return id_path
        
        # Find position among siblings of same type
        siblings = current.find_previous_siblings(current.name)
        position = len(siblings) + 1
        
        # Add to xpath components
        components.insert(0, f"{current.name}[{position}]")
        
        # Move up to parent
        current = current.parent
    
    # Construct final xpath
    if components:
        return "/" + "/".join(components)
    return ""

def load_auth_actions_file() -> dict | None:
    """Load the recorded auth actions file (from capture_auth.py) if configured."""
    auth_file = os.getenv('CRAWLER_AUTH_ACTIONS_FILE')
    if not auth_file:
        return None

    # Resolve relative paths
    if not os.path.isabs(auth_file):
        potential_path = os.path.join('/app', auth_file)
        if os.path.exists(potential_path):
            auth_file = potential_path
        elif not os.path.exists(auth_file):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            potential_path = os.path.join(os.path.dirname(current_dir), auth_file)
            if os.path.exists(potential_path):
                auth_file = potential_path

    if not os.path.exists(auth_file):
        print(f"Warning: Auth actions file not found: {auth_file}")
        return None

    try:
        with open(auth_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded auth actions from: {auth_file}")
        return data
    except Exception as e:
        print(f"Warning: Error loading auth actions file: {e}")
        return None


def build_replay_js(actions: list) -> str:
    """
    Convert a list of recorded actions into JavaScript that replays them EXACTLY in order.
    Preserves the exact sequence of user interactions as recorded.
    """
    # Use recorded actions in exact order - no reordering
    replay_actions = list(actions)

    js_lines = [
        "(async () => {",
        "  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }",
        "  async function waitForSelector(selector, timeoutMs = 15000) {",
        "    const started = Date.now();",
        "    while (Date.now() - started < timeoutMs) {",
        "      const el = document.querySelector(selector);",
        "      if (el) return el;",
        "      await sleep(100);",
        "    }",
        "    return null;",
        "  }",
        "  function dispatchEvents(el) {",
        "    el.dispatchEvent(new Event('input', { bubbles: true }));",
        "    el.dispatchEvent(new Event('change', { bubbles: true }));",
        "  }",
        "",
    ]

    for i, action in enumerate(replay_actions):
        selector = json.dumps(action.get("selector", ""))
        action_type = action.get("type", "")

        if action_type == "fill":
            value = json.dumps(action.get("value", ""))
            js_lines.append(f"  // Action {i+1}: fill {action.get('selector', '')}")
            js_lines.append(f"  {{ const el = await waitForSelector({selector});")
            js_lines.append(f"    if (el) {{ el.value = {value}; dispatchEvents(el); console.log('Filled', {selector}); }}")
            js_lines.append(f"    else {{ console.error('Not found:', {selector}); }} }}")
            js_lines.append("  await sleep(300);")

        elif action_type == "click":
            js_lines.append(f"  // Action {i+1}: click {action.get('selector', '')}")
            js_lines.append(f"  {{ const el = await waitForSelector({selector});")
            js_lines.append("    if (el) {")
            if action.get("checked") is not None:
                checked_value = "true" if action.get("checked") else "false"
                js_lines.append(f"      if (el.type === 'checkbox' || el.type === 'radio') {{ el.checked = {checked_value}; dispatchEvents(el); }}")
                js_lines.append("      else { el.click(); }")
            else:
                js_lines.append("      el.click();")
            js_lines.append(f"      console.log('Clicked', {selector});")
            js_lines.append("    }")
            js_lines.append(f"    else {{ console.error('Not found:', {selector}); }} }}")
            js_lines.append("  await sleep(500);")

        elif action_type == "submit":
            js_lines.append(f"  // Action {i+1}: submit {action.get('selector', '')}")
            js_lines.append(f"  {{ const el = await waitForSelector({selector});")
            js_lines.append(f"    if (el) {{ el.submit(); console.log('Submitted', {selector}); }}")
            js_lines.append(f"    else {{ console.error('Not found:', {selector}); }} }}")
            js_lines.append("  await sleep(1000);")

    js_lines.append("  console.log('Replay complete');")
    js_lines.append("})();")

    return "\n".join(js_lines)


def extract_internal_links(html: str, page_url: str, base_host: str) -> list[str]:
    soup = BeautifulSoup(html, 'html.parser')
    links = []

    for link in soup.find_all('a'):
        href = link.get('href')
        if not href:
            continue
        canonical = canonicalize_url(href, base_url=page_url)
        if not canonical:
            continue
        host = urlparse(canonical).hostname or ""
        if host != base_host:
            continue
        links.append(canonical)

    return links


async def crawl_pages(
    crawler: AsyncWebCrawler,
    start_url: str,
    use_DFS: bool,
    max_depth: int,
    max_pages: int,
    session_id: str | None,
) -> list:
    from crawl4ai.cache_context import CacheMode

    base_url = canonicalize_url(start_url) or start_url
    base_host = urlparse(base_url).hostname or ""

    page_config = CrawlerRunConfig(
        session_id=session_id,
        markdown_generator=DefaultMarkdownGenerator(
            options={"citations": True}
        ),
        cache_mode=CacheMode.BYPASS,
        verbose=True,
    )

    visited = set()
    queued = set()
    queue = deque([(base_url, 0)])
    queued.add(base_url)
    results = []

    while queue and len(results) < max_pages:
        current_url, depth = queue.pop() if use_DFS else queue.popleft()
        if current_url in visited:
            continue
        visited.add(current_url)

        result = await crawler.arun(url=current_url, config=page_config)
        results.append(result)

        if depth >= max_depth:
            continue
        if not getattr(result, "success", False) or not getattr(result, "html", None):
            continue

        page_url = canonicalize_url(getattr(result, "url", "")) or current_url
        for next_url in extract_internal_links(result.html, page_url, base_host):
            if next_url in visited or next_url in queued:
                continue
            if len(queued) + len(visited) >= max_pages:
                break
            queue.append((next_url, depth + 1))
            queued.add(next_url)

    return results


async def web_crawler(url: str, use_DFS: bool, max_depth: int, max_pages: int, use_auth: bool = True) -> str:
    from crawl4ai.cache_context import CacheMode

    # Convert local hosts to host.docker.internal if running in Docker
    url = convert_localhost_url(url)

    # Check if we have recorded auth actions to replay
    auth_data = load_auth_actions_file() if use_auth else None
    has_auth = auth_data and auth_data.get("actions")

    browser_config = BrowserConfig(
        verbose=True,
        headless=True,
    )

    output_lines = []
    session_id = "auth_crawl_session" if has_auth else None

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Step 1: If auth actions exist, navigate to the login page and replay them
        if has_auth:
            actions = auth_data["actions"]
            recorded_navigations = auth_data.get("navigations", [])

            # Use the target_url from the recording metadata for auth replay
            # This ensures we start from the same page where actions were recorded
            auth_start_url = auth_data.get("_meta", {}).get("target_url", url)
            auth_start_url = convert_localhost_url(auth_start_url)
            print(f"  Starting auth replay from: {auth_start_url}")

            final_url_recorded = auth_data.get("_meta", {}).get("final_url", "")
            final_url_converted = convert_localhost_url(final_url_recorded) if final_url_recorded else ""

            n_fills = sum(1 for a in actions if a["type"] == "fill")
            n_clicks = sum(1 for a in actions if a["type"] == "click")
            n_submits = sum(1 for a in actions if a["type"] == "submit")
            print(f"  Replaying {len(actions)} auth actions ({n_clicks} click(s), {n_fills} fill(s), {n_submits} submit(s) in exact order)...")

            navs_for_stages = [{**n, "url": convert_localhost_url(n.get("url", ""))} for n in recorded_navigations]
            stages = split_actions_by_navigation(actions, navs_for_stages)

            # If recorder didn't include navigations, keep single stage from target URL.
            if not stages:
                stages = [{"stage": 1, "url": auth_start_url, "actions": actions}]

            # Ensure first stage starts from auth_start_url.
            if stages and not stages[0].get("url"):
                stages[0]["url"] = auth_start_url

            stage_results = []

            for idx, stage in enumerate(stages):
                stage_actions = stage.get("actions", [])
                if not stage_actions:
                    continue

                stage_url = stage.get("url") or auth_start_url
                replay_js = build_replay_js(stage_actions)

                if idx + 1 < len(stages) and stages[idx + 1].get("url"):
                    next_stage_url = stages[idx + 1]["url"]
                    next_path = urlparse(next_stage_url).path
                    next_query = urlparse(next_stage_url).query
                    path_check = f"window.location.pathname === '{next_path}'" if next_path else "true"
                    query_check = f"window.location.search.includes('{next_query}')" if next_query else "true"
                    success_check = f"({path_check}) && ({query_check})" if next_query else path_check
                    wait_for_js = f"() => {{ return {success_check}; }}"
                elif final_url_converted:
                    final_path = urlparse(final_url_converted).path
                    final_query = urlparse(final_url_converted).query
                    path_check = f"window.location.pathname === '{final_path}'" if final_path else "true"
                    query_check = f"window.location.search.includes('{final_query}')" if final_query else "true"
                    success_check = f"({path_check}) && ({query_check})" if final_query else path_check
                    wait_for_js = f"() => {{ return {success_check}; }}"
                else:
                    wait_for_js = "() => true"

                print(f"  Auth replay stage {idx + 1}/{len(stages)} at {stage_url} with {len(stage_actions)} action(s)")

                login_config = CrawlerRunConfig(
                    session_id=session_id,
                    js_code=replay_js,
                    wait_for=wait_for_js,
                    cache_mode=CacheMode.BYPASS,
                    verbose=True,
                    page_timeout=60000,
                    delay_before_return_html=2.0,
                )

                stage_result = await crawler.arun(url=stage_url, config=login_config)
                stage_result_summary = {
                    "stage": idx + 1,
                    "url": stage_url,
                    "action_count": len(stage_actions),
                    "success": bool(getattr(stage_result, "success", False)),
                    "status_code": getattr(stage_result, "status_code", None),
                    "error_message": getattr(stage_result, "error_message", None),
                    "result_url": getattr(stage_result, "url", None),
                }
                stage_results.append(stage_result_summary)
                print(
                    "  Auth stage result: "
                    f"stage={idx + 1} success={stage_result_summary['success']} "
                    f"status={stage_result_summary['status_code']} url={stage_result_summary['result_url']}"
                )

                if not stage_result_summary["success"]:
                    print(f"  Auth stage {idx + 1} failed: {stage_result_summary['error_message']}")
                    break

            final_stage_result = stage_results[-1] if stage_results else {
                "success": False,
                "status_code": None,
                "error_message": "No auth stages executed",
                "result_url": None,
            }

            if final_stage_result.get("success"):
                print("  Auth replay successful, proceeding with authenticated crawl...")
            else:
                print(f"  Auth replay issue: {final_stage_result.get('error_message')}")
                print("  Continuing with crawl anyway (may land on login page)...")

        # Step 2: Perform the main crawl (authenticated session if login was done)
        if is_running_in_docker():
            results = await crawl_pages(
                crawler=crawler,
                start_url=url,
                use_DFS=use_DFS,
                max_depth=max_depth,
                max_pages=max_pages,
                session_id=session_id,
            )
        else:
            run_config = CrawlerRunConfig(
                session_id=session_id,
                exclude_external_links=True,
                markdown_generator=DefaultMarkdownGenerator(
                    options={"citations": True}
                ),
                deep_crawl_strategy=DFSDeepCrawlStrategy(
                    max_depth=max_depth,
                    include_external=False,
                    max_pages=max_pages,
                ) if use_DFS else BFSDeepCrawlStrategy(
                    max_depth=max_depth,
                    include_external=False,
                    max_pages=max_pages,
                ),
                cache_mode=CacheMode.BYPASS,
                verbose=True,
            )

            results = await crawler.arun(
                url=url,
                config=run_config
            )

        # Clean up session
        if session_id:
            try:
                await crawler.crawler_strategy.kill_session(session_id)
            except Exception:
                pass

        for result in results:
            output_lines.append(f"\n# URL: {result.url}\n")
            if not result.success:
                # Check for connection refused error and provide LLM-friendly response
                if "ERR_CONNECTION_REFUSED" in str(result.error_message):
                    output_lines.append("""
## Connection Error
    The target website is not accessible. This could mean:
    - The website is down or offline
    - The URL is incorrect or the service is not running
    - Network connectivity issues
    - Firewall or security restrictions
    \nPlease verify the URL and ensure the target service is running and accessible.
                                        """)
                else:
                    output_lines.append(f"Crawl failed: {result.error_message}")
                    output_lines.append(f"Status code: {result.status_code}")
                continue

            try:
                # Process links
                output_lines.append("## Link URLs")
                unique_links = {link['href']: link for link in result.links['external'] + result.links['internal']}.values()
                for link in unique_links:
                    output_lines.append(f"- {link['href']}")

                # Process HTML using BeautifulSoup
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Extract links
                output_lines.append("\n## Links")
                links = soup.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text().strip() or link.get('title', '') or href
                    xpath = get_xpath(link)
                    output_lines.append(f"- name=\"{text}\", type=\"a\", xpath=\"{xpath}\", href=\"{href}\"")
                
                # Extract buttons
                output_lines.append("\n## Buttons")
                buttons = soup.find_all(['button', 'input'])
                for btn in buttons:
                    if btn.name == 'input' and btn.get('type') not in ['button', 'submit']:
                        continue  # Skip non-button inputs
                    
                    btn_type = btn.get('type', 'button')
                    title = ""
                    
                    if btn.name == 'button':
                        title = btn.get_text().strip()
                    else:  # input
                        title = btn.get('value', '')
                    
                    if not title:
                        # Try to use ID as name
                        if btn.get('id'):
                            title = btn.get('id')
                        # If no ID, try to use class as name
                        elif btn.get('class'):
                            title = ' '.join(btn.get('class'))
                        # Fall back to other attributes
                        else:
                            title = btn.get('name', '') or btn_type
                    
                    xpath = get_xpath(btn)
                    output_lines.append(f"- name=\"{title}\", type=\"{btn_type}\", xpath=\"{xpath}\"")
                
                # Extract inputs (excluding button/submit types)
                output_lines.append("\n## Inputs")
                inputs = soup.find_all('input')
                for inp in inputs:
                    inp_type = inp.get('type', 'text')
                    if inp_type in ['button', 'submit']:
                        continue  # Skip button inputs as they're already processed
                    
                    name = inp.get('name', '')
                    placeholder = inp.get('placeholder', '')
                    title = name or placeholder or inp_type
                    xpath = get_xpath(inp)
                    output_lines.append(f"- name=\"{title}\", type=\"{inp_type}\", xpath=\"{xpath}\"")
            
                output_lines.append('\n## Page content')
                output_lines.append(result.markdown.raw_markdown)
                # output_lines.append(result.markdown.references_markdown)
            except Exception as e:
                output_lines.append(f"Error processing HTML: {str(e)}")

    return "\n".join(output_lines)