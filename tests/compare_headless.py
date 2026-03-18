"""
Nyx vs Playwright — Headless Mode Benchmark

Runs both browsers against the same targets and compares:
  - Anti-bot detection pass/fail
  - Fingerprint leak detection
  - Page load performance
  - JavaScript execution
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Add src to path for local dev
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class Result:
    test: str
    browser: str
    passed: bool
    ms: float
    details: dict = field(default_factory=dict)
    error: str | None = None


TESTS = [
    {
        "name": "Basic — example.com",
        "url": "https://example.com",
        "check": "title",
        "expected": "Example Domain",
    },
    {
        "name": "JS execution — httpbin headers",
        "url": "https://httpbin.org/headers",
        "check": "json_content",
    },
    {
        "name": "Anti-bot — SannySoft",
        "url": "https://bot.sannysoft.com/",
        "check": "sannysoft",
        "wait": 5,
    },
    {
        "name": "Headless detection — Vastel",
        "url": "https://arh.antoinevastel.com/bots/areyouheadless",
        "check": "vastel",
        "wait": 3,
    },
    {
        "name": "Anti-bot — CreepJS",
        "url": "https://abrahamjuliot.github.io/creepjs/",
        "check": "creepjs",
        "wait": 10,
    },
    {
        "name": "TLS fingerprint — browserleaks",
        "url": "https://tls.browserleaks.com/json",
        "check": "tls",
    },
    {
        "name": "WebDriver flag — navigator check",
        "url": "data:text/html,<script>document.title=navigator.webdriver?'WEBDRIVER':'CLEAN'</script>",
        "check": "webdriver",
    },
    {
        "name": "CDP detection — window.cdc",
        "url": "data:text/html,<script>document.title=(Object.keys(window).filter(k=>k.match(/cdc|driver|selenium|puppet/i)).length>0)?'DETECTED':'CLEAN'</script>",
        "check": "cdp_leak",
    },
]


# ── Playwright ────────────────────────────────────────────

async def pw_test(t: dict) -> Result:
    from playwright.async_api import async_playwright

    start = time.monotonic()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            url = t["url"]
            await page.goto(url, wait_until="networkidle", timeout=30000)

            if t.get("wait"):
                await page.wait_for_timeout(t["wait"] * 1000)

            check = t["check"]
            details = {}
            passed = False

            if check == "title":
                title = await page.title()
                details["title"] = title
                passed = t["expected"].lower() in title.lower()

            elif check == "json_content":
                text = await page.inner_text("body")
                try:
                    data = json.loads(text)
                    details["headers"] = data.get("headers", {})
                    ua = details["headers"].get("User-Agent", "")
                    details["user_agent"] = ua
                    passed = "headless" not in ua.lower()
                except json.JSONDecodeError:
                    details["raw"] = text[:200]
                    passed = False

            elif check == "sannysoft":
                # Evaluate in-page to count failed tests
                result = await page.evaluate("""() => {
                    const rows = document.querySelectorAll('table tr');
                    let passed = 0, failed = 0, results = {};
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const name = cells[0].textContent.trim();
                            const cls = cells[1].className;
                            if (cls.includes('failed')) { failed++; results[name] = 'FAIL'; }
                            else if (cls.includes('passed')) { passed++; results[name] = 'PASS'; }
                        }
                    });
                    return {passed, failed, results};
                }""")
                details = result
                passed = result.get("failed", 1) == 0

            elif check == "vastel":
                text = await page.inner_text("body")
                details["text"] = text[:300]
                passed = "not chrome headless" in text.lower()

            elif check == "creepjs":
                # Get the trust score element
                content = await page.content()
                text = await page.inner_text("body")
                details["page_length"] = len(text)
                details["has_score"] = "trust" in text.lower()
                # Check if "headless" appears in the fingerprint results
                details["headless_mentioned"] = text.lower().count("headless")
                passed = details["has_score"] and details["headless_mentioned"] == 0

            elif check == "tls":
                text = await page.inner_text("body")
                try:
                    data = json.loads(text)
                    details["ja3_hash"] = data.get("ja3_hash", "")[:20]
                    details["ja4"] = data.get("ja4", "")
                    details["akamai_hash"] = data.get("akamai_fingerprint_hash", "")[:20]
                    details["user_agent"] = data.get("user_agent", "")[:60]
                    passed = "headless" not in data.get("user_agent", "").lower()
                except json.JSONDecodeError:
                    details["raw"] = text[:100]
                    passed = False

            elif check == "webdriver":
                title = await page.title()
                details["title"] = title
                passed = title == "CLEAN"

            elif check == "cdp_leak":
                title = await page.title()
                details["title"] = title
                passed = title == "CLEAN"

            await browser.close()
            ms = (time.monotonic() - start) * 1000
            return Result(t["name"], "playwright", passed, ms, details)

    except Exception as e:
        ms = (time.monotonic() - start) * 1000
        return Result(t["name"], "playwright", False, ms, error=str(e)[:200])


# ── Nyx ───────────────────────────────────────────────────

async def nyx_test(t: dict, nyx_host: str) -> Result:
    from nyx.browser import Browser

    start = time.monotonic()
    try:
        async with await Browser.connect(nyx_host, timeout=10) as browser:
            snap = await browser.goto(t["url"])

            if t.get("wait"):
                await asyncio.sleep(t["wait"])
                snap = await browser.snapshot(full=True)

            check = t["check"]
            details = {}
            passed = False

            if check == "title":
                details["title"] = snap.title
                passed = t["expected"].lower() in snap.title.lower()

            elif check == "json_content":
                text = snap.page_text
                try:
                    data = json.loads(text)
                    details["headers"] = data.get("headers", {})
                    ua = details["headers"].get("User-Agent", "")
                    details["user_agent"] = ua
                    passed = "headless" not in ua.lower()
                except json.JSONDecodeError:
                    details["raw"] = text[:200]
                    passed = False

            elif check == "sannysoft":
                text = snap.page_text.lower()
                # Nyx doesn't have page.evaluate, so parse text
                fail_count = text.count("failed")
                details["page_text_length"] = len(text)
                details["fail_mentions"] = fail_count
                # Also look for specific known fails
                for keyword in ["webdriver", "chrome.runtime", "permissions", "plugins"]:
                    if keyword in text:
                        details[f"has_{keyword}"] = True
                passed = fail_count == 0

            elif check == "vastel":
                text = snap.page_text
                details["text"] = text[:300]
                passed = "not chrome headless" in text.lower()

            elif check == "creepjs":
                text = snap.page_text
                details["page_length"] = len(text)
                details["has_score"] = "trust" in text.lower()
                details["headless_mentioned"] = text.lower().count("headless")
                passed = details["has_score"] and details["headless_mentioned"] == 0

            elif check == "tls":
                text = snap.page_text
                try:
                    data = json.loads(text)
                    details["ja3_hash"] = data.get("ja3_hash", "")[:20]
                    details["ja4"] = data.get("ja4", "")
                    details["akamai_hash"] = data.get("akamai_fingerprint_hash", "")[:20]
                    details["user_agent"] = data.get("user_agent", "")[:60]
                    passed = "headless" not in data.get("user_agent", "").lower()
                except json.JSONDecodeError:
                    details["raw"] = text[:100]
                    passed = False

            elif check == "webdriver":
                details["title"] = snap.title
                # Nyx uses CEF — check if webdriver flag is exposed
                passed = snap.title == "CLEAN"

            elif check == "cdp_leak":
                details["title"] = snap.title
                passed = snap.title == "CLEAN"

            ms = (time.monotonic() - start) * 1000
            return Result(t["name"], "nyx", passed, ms, details)

    except Exception as e:
        ms = (time.monotonic() - start) * 1000
        return Result(t["name"], "nyx", False, ms, error=str(e)[:200])


# ── Runner ────────────────────────────────────────────────

def fmt_status(passed: bool) -> str:
    return "\033[32mPASS\033[0m" if passed else "\033[31mFAIL\033[0m"


def fmt_ms(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms/1000:.1f}s"


async def run(nyx_host: str = "http://localhost:8765"):
    print("\n\033[1mNyx vs Playwright — Headless Benchmark\033[0m")
    print("=" * 70)

    # Verify both browsers are reachable
    print("\nChecking Playwright...", end=" ", flush=True)
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            await b.close()
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        print("Install: pip install playwright && playwright install chromium")
        return

    print("Checking Nyx...", end=" ", flush=True)
    try:
        from nyx.browser import Browser
        async with await Browser.connect(nyx_host, timeout=5) as browser:
            await browser.status()
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        print(f"Start the browser: open NyxBrowser.app or launch with --headless --agent-port 8765")
        return

    pw_results: list[Result] = []
    nyx_results: list[Result] = []

    for t in TESTS:
        print(f"\n--- {t['name']} ---")
        print(f"    {t['url'][:70]}")

        # Run sequentially to avoid port contention on Nyx (single instance)
        pw = await pw_test(t)
        nyx = await nyx_test(t, nyx_host)

        pw_results.append(pw)
        nyx_results.append(nyx)

        print(f"    Playwright: {fmt_status(pw.passed)}  {fmt_ms(pw.ms)}")
        if pw.error:
            print(f"      error: {pw.error}")
        for k, v in pw.details.items():
            val = str(v)
            if len(val) > 70:
                val = val[:67] + "..."
            print(f"      {k}: {val}")

        print(f"    Nyx:        {fmt_status(nyx.passed)}  {fmt_ms(nyx.ms)}")
        if nyx.error:
            print(f"      error: {nyx.error}")
        for k, v in nyx.details.items():
            val = str(v)
            if len(val) > 70:
                val = val[:67] + "..."
            print(f"      {k}: {val}")

    # ── Summary table ─────────────────────────────────────
    print(f"\n\033[1m{'═' * 70}\033[0m")
    print(f"\033[1m  RESULTS SUMMARY\033[0m")
    print(f"\033[1m{'═' * 70}\033[0m\n")

    print(f"  {'Test':<35} {'Playwright':>12} {'Nyx':>12}  {'Winner':>8}")
    print(f"  {'─' * 67}")

    pw_wins = 0
    nyx_wins = 0
    ties = 0

    for pw, nyx in zip(pw_results, nyx_results):
        p_s = "PASS" if pw.passed else "FAIL"
        n_s = "PASS" if nyx.passed else "FAIL"

        if nyx.passed and not pw.passed:
            winner = "Nyx"
            nyx_wins += 1
        elif pw.passed and not nyx.passed:
            winner = "PW"
            pw_wins += 1
        elif pw.passed and nyx.passed:
            winner = "tie"
            ties += 1
        else:
            winner = "both fail"
            ties += 1

        print(f"  {pw.test:<35} {p_s:>12} {n_s:>12}  {winner:>8}")

    pw_total = sum(1 for r in pw_results if r.passed)
    nyx_total = sum(1 for r in nyx_results if r.passed)
    total = len(TESTS)

    print(f"  {'─' * 67}")
    print(f"  {'TOTAL':<35} {pw_total:>9}/{total} {nyx_total:>9}/{total}")
    print()

    # ── Performance table ─────────────────────────────────
    print(f"  {'Test':<35} {'PW time':>10} {'Nyx time':>10} {'Faster':>8}")
    print(f"  {'─' * 63}")

    pw_faster_count = 0
    nyx_faster_count = 0

    for pw, nyx in zip(pw_results, nyx_results):
        if nyx.ms < pw.ms:
            faster = "Nyx"
            nyx_faster_count += 1
        else:
            faster = "PW"
            pw_faster_count += 1
        print(f"  {pw.test:<35} {fmt_ms(pw.ms):>10} {fmt_ms(nyx.ms):>10} {faster:>8}")

    print(f"  {'─' * 63}")
    pw_avg = sum(r.ms for r in pw_results) / len(pw_results)
    nyx_avg = sum(r.ms for r in nyx_results) / len(nyx_results)
    print(f"  {'Average':<35} {fmt_ms(pw_avg):>10} {fmt_ms(nyx_avg):>10}")
    print(f"  Faster in more tests: {'Nyx' if nyx_faster_count > pw_faster_count else 'Playwright'} "
          f"({nyx_faster_count} vs {pw_faster_count})")

    # ── Verdict ───────────────────────────────────────────
    print(f"\n\033[1m  VERDICT\033[0m")
    print(f"  Playwright: {pw_total}/{total} passed, avg {fmt_ms(pw_avg)}")
    print(f"  Nyx:        {nyx_total}/{total} passed, avg {fmt_ms(nyx_avg)}")

    if nyx_total > pw_total:
        print(f"\n  \033[32mNyx wins on stealth ({nyx_total} vs {pw_total} anti-bot tests passed)\033[0m")
    elif pw_total > nyx_total:
        print(f"\n  \033[33mPlaywright wins on pass rate ({pw_total} vs {nyx_total})\033[0m")
    else:
        print(f"\n  Tied on pass rate, check details above for nuance.")

    nyx_advantages = [pw.test for pw, nyx in zip(pw_results, nyx_results) if nyx.passed and not pw.passed]
    nyx_failures = [pw.test for pw, nyx in zip(pw_results, nyx_results) if not nyx.passed]

    if nyx_advantages:
        print(f"\n  Nyx advantages (passed where PW failed):")
        for t in nyx_advantages:
            print(f"    + {t}")

    if nyx_failures:
        print(f"\n  Nyx failures (needs work):")
        for t in nyx_failures:
            print(f"    - {t}")

    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Nyx vs Playwright headless benchmark")
    parser.add_argument("--nyx-host", default="http://localhost:8765",
                        help="Nyx AgentServer URL (default: http://localhost:8765)")
    args = parser.parse_args()
    asyncio.run(run(args.nyx_host))


if __name__ == "__main__":
    main()
