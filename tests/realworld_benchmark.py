"""
Real-world automation benchmark: Nyx (headless) vs Playwright (stealth)

Both browsers start with their BEST config from attempt 1.
On retry, each escalates further:
  - Playwright: new context with rotated UA + extra JS patches
  - Nyx: full browser restart (fresh TLS session, new fingerprint surface)

Scenarios test actual multi-step interactions on live anti-bot sites.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

NYX_HOST = "http://127.0.0.1:8765"

# Realistic UAs for Playwright retry rotation
UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]


@dataclass
class Attempt:
    num: int
    passed: bool
    ms: float
    steps: str  # "3/4"
    details: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class TestResult:
    name: str
    browser: str
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return any(a.passed for a in self.attempts)

    @property
    def best_ms(self) -> float:
        ok = [a.ms for a in self.attempts if a.passed]
        return min(ok) if ok else (self.attempts[-1].ms if self.attempts else 0)

    @property
    def tries_needed(self) -> int:
        for a in self.attempts:
            if a.passed:
                return a.num
        return -1


# ── Playwright runner (stealth from the start) ────────────

async def _pw_launch(attempt: int):
    """Launch Playwright with stealth. Attempt 2 rotates UA."""
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)

    ua = UA_POOL[min(attempt - 1, len(UA_POOL) - 1)]
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
        timezone_id="America/Los_Angeles",
        user_agent=ua,
    )

    # Apply stealth patches
    try:
        from playwright_stealth import stealth_async
        await stealth_async(context.pages[0] if context.pages else await context.new_page())
    except Exception:
        pass

    # Extra JS patches on every new page
    await context.add_init_script("""
        // Hide webdriver
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        // Fake plugins
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        // Fake languages
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
        // Chrome runtime stub
        window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
        // Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({state: Notification.permission})
                : originalQuery(parameters);
    """)

    page = await context.new_page()
    return pw, browser, context, page


async def run_pw(scenario_fn, attempt: int) -> Attempt:
    start = time.monotonic()
    pw_inst = browser = context = page = None
    try:
        pw_inst, browser, context, page = await _pw_launch(attempt)
        passed, done, total, details = await asyncio.wait_for(
            scenario_fn(page), timeout=60,
        )
        ms = (time.monotonic() - start) * 1000
        return Attempt(attempt, passed, ms, f"{done}/{total}", details)
    except Exception as e:
        ms = (time.monotonic() - start) * 1000
        return Attempt(attempt, False, ms, "0/?", error=str(e)[:200])
    finally:
        if browser:
            await browser.close()
        if pw_inst:
            await pw_inst.stop()


# ── Nyx runner ────────────────────────────────────────────

async def run_nyx(scenario_fn, attempt: int) -> Attempt:
    from nyx.browser import Browser

    start = time.monotonic()
    try:
        async with await Browser.connect(NYX_HOST, timeout=10) as browser:
            await browser.reset("about:blank")
            await asyncio.sleep(0.5)
            passed, done, total, details = await asyncio.wait_for(
                scenario_fn(browser), timeout=60,
            )
            ms = (time.monotonic() - start) * 1000
            return Attempt(attempt, passed, ms, f"{done}/{total}", details)
    except Exception as e:
        ms = (time.monotonic() - start) * 1000
        return Attempt(attempt, False, ms, "0/?", error=str(e)[:200])


def restart_nyx():
    """Kill and re-open for fresh fingerprint."""
    import subprocess, time as t
    subprocess.run(["pkill", "-f", "NyxBrowser"], capture_output=True)
    t.sleep(2)
    subprocess.run([
        "open",
        "/Users/riyandhiman/Library/Developer/Xcode/DerivedData/"
        "NyxBrowser-awyiibhcradzaqannlzawfvhtczf/Build/Products/Debug/NyxBrowser.app",
        "--args", "--agent-port", "8765", "--headless",
    ], capture_output=True)
    import urllib.request
    for _ in range(30):
        try:
            r = urllib.request.urlopen("http://127.0.0.1:8765/status", timeout=2)
            if r.status == 200:
                return
        except Exception:
            pass
        t.sleep(1)
    raise RuntimeError("Nyx restart failed")


# ══════════════════════════════════════════════════════════
#  SCENARIOS
# ══════════════════════════════════════════════════════════

# 1. Google Search — search + click result
async def google_pw(page):
    d = {}
    await page.goto("https://www.google.com", wait_until="networkidle", timeout=15000)
    s = 1

    box = page.locator('textarea[name="q"], input[name="q"]')
    await box.wait_for(state="visible", timeout=5000)
    await box.fill("python asyncio tutorial")
    await box.press("Enter")
    await page.wait_for_load_state("networkidle", timeout=10000)
    s = 2
    d["url"] = page.url

    body = await page.inner_text("body")
    if "unusual traffic" in body.lower() or "captcha" in body.lower():
        d["blocked"] = True
        return False, s, 3, d

    results = page.locator("#search a h3")
    cnt = await results.count()
    d["results"] = cnt
    if cnt == 0:
        return False, s, 3, d

    await results.first.click()
    await page.wait_for_load_state("domcontentloaded", timeout=10000)
    s = 3
    d["landed"] = page.url[:80]
    return "google.com" not in page.url, s, 3, d


async def google_nyx(browser):
    d = {}
    snap = await browser.goto("https://www.google.com")
    s = 1

    inp = snap.find("Search") or snap.find("search")
    if not inp:
        inputs = snap.inputs()
        inp = inputs[0] if inputs else None
    if not inp:
        d["err"] = "no search box"
        return False, s, 3, d

    snap = await browser.fill(inp["action_id"], "python asyncio tutorial")
    snap = await browser.submit(inp["action_id"])
    await asyncio.sleep(2)
    snap = await browser.snapshot(full=True)
    s = 2
    d["url"] = snap.url

    if "unusual traffic" in snap.page_text.lower():
        d["blocked"] = True
        return False, s, 3, d

    links = [l for l in snap.links()
             if l.get("text") and len(l["text"]) > 10
             and "google" not in (l.get("href") or "")]
    d["results"] = len(links)
    if not links:
        return False, s, 3, d

    snap = await browser.click(links[0]["action_id"])
    await asyncio.sleep(2)
    snap = await browser.snapshot()
    s = 3
    d["landed"] = snap.url[:80]
    return "google.com" not in snap.url, s, 3, d


# 2. Amazon — search + open product
async def amazon_pw(page):
    d = {}
    await page.goto("https://www.amazon.com", wait_until="networkidle", timeout=15000)
    s = 1

    body = await page.inner_text("body")
    if "captcha" in body.lower() or "robot" in body.lower():
        d["blocked"] = "landing captcha"
        return False, s, 3, d

    box = page.locator("#twotabsearchtextbox")
    await box.wait_for(state="visible", timeout=5000)
    await box.fill("mechanical keyboard")
    await box.press("Enter")
    await page.wait_for_load_state("networkidle", timeout=15000)
    s = 2

    body = await page.inner_text("body")
    if "captcha" in body.lower() or "robot" in body.lower():
        d["blocked"] = "search captcha"
        return False, s, 3, d

    prods = page.locator("[data-component-type='s-search-result'] h2 a")
    cnt = await prods.count()
    d["products"] = cnt
    if cnt == 0:
        d["text"] = body[:200]
        return False, s, 3, d

    await prods.first.click()
    await page.wait_for_load_state("domcontentloaded", timeout=10000)
    s = 3
    d["title"] = (await page.title())[:60]
    d["url"] = page.url[:80]
    return "/dp/" in page.url, s, 3, d


async def amazon_nyx(browser):
    d = {}
    snap = await browser.goto("https://www.amazon.com")
    s = 1

    if "captcha" in snap.page_text.lower() or "robot" in snap.page_text.lower():
        d["blocked"] = "landing captcha"
        return False, s, 3, d

    inp = snap.find("Search Amazon") or snap.find("search")
    if not inp:
        inputs = snap.inputs()
        inp = inputs[0] if inputs else None
    if not inp:
        d["err"] = "no search box"
        return False, s, 3, d

    snap = await browser.fill(inp["action_id"], "mechanical keyboard")
    snap = await browser.submit(inp["action_id"])
    await asyncio.sleep(3)
    snap = await browser.snapshot(full=True)
    s = 2

    if "captcha" in snap.page_text.lower() or "robot" in snap.page_text.lower():
        d["blocked"] = "search captcha"
        return False, s, 3, d

    links = [l for l in snap.links()
             if l.get("text") and len(l["text"]) > 15
             and "keyboard" in l["text"].lower()]
    if not links:
        links = [l for l in snap.links() if l.get("text") and len(l["text"]) > 20]
    d["products"] = len(links)
    if not links:
        return False, s, 3, d

    snap = await browser.click(links[0]["action_id"])
    await asyncio.sleep(2)
    snap = await browser.snapshot()
    s = 3
    d["title"] = snap.title[:60]
    d["url"] = snap.url[:80]
    return "/dp/" in snap.url or len(snap.title) > 10, s, 3, d


# 3. Cloudflare (nowsecure.nl)
async def cloudflare_pw(page):
    d = {}
    await page.goto("https://nowsecure.nl", wait_until="commit", timeout=20000)
    s = 1

    # Give CF challenge time
    await page.wait_for_timeout(8000)
    title = await page.title()
    body = await page.inner_text("body")
    d["title"] = title

    if "just a moment" in title.lower() or "checking" in title.lower():
        await page.wait_for_timeout(12000)
        title = await page.title()
        body = await page.inner_text("body")
        d["title_retry"] = title

    s = 2
    passed = "just a moment" not in title.lower() and "checking" not in title.lower() and len(body) > 50
    d["passed_cf"] = passed
    d["body"] = body[:150]
    return passed, s, 2, d


async def cloudflare_nyx(browser):
    d = {}
    snap = await browser.goto("https://nowsecure.nl")
    s = 1

    try:
        await browser.wait_challenge(timeout=20000)
    except Exception as e:
        d["challenge_err"] = str(e)[:80]

    await asyncio.sleep(3)
    snap = await browser.snapshot(full=True)
    s = 2
    d["title"] = snap.title
    d["body"] = snap.page_text[:150]

    passed = ("just a moment" not in snap.title.lower()
              and "checking" not in snap.title.lower()
              and len(snap.page_text) > 50)
    d["passed_cf"] = passed
    return passed, s, 2, d


# 4. Wikipedia — multi-step: search → article → click internal link
async def wiki_pw(page):
    d = {}
    await page.goto("https://en.wikipedia.org", wait_until="networkidle", timeout=10000)
    s = 1

    box = page.locator("#searchInput, input[name='search']")
    await box.fill("quantum computing")
    await box.press("Enter")
    await page.wait_for_load_state("networkidle", timeout=10000)
    s = 2
    d["article"] = (await page.title())[:50]

    # Should land on article directly or search results
    if "search" in page.url.lower():
        link = page.locator(".mw-search-result-heading a").first
        if await link.count():
            await link.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            d["article"] = (await page.title())[:50]
    s = 3

    # Click internal link
    internal = page.locator("#mw-content-text p a[href^='/wiki/']").first
    if await internal.count():
        await internal.click()
        await page.wait_for_load_state("networkidle", timeout=10000)
        s = 4
        d["linked"] = (await page.title())[:50]
        d["url"] = page.url[:60]
        return True, s, 4, d
    return s >= 3, s, 4, d


async def wiki_nyx(browser):
    d = {}
    snap = await browser.goto("https://en.wikipedia.org")
    s = 1

    inp = snap.find("Search Wikipedia") or snap.find("search")
    if not inp:
        inputs = snap.inputs()
        inp = inputs[0] if inputs else None
    if not inp:
        return False, s, 4, {"err": "no search"}

    snap = await browser.fill(inp["action_id"], "quantum computing")
    snap = await browser.submit(inp["action_id"])
    await asyncio.sleep(2)
    snap = await browser.snapshot(full=True)
    s = 2
    d["article"] = snap.title[:50]

    if "search" in snap.url.lower():
        qlinks = [l for l in snap.links() if "quantum" in (l.get("text") or "").lower()]
        if qlinks:
            snap = await browser.click(qlinks[0]["action_id"])
            await asyncio.sleep(2)
            snap = await browser.snapshot(full=True)
            d["article"] = snap.title[:50]
    s = 3

    links = snap.links()
    internal = [l for l in links if l.get("text")
                and len(l["text"]) > 3
                and "edit" not in l["text"].lower()
                and "wiki" not in l["text"].lower()
                and "[" not in l["text"]]
    if internal:
        snap = await browser.click(internal[0]["action_id"])
        await asyncio.sleep(2)
        snap = await browser.snapshot()
        s = 4
        d["linked"] = snap.title[:50]
        d["url"] = snap.url[:60]
        return True, s, 4, d
    return s >= 3, s, 4, d


# 5. GitHub — browse repo + open file
async def github_pw(page):
    d = {}
    await page.goto("https://github.com/psf/requests", wait_until="networkidle", timeout=15000)
    s = 1
    d["title"] = (await page.title())[:50]

    # Click on README
    readme = page.locator("a[title='README.md'], a[title='readme.md']").first
    if await readme.count():
        await readme.click()
    else:
        readme = page.locator("a.Link--primary[href*='README']").first
        if await readme.count():
            await readme.click()
    await page.wait_for_load_state("networkidle", timeout=10000)
    s = 2
    d["file_url"] = page.url[:70]

    body = await page.inner_text("article, .markdown-body, main")
    d["content_len"] = len(body)
    d["sample"] = body[:100]
    s = 3
    return len(body) > 50, s, 3, d


async def github_nyx(browser):
    d = {}
    snap = await browser.goto("https://github.com/psf/requests")
    await asyncio.sleep(2)
    snap = await browser.snapshot(full=True)
    s = 1
    d["title"] = snap.title[:50]

    links = snap.links()
    readme = next((l for l in links if "readme" in (l.get("text") or "").lower()), None)
    if readme:
        snap = await browser.click(readme["action_id"])
        await asyncio.sleep(2)
        snap = await browser.snapshot(full=True)
    s = 2
    d["file_url"] = snap.url[:70]

    d["content_len"] = len(snap.page_text)
    d["sample"] = snap.page_text[:100]
    s = 3
    return len(snap.page_text) > 50, s, 3, d


# 6. DuckDuckGo — JS SPA search + click
async def ddg_pw(page):
    d = {}
    await page.goto("https://duckduckgo.com", wait_until="networkidle", timeout=10000)
    s = 1

    box = page.locator("#searchbox_input, input[name='q']")
    await box.fill("rust programming language")
    await box.press("Enter")
    await page.wait_for_load_state("networkidle", timeout=10000)
    s = 2

    results = page.locator("[data-testid='result-title-a'], .result__a, article a")
    cnt = await results.count()
    d["results"] = cnt
    if cnt == 0:
        d["body"] = (await page.inner_text("body"))[:200]
        return False, s, 3, d

    await results.first.click()
    await page.wait_for_load_state("domcontentloaded", timeout=10000)
    s = 3
    d["landed"] = page.url[:80]
    return "duckduckgo" not in page.url, s, 3, d


async def ddg_nyx(browser):
    d = {}
    snap = await browser.goto("https://duckduckgo.com")
    s = 1

    inp = snap.find("Search") or snap.find("search")
    if not inp:
        inputs = snap.inputs()
        inp = inputs[0] if inputs else None
    if not inp:
        return False, s, 3, {"err": "no search box"}

    snap = await browser.fill(inp["action_id"], "rust programming language")
    snap = await browser.submit(inp["action_id"])
    await asyncio.sleep(3)
    snap = await browser.snapshot(full=True)
    s = 2
    d["url"] = snap.url[:70]

    links = [l for l in snap.links()
             if l.get("text") and len(l["text"]) > 10
             and "duckduckgo" not in (l.get("text") or "").lower()]
    d["results"] = len(links)
    if not links:
        d["all_links"] = [l.get("text", "")[:40] for l in snap.links()[:10]]
        return False, s, 3, d

    snap = await browser.click(links[0]["action_id"])
    await asyncio.sleep(2)
    snap = await browser.snapshot()
    s = 3
    d["landed"] = snap.url[:80]
    return "duckduckgo" not in snap.url, s, 3, d


# 7. Booking.com — hotel search (heavy anti-bot)
async def booking_pw(page):
    d = {}
    await page.goto("https://www.booking.com", wait_until="networkidle", timeout=20000)
    s = 1

    body = await page.inner_text("body")
    if "captcha" in body.lower() or "verify" in body.lower():
        d["blocked"] = True
        return False, s, 2, d

    title = await page.title()
    d["title"] = title[:60]
    d["body_len"] = len(body)
    s = 2
    # Just loading the homepage past anti-bot is a win
    passed = len(body) > 200 and "booking" in title.lower()
    return passed, s, 2, d


async def booking_nyx(browser):
    d = {}
    snap = await browser.goto("https://www.booking.com")
    await asyncio.sleep(3)
    snap = await browser.snapshot(full=True)
    s = 1

    if "captcha" in snap.page_text.lower() or "verify" in snap.page_text.lower():
        d["blocked"] = True
        return False, s, 2, d

    d["title"] = snap.title[:60]
    d["body_len"] = len(snap.page_text)
    s = 2
    passed = len(snap.page_text) > 200 and "booking" in snap.title.lower()
    return passed, s, 2, d


# ══════════════════════════════════════════════════════════

SCENARIOS = [
    ("Google Search + Click",       google_pw,     google_nyx),
    ("Amazon Product Search",       amazon_pw,     amazon_nyx),
    ("Cloudflare Challenge",        cloudflare_pw, cloudflare_nyx),
    ("Wikipedia Multi-step Nav",    wiki_pw,       wiki_nyx),
    ("GitHub Repo Browse",          github_pw,     github_nyx),
    ("DuckDuckGo SPA Search",       ddg_pw,        ddg_nyx),
    ("Booking.com Anti-bot",        booking_pw,    booking_nyx),
]


# ── Formatting ────────────────────────────────────────────

G = "\033[32m"; R = "\033[31m"; Y = "\033[33m"; B = "\033[1m"; D = "\033[2m"; X = "\033[0m"

def ok(p): return f"{G}PASS{X}" if p else f"{R}FAIL{X}"
def ms(t): return f"{t/1000:.1f}s" if t >= 1000 else f"{t:.0f}ms"


# ── Main ──────────────────────────────────────────────────

async def main():
    print(f"\n{B}Real-World Automation: Nyx (headless) vs Playwright (stealth){X}")
    print("=" * 72)
    print(f"  PW: stealth plugin + webdriver hide + chrome stub (best config)")
    print(f"  Nyx: headless CEF + aegis TLS engine")
    print(f"  2 attempts each. PW retries with rotated UA. Nyx restarts (fresh fingerprint).\n")

    all_pw: list[TestResult] = []
    all_nyx: list[TestResult] = []

    for name, pw_fn, nyx_fn in SCENARIOS:
        print(f"\n{'━' * 72}")
        print(f"  {B}{name}{X}")
        print(f"{'━' * 72}")

        pw_res = TestResult(name, "playwright")
        nyx_res = TestResult(name, "nyx")

        # ── PW attempt 1 ──
        print(f"  {D}PW #1 (stealth+patches)...{X}", end=" ", flush=True)
        a1 = await run_pw(pw_fn, 1)
        pw_res.attempts.append(a1)
        print(f"{ok(a1.passed)} {ms(a1.ms)} [{a1.steps}]")
        if a1.error: print(f"    {R}{a1.error}{X}")
        for k, v in a1.details.items():
            print(f"    {D}{k}: {str(v)[:65]}{X}")

        # ── PW attempt 2 ──
        if not a1.passed:
            print(f"  {D}PW #2 (rotated UA)...{X}", end=" ", flush=True)
            a2 = await run_pw(pw_fn, 2)
            pw_res.attempts.append(a2)
            print(f"{ok(a2.passed)} {ms(a2.ms)} [{a2.steps}]")
            if a2.error: print(f"    {R}{a2.error}{X}")
            for k, v in a2.details.items():
                print(f"    {D}{k}: {str(v)[:65]}{X}")

        # ── Nyx attempt 1 ──
        print(f"  {D}Nyx #1 (headless)...{X}", end=" ", flush=True)
        n1 = await run_nyx(nyx_fn, 1)
        nyx_res.attempts.append(n1)
        print(f"{ok(n1.passed)} {ms(n1.ms)} [{n1.steps}]")
        if n1.error: print(f"    {R}{n1.error}{X}")
        for k, v in n1.details.items():
            print(f"    {D}{k}: {str(v)[:65]}{X}")

        # ── Nyx attempt 2 ──
        if not n1.passed:
            print(f"  {D}Nyx #2 (restarting browser — fresh fingerprint)...{X}", end=" ", flush=True)
            try:
                restart_nyx()
                n2 = await run_nyx(nyx_fn, 2)
            except Exception as e:
                n2 = Attempt(2, False, 0, "0/?", error=str(e)[:200])
            nyx_res.attempts.append(n2)
            print(f"{ok(n2.passed)} {ms(n2.ms)} [{n2.steps}]")
            if n2.error: print(f"    {R}{n2.error}{X}")
            for k, v in n2.details.items():
                print(f"    {D}{k}: {str(v)[:65]}{X}")

        all_pw.append(pw_res)
        all_nyx.append(nyx_res)

    # ═══ SUMMARY ══════════════════════════════════════════

    print(f"\n\n{B}{'═' * 72}{X}")
    print(f"{B}  FINAL RESULTS{X}")
    print(f"{B}{'═' * 72}{X}\n")

    print(f"  {'Scenario':<30} {'Playwright':>10} {'try':>4}  {'Nyx':>10} {'try':>4}  {'Winner':>8}")
    print(f"  {'─' * 68}")

    pw_w = nyx_w = 0
    for pw, nyx in zip(all_pw, all_nyx):
        ps = f"{G}PASS{X}" if pw.passed else f"{R}FAIL{X}"
        ns = f"{G}PASS{X}" if nyx.passed else f"{R}FAIL{X}"
        pt = str(pw.tries_needed) if pw.passed else "—"
        nt = str(nyx.tries_needed) if nyx.passed else "—"
        if nyx.passed and not pw.passed:
            w = f"{G}Nyx{X}"; nyx_w += 1
        elif pw.passed and not nyx.passed:
            w = f"{Y}PW{X}"; pw_w += 1
        elif pw.passed and nyx.passed:
            w = "tie"
        else:
            w = f"{R}both{X}"
        print(f"  {pw.name:<30} {ps:>19} {pt:>4}  {ns:>19} {nt:>4}  {w:>17}")

    pw_tot = sum(1 for r in all_pw if r.passed)
    nyx_tot = sum(1 for r in all_nyx if r.passed)
    t = len(SCENARIOS)

    print(f"  {'─' * 68}")
    print(f"  {'TOTAL':<30} {pw_tot:>7}/{t}        {nyx_tot:>7}/{t}")

    # Performance
    print(f"\n  {'Scenario':<30} {'PW best':>10} {'Nyx best':>10} {'Faster':>8}")
    print(f"  {'─' * 58}")
    for pw, nyx in zip(all_pw, all_nyx):
        print(f"  {pw.name:<30} {ms(pw.best_ms):>10} {ms(nyx.best_ms):>10} "
              f"{'Nyx' if nyx.best_ms < pw.best_ms else 'PW':>8}")

    # Verdict
    print(f"\n  {B}VERDICT{X}")
    print(f"  Playwright (stealth): {pw_tot}/{t}")
    print(f"  Nyx (headless):       {nyx_tot}/{t}")

    nyx_only = [p.name for p, n in zip(all_pw, all_nyx) if n.passed and not p.passed]
    pw_only = [p.name for p, n in zip(all_pw, all_nyx) if p.passed and not n.passed]
    both_fail = [p.name for p, n in zip(all_pw, all_nyx) if not p.passed and not n.passed]

    if nyx_only:
        print(f"\n  {G}Nyx wins (PW couldn't):{X}")
        for n in nyx_only: print(f"    + {n}")
    if pw_only:
        print(f"\n  {Y}PW wins (Nyx couldn't):{X}")
        for n in pw_only: print(f"    + {n}")
    if both_fail:
        print(f"\n  {R}Both failed:{X}")
        for n in both_fail: print(f"    - {n}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
