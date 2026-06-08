#!/usr/bin/env python3
"""
Interactive browser action recorder for authentication.

Opens a real browser window where you can manually log in to any web application.
It records ALL your interactions (clicks, typing, form submissions, navigation)
and saves them as a replayable action sequence that the web crawler can use
to authenticate automatically.

Usage:
    python capture_auth.py <url> [--output auth_actions.json]

Examples:
    python capture_auth.py http://localhost:8080/administrator
    python capture_auth.py http://localhost:3000/admin --output my_app_auth.json
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Error: Playwright is not installed.")
    print("Install it with: pip install playwright && python -m playwright install chromium")
    sys.exit(1)


# JavaScript injected into the page to record user interactions
RECORDER_JS = """
(() => {
    if (window.__recorderInstalled) return;
    window.__recorderInstalled = true;

    // __reportAction is exposed by Playwright's expose_function — sends data to Python
    function report(action) {
        if (typeof window.__reportAction === 'function') {
            window.__reportAction(JSON.stringify(action));
        }
    }

    function getSelector(el) {
        // Priority 1: id
        if (el.id) return '#' + CSS.escape(el.id);

        // Priority 2: name attribute (for inputs)
        if (el.name && (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA')) {
            const sel = el.tagName.toLowerCase() + '[name="' + el.name + '"]';
            if (document.querySelectorAll(sel).length === 1) return sel;
        }

        // Priority 3: unique combination of tag + type + nearby attributes
        if (el.tagName === 'BUTTON' || (el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button'))) {
            if (el.type === 'submit') {
                const sel = el.tagName.toLowerCase() + '[type="submit"]';
                if (document.querySelectorAll(sel).length === 1) return sel;
            }
        }

        // Priority 4: build a path from parent
        const parts = [];
        let current = el;
        while (current && current !== document.body && current !== document.documentElement) {
            let sel = current.tagName.toLowerCase();
            if (current.id) {
                sel = '#' + CSS.escape(current.id);
                parts.unshift(sel);
                break;
            }
            const parent = current.parentElement;
            if (parent) {
                const siblings = Array.from(parent.children).filter(c => c.tagName === current.tagName);
                if (siblings.length > 1) {
                    const idx = siblings.indexOf(current) + 1;
                    sel += ':nth-of-type(' + idx + ')';
                }
            }
            parts.unshift(sel);
            current = current.parentElement;
        }
        return parts.join(' > ');
    }

    // Record clicks
    document.addEventListener('click', (e) => {
        const el = e.target.closest('a, button, input[type="submit"], input[type="button"], input[type="checkbox"], input[type="radio"], [role="button"], label');
        if (!el) return;
        
        const action = {
            type: 'click',
            selector: getSelector(el),
            tagName: el.tagName.toLowerCase(),
            text: el.textContent.trim().substring(0, 100),
            timestamp: Date.now()
        };
        
        if (el.tagName === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio')) {
            action.checked = el.checked;
        }
        
        report(action);
    }, true);

    // Record typing — capture on 'change' (fires when field loses focus / form submits)
    document.addEventListener('change', (e) => {
        const el = e.target;
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {
            if (el.type === 'checkbox' || el.type === 'radio') return;
            
            report({
                type: 'fill',
                selector: getSelector(el),
                tagName: el.tagName.toLowerCase(),
                inputType: el.type || 'text',
                value: el.value,
                timestamp: Date.now()
            });
        }
    }, true);

    // Also capture via 'input' events (debounced) for SPAs that don't fire 'change'
    let inputDebounce = {};
    document.addEventListener('input', (e) => {
        const el = e.target;
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
            if (el.type === 'checkbox' || el.type === 'radio') return;
            
            const sel = getSelector(el);
            clearTimeout(inputDebounce[sel]);
            inputDebounce[sel] = setTimeout(() => {
                report({
                    type: 'fill',
                    selector: sel,
                    tagName: el.tagName.toLowerCase(),
                    inputType: el.type || 'text',
                    value: el.value,
                    timestamp: Date.now()
                });
            }, 500);
        }
    }, true);

    // Record form submissions
    document.addEventListener('submit', (e) => {
        const form = e.target;
        // Capture all form field values before submitting
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(inp => {
            if (inp.type === 'hidden' || inp.type === 'submit' || inp.type === 'button') return;
            if (inp.type === 'checkbox' || inp.type === 'radio') return;
            report({
                type: 'fill',
                selector: getSelector(inp),
                tagName: inp.tagName.toLowerCase(),
                inputType: inp.type || 'text',
                value: inp.value,
                timestamp: Date.now()
            });
        });
        
        report({
            type: 'submit',
            selector: getSelector(form),
            tagName: 'form',
            timestamp: Date.now()
        });
    }, true);

    console.log('[RECORDER] Action recorder installed');
})();
"""


async def capture_auth_actions(url: str, output_file: str):
    """
    Open a headed browser, record all user interactions, and save them
    as a replayable action sequence for the web crawler.
    """
    separator = '=' * 60
    print(f"\n{separator}")
    print("  Authentication Action Recorder")
    print(f"{separator}")
    print(f"\n  Target URL: {url}")
    print(f"  Output:     {output_file}")
    print("\n  A browser window will open. Please:")
    print("  1. Log in to the application normally")
    print("  2. All your clicks/typing will be recorded")
    print("  3. Come back to this terminal and press ENTER when done")
    print(f"\n{separator}\n")

    recorded_navigations = []
    recorded_actions = []  # stored in Python, survives page navigations

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--allow-insecure-localhost",
                "--ignore-certificate-errors",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
            bypass_csp=True,
        )

        # Expose a Python function so the in-page JS can send actions back
        # to Python. This survives page navigations.
        async def on_action_recorded(action_json: str):
            action = json.loads(action_json)
            recorded_actions.append(action)
            atype = action.get("type", "?")
            sel = action.get("selector", "")
            if atype == "fill":
                val = "****" if action.get("inputType") == "password" else action.get("value", "")
                print(f"  [REC] FILL  {sel}  =  {val}")
            elif atype == "click":
                print(f"  [REC] CLICK {sel}  ({action.get('text', '')[:40]})")
            elif atype == "submit":
                print(f"  [REC] SUBMIT {sel}")

        await context.expose_function("__reportAction", on_action_recorded)

        # Inject recorder script into EVERY page/frame BEFORE any page JS runs
        await context.add_init_script(RECORDER_JS)

        page = await context.new_page()

        # Track navigations
        def on_navigate(frame):
            if frame == page.main_frame:
                nav_url = frame.url
                if nav_url and not nav_url.startswith("about:"):
                    recorded_navigations.append({
                        "type": "navigate",
                        "url": nav_url,
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    })
                    print(f"  [NAV] {nav_url}")

        page.on("framenavigated", on_navigate)

        print(f"  Opening {url} ...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            if "ERR_SSL_PROTOCOL_ERROR" in str(e) and url.startswith("https://"):
                http_url = url.replace("https://", "http://", 1)
                print(f"  SSL error detected. Retrying with HTTP: {http_url}")
                try:
                    await page.goto(http_url, wait_until="domcontentloaded", timeout=30000)
                    url = http_url
                except Exception as e2:
                    print(f"  Warning: Navigation issue: {e2}")
                    print("  The browser is still open — navigate manually.\n")
            else:
                print(f"  Warning: Navigation issue: {e}")
                print("  The browser is still open — navigate manually.\n")

        print("  >>> Recording started. Log in now. <<<")
        print("  >>> Press ENTER here when you are done. <<<\n")

        await asyncio.get_event_loop().run_in_executor(None, input)

        print("  Collecting recorded actions...")

        # Actions are already in recorded_actions (sent via __reportAction)
        browser_actions = recorded_actions

        # Get the final URL (where the user ended up after login)
        final_url = page.url

        await browser.close()

    # Deduplicate: remove fill actions that are immediately followed by a
    # newer fill on the same selector (keep only the last value)
    cleaned_actions = []
    for i, action in enumerate(browser_actions):
        if action["type"] == "fill":
            # Check if there's a later fill on the same selector
            has_later = any(
                a["type"] == "fill" and a["selector"] == action["selector"]
                for a in browser_actions[i + 1:]
            )
            if has_later:
                continue
        cleaned_actions.append(action)

    # Build the output
    auth_actions = {
        "_meta": {
            "captured_at": datetime.now().isoformat(),
            "target_url": url,
            "final_url": final_url,
            "tool": "capture_auth.py",
            "description": "Recorded browser actions for authentication replay"
        },
        "actions": cleaned_actions,
        "navigations": recorded_navigations,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(auth_actions, f, indent=2, ensure_ascii=False)

    # Print summary
    n_clicks = sum(1 for a in cleaned_actions if a["type"] == "click")
    n_fills = sum(1 for a in cleaned_actions if a["type"] == "fill")
    n_submits = sum(1 for a in cleaned_actions if a["type"] == "submit")

    print(f"\n  Recorded {len(cleaned_actions)} action(s):")
    print(f"    - {n_clicks} click(s)")
    print(f"    - {n_fills} fill(s) (typing)")
    print(f"    - {n_submits} form submission(s)")
    print(f"    - {len(recorded_navigations)} navigation(s)")

    # Print action sequence for review
    print(f"\n  Action sequence:")
    for i, action in enumerate(cleaned_actions, 1):
        if action["type"] == "fill":
            val = "****" if action.get("inputType") == "password" else action.get("value", "")
            print(f"    {i}. FILL  {action['selector']}  =  {val}")
        elif action["type"] == "click":
            print(f"    {i}. CLICK {action['selector']}  ({action.get('text', '')[:40]})")
        elif action["type"] == "submit":
            print(f"    {i}. SUBMIT {action['selector']}")

    print(f"\n  Saved to: {output_file}")
    print("\n  To use with the crawler, set in your .env:")
    print(f"    CRAWLER_AUTH_ACTIONS_FILE={output_file}")
    print(f"\n{separator}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Record browser authentication actions for the web crawler"
    )
    parser.add_argument("url", help="The URL to open for login")
    parser.add_argument(
        "--output", "-o",
        default="auth_actions.json",
        help="Output JSON file path (default: auth_actions.json)"
    )
    args = parser.parse_args()

    asyncio.run(capture_auth_actions(args.url, args.output))


if __name__ == "__main__":
    main()
