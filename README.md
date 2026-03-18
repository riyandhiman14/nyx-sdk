# Nyx Browser SDK

Stealth browser automation for Python. Real browser with anti-bot bypass built into the engine.

Two clean entry points:
- **`Browser` + `Page`** — Playwright-compatible API for web developers
- **`AgentBrowser`** — Snapshot-based API for AI agents (like browser-use)

## Install

```bash
pip install nyx-browser
```

The browser binary auto-downloads on first launch. To install manually:

```bash
nyx install
```

## Quick Start — Playwright-Compatible (Async)

```python
import asyncio
from nyx import Browser

async def main():
    async with await Browser.launch(headless=True) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")

        # Familiar Playwright API
        title = await page.title()
        print(f"Title: {title}")

        # CSS selectors
        await page.click("a")
        await page.fill("input[name=q]", "nyx browser")

        # JavaScript evaluation
        result = await page.evaluate("document.title")

        # Full HTML
        html = await page.content()

        # Screenshots
        await page.screenshot(path="page.png")

        # Locators (Playwright-style)
        loc = page.locator("h1")
        text = await loc.inner_text()
        print(f"H1: {text}")

asyncio.run(main())
```

## Quick Start — Playwright-Compatible (Sync)

```python
from nyx.sync_api import SyncBrowser

with SyncBrowser.launch() as browser:
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    page.screenshot(path="example.png")
```

## Quick Start — AI Agent API

Built for LLM-driven automation. Semantic snapshots with indexed elements, perceive-decide-act loop.

```python
import asyncio
from nyx import AgentBrowser

async def main():
    async with await AgentBrowser.launch() as browser:
        # Navigate and get structured page state
        snap = await browser.act("navigate", "https://books.toscrape.com")
        print(snap.page_text)      # Extracted text
        print(snap.elements)       # [{action_id, tag, text}, ...]

        # Act using action_ids from the snapshot
        snap = await browser.act("click", snap.elements[0]["action_id"])

        # Fill and submit forms
        snap = await browser.act("fill", "i_8e3f2a", value="Tokyo")
        snap = await browser.act("submit", "i_8e3f2a")

        # Batch actions
        snap = await browser.act_sequence([
            {"action": "fill", "target": "i_3a2b", "value": "Tokyo"},
            {"action": "submit", "target": "i_3a2b"},
        ])

        # Target resolution (tried in order):
        # 1. action_id  — "b_4f2a1c" (preferred)
        # 2. text:      — "text:Sign In"
        # 3. href:      — "href:/login"
        # 4. css:       — "css:button.primary"

asyncio.run(main())
```

## Proxy Support

```python
browser = await Browser.launch(
    proxy="http://user:pass@proxy.example.com:8080"
)
# or socks5
browser = await Browser.launch(
    proxy="socks5://proxy.example.com:1080"
)
```

## Nyx-Specific Features

Beyond the Playwright-compatible API, Nyx provides unique features on `Page`:

```python
# Semantic snapshots — structured page state for AI agents
snap = await page.snapshot()
print(snap.elements)   # Flat list of actionable elements
print(snap.page_text)  # Extracted text

# Semantic actions — click by description, not selector
snap = await page.act("click", "Sign In button")
snap = await page.act("fill", "search box", value="nyx browser")

# Anti-bot challenge handling
await page.wait_for_challenge(timeout=15)
```

## API Reference

### Browser

| Method | Description |
|--------|-------------|
| `Browser.launch(**kw)` | Launch new browser instance |
| `Browser.connect(host)` | Connect to running browser |
| `browser.new_page()` | Create new tab, returns `Page` |
| `browser.close()` | Shut down browser |

Launch options: `headless`, `proxy`, `timeout`, `version`, `auto_install`, `extra_args`.

### Page (Playwright-compatible)

| Method | Description |
|--------|-------------|
| `page.goto(url)` | Navigate to URL |
| `page.click(selector)` | Click element by CSS selector |
| `page.fill(selector, value)` | Fill input field |
| `page.type(selector, text)` | Type into element |
| `page.press(selector, key)` | Press key on element |
| `page.select_option(sel, val)` | Select dropdown option |
| `page.check(selector)` | Check checkbox |
| `page.uncheck(selector)` | Uncheck checkbox |
| `page.hover(selector)` | Hover over element |
| `page.evaluate(expr)` | Execute JavaScript |
| `page.content()` | Get full HTML |
| `page.title()` | Get page title |
| `page.url` | Current URL (property) |
| `page.screenshot(path=...)` | Take screenshot |
| `page.query_selector(sel)` | Find element |
| `page.query_selector_all(sel)` | Find all matching elements |
| `page.locator(sel)` | Create Locator |
| `page.wait_for_selector(sel)` | Wait for element |
| `page.wait_for_url(url)` | Wait for navigation |
| `page.wait_for_load_state()` | Wait for page load |
| `page.go_back()` | Navigate back |
| `page.go_forward()` | Navigate forward |
| `page.reload()` | Reload page |
| `page.inner_text(sel)` | Get element text |
| `page.inner_html(sel)` | Get element HTML |
| `page.is_visible(sel)` | Check visibility |
| `page.close()` | Close tab |
| `page.snapshot()` | Get semantic snapshot (Nyx) |
| `page.act(action, target)` | Semantic action (Nyx) |

### AgentBrowser (AI Agent API)

| Method | Description |
|--------|-------------|
| `AgentBrowser.launch(**kw)` | Launch new browser instance |
| `AgentBrowser.connect(host)` | Connect to running browser |
| `browser.snapshot(full=False)` | Get semantic page tree |
| `browser.act(action, target)` | Perform action, get snapshot |
| `browser.act_sequence(steps)` | Batch actions |
| `browser.navigate(url)` | Navigate to URL |
| `browser.text()` | Get extracted page text |
| `browser.page_html()` | Get full HTML |
| `browser.eval_js(script)` | Execute JavaScript |
| `browser.screenshot(path=...)` | Take screenshot |
| `browser.status()` | Check server status |
| `browser.wait_for(selector)` | Wait for CSS selector |
| `browser.wait_challenge()` | Wait for anti-bot challenge |
| `browser.tabs()` | List open tabs |
| `browser.new_tab(url)` | Open new tab |
| `browser.switch_tab(id)` | Switch to tab |
| `browser.close_tab(id)` | Close tab |
| `browser.session_create()` | Create session with config |
| `browser.session_status()` | Get session info |
| `browser.session_destroy()` | End session |
| `browser.media()` | Detect media elements |
| `browser.back()` / `forward()` | Navigate history |
| `browser.reset(url)` | Reset browser state |
| `browser.close()` | Shut down browser |

### Locator

```python
loc = page.locator("div.content")
await loc.click()
await loc.fill("text")
text = await loc.inner_text()
child = loc.locator("span")       # chain
first = loc.first()
items = await loc.all()
count = await loc.count()
```

### Snapshot

```python
snap = await browser.snapshot()
snap.url                  # Current URL
snap.title                # Page title
snap.page_text            # Extracted text content
snap.elements             # Flat list of actionable elements
snap.tree                 # Full semantic tree
snap.scroll_y             # Current scroll position
snap.has_more             # More content below viewport
snap.find("Sign In")      # Find element by text
snap.find_all("button")   # Find all matching text
snap.links()              # All <a> elements
snap.buttons()            # All <button> elements
snap.inputs()             # All <input>/<textarea> elements
```

## Stealth HTTP Client

For simple HTTP requests without a browser:

```python
from nyx import Nyx

client = Nyx(profile="random")
resp = client.get("https://example.com")
print(resp.status_code)
print(resp.text)
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NYX_HOME` | Browser install directory (default: `~/.nyx`) |
| `NYX_BROWSER_EXECUTABLE` | Override browser binary path |
| `NYX_RELEASES_REPO` | Override GitHub releases repo |

## CLI

```bash
nyx install              # Download browser binary
nyx install --force      # Force reinstall
nyx list                 # Show installed versions
nyx doctor               # Diagnostics
nyx uninstall <version>  # Remove a version
```
