# Nyx Browser SDK

Stealth browser automation for Python. Real browser with anti-bot bypass built into the engine. **Playwright-compatible API** — switch from Playwright by changing one import.

## Install

```bash
pip install nyx-browser
```

The browser binary auto-downloads on first launch. To install manually:

```bash
nyx install
```

## Quick Start (Async)

```python
import asyncio
from nyx import Browser

async def main():
    async with await Browser.launch(headless=True) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")

        # Playwright-compatible API
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

## Quick Start (Sync)

```python
from nyx.sync_api import SyncBrowser

with SyncBrowser.launch() as browser:
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    page.screenshot(path="example.png")
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

Beyond the Playwright-compatible API, Nyx provides unique features:

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

### Page (Playwright-compatible)

| Method | Description |
|--------|-------------|
| `page.goto(url)` | Navigate to URL |
| `page.click(selector)` | Click element by CSS selector |
| `page.fill(selector, value)` | Fill input field |
| `page.type(selector, text)` | Type into element |
| `page.evaluate(expr)` | Execute JavaScript |
| `page.content()` | Get full HTML |
| `page.title()` | Get page title |
| `page.url` | Current URL (property) |
| `page.screenshot(path=...)` | Take screenshot |
| `page.query_selector(sel)` | Find element |
| `page.locator(sel)` | Create Locator |
| `page.wait_for_selector(sel)` | Wait for element |
| `page.wait_for_url(url)` | Wait for navigation |
| `page.go_back()` | Navigate back |
| `page.go_forward()` | Navigate forward |
| `page.reload()` | Reload page |
| `page.inner_text(sel)` | Get element text |
| `page.inner_html(sel)` | Get element HTML |
| `page.is_visible(sel)` | Check visibility |
| `page.close()` | Close tab |

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

## Stealth HTTP Client

For simple HTTP requests without a browser:

```python
from nyx import Nyx

client = Nyx(profile="random")
resp = client.get("https://example.com")
print(resp.status_code)
print(resp.text)
```

## CLI

```bash
nyx install              # Download browser binary
nyx list                 # Show installed versions
nyx doctor               # Diagnostics
```
