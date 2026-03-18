#!/usr/bin/env python3
"""
Nyx vs Playwright (headless) — side-by-side comparison.

Nyx uses aegis --browser-mode (CLI HTTP client).
Playwright launches headless Chromium.
"""

import time
import traceback


results = []

def run_test(name, nyx_fn, pw_fn):
    print(f"\n{'='*60}")
    print(f"  TEST: {name}")
    print(f"{'='*60}")

    print("\n  [Nyx]")
    nyx_ok, nyx_time, nyx_detail = _run(nyx_fn)

    print("\n  [Playwright]")
    pw_ok, pw_time, pw_detail = _run(pw_fn)

    results.append({
        "test": name,
        "nyx_pass": nyx_ok, "nyx_time": nyx_time, "nyx_detail": nyx_detail,
        "pw_pass": pw_ok, "pw_time": pw_time, "pw_detail": pw_detail,
    })


def _run(fn):
    start = time.time()
    try:
        detail = fn()
        elapsed = round(time.time() - start, 2)
        print(f"    PASS ({elapsed}s)")
        return True, elapsed, detail or "ok"
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        print(f"    FAIL ({elapsed}s): {e}")
        traceback.print_exc()
        return False, elapsed, str(e)


# ── Test 1: Fetch HTML ──────────────────────────────────────

def test1_nyx():
    from nyx import Nyx
    resp = Nyx().get("https://example.com")
    assert resp.status_code == 200
    assert "Example Domain" in resp.text
    return f"status={resp.status_code}, size={len(resp.body)}"

def test1_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://example.com")
        title = page.title()
        text = page.content()
        b.close()
        assert "Example Domain" in title
        return f"title={title}, size={len(text)}"


# ── Test 2: Headers sent ────────────────────────────────────

def test2_nyx():
    from nyx import Nyx
    resp = Nyx().get("https://httpbin.org/headers")
    h = resp.json()["headers"]
    assert "Sec-Ch-Ua" in h, f"no sec-ch-ua, got: {list(h.keys())}"
    return f"{len(h)} headers, UA={h.get('User-Agent','?')[:50]}"

def test2_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://httpbin.org/headers")
        text = page.inner_text("body")
        import json
        h = json.loads(text)["headers"]
        b.close()
        assert "User-Agent" in h
        return f"{len(h)} headers, UA={h.get('User-Agent','?')[:50]}"


# ── Test 3: POST JSON ──────────────────────────────────────

def test3_nyx():
    from nyx import Nyx
    resp = Nyx().post("https://httpbin.org/post", json={"test": True})
    data = resp.json()
    assert data["data"] == '{"test": true}'
    return f"status={resp.status_code}"

def test3_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        page = ctx.new_page()
        resp = page.evaluate("""async () => {
            const r = await fetch('https://httpbin.org/post', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({test: true})
            });
            return await r.json();
        }""")
        b.close()
        assert '"test": true' in resp["data"] or resp.get("json", {}).get("test") == True
        return f"status=200"


# ── Test 4: TLS Fingerprint ────────────────────────────────

def test4_nyx():
    from nyx import Nyx
    resp = Nyx().get("https://tls.peet.ws/api/all")
    data = resp.json()
    ja3 = data.get("tls", {}).get("ja3_hash", "n/a")
    ja4 = data.get("tls", {}).get("ja4", "n/a")
    return f"JA3={ja3[:20]}, JA4={ja4[:20]}"

def test4_pw():
    from playwright.sync_api import sync_playwright
    import json
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://tls.peet.ws/api/all", timeout=15000)
        text = page.inner_text("body")
        data = json.loads(text)
        b.close()
        ja3 = data.get("tls", {}).get("ja3_hash", "n/a")
        ja4 = data.get("tls", {}).get("ja4", "n/a")
        return f"JA3={ja3[:20]}, JA4={ja4[:20]}"


# ── Test 5: Anti-Bot (nowsecure.nl) ─────────────────────────

def test5_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://nowsecure.nl")
    blocked = resp.status_code in (403, 503) or "captcha" in resp.text.lower() or "challenge" in resp.text[:500].lower()
    status = "BLOCKED" if blocked else "PASSED"
    return f"status={resp.status_code}, {status}"

def test5_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        resp = page.goto("https://nowsecure.nl", timeout=15000)
        time.sleep(5)
        text = page.content()
        status_code = resp.status if resp else 0
        blocked = status_code in (403, 503) or "captcha" in text.lower() or "challenge" in text[:500].lower()
        status = "BLOCKED" if blocked else "PASSED"
        b.close()
        return f"status={status_code}, {status}"


# ── Test 6: Google Search ───────────────────────────────────

def test6_nyx():
    from nyx import Nyx
    resp = Nyx().get("https://www.google.com/search?q=nyx+browser")
    blocked = "sorry" in resp.url.lower() or resp.status_code == 429
    status = "BLOCKED" if blocked else "PASSED"
    return f"status={resp.status_code}, {status}, url={resp.url[:60]}"

def test6_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://www.google.com/search?q=nyx+browser", timeout=10000)
        page.wait_for_load_state("networkidle", timeout=10000)
        url = page.url
        blocked = "sorry" in url.lower() or "/sorry/" in url.lower()
        status = "BLOCKED" if blocked else "PASSED"
        b.close()
        return f"{status}, url={url[:60]}"


# ── Test 7: Response Speed (multiple requests) ─────────────

def test7_nyx():
    from nyx import Nyx
    client = Nyx()
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent",
    ]
    start = time.time()
    for url in urls:
        resp = client.get(url)
        assert resp.status_code == 200
    elapsed = round(time.time() - start, 2)
    return f"3 requests in {elapsed}s"

def test7_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        urls = [
            "https://httpbin.org/get",
            "https://httpbin.org/headers",
            "https://httpbin.org/user-agent",
        ]
        start = time.time()
        for url in urls:
            resp = page.goto(url)
            assert resp.status == 200
        elapsed = round(time.time() - start, 2)
        b.close()
        return f"3 requests in {elapsed}s"


# ── Test 8: Headless Detection ──────────────────────────────

def test8_nyx():
    from nyx import Nyx
    resp = Nyx().get("https://arh.antoinevastel.com/bots/areyouheadless")
    is_bot = "you are" in resp.text.lower() and "headless" in resp.text.lower()
    # Nyx is an HTTP client, not a browser — but it shouldn't look like a bot
    return f"size={len(resp.body)}, detected_headless={'yes' if is_bot else 'no'}"

def test8_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://arh.antoinevastel.com/bots/areyouheadless", timeout=10000)
        time.sleep(2)
        text = page.inner_text("body")
        is_bot = "you are" in text.lower() and "headless" in text.lower()
        b.close()
        return f"detected_headless={'yes' if is_bot else 'no'}"


# ── Run All ─────────────────────────────────────────────────

if __name__ == "__main__":
    run_test("1. Fetch HTML (example.com)", test1_nyx, test1_pw)
    run_test("2. Headers Sent", test2_nyx, test2_pw)
    run_test("3. POST JSON", test3_nyx, test3_pw)
    run_test("4. TLS Fingerprint", test4_nyx, test4_pw)
    run_test("5. Anti-Bot (nowsecure.nl)", test5_nyx, test5_pw)
    run_test("6. Google Search (bot detection)", test6_nyx, test6_pw)
    run_test("7. Speed (3 sequential GETs)", test7_nyx, test7_pw)
    run_test("8. Headless Detection", test8_nyx, test8_pw)

    # ── Summary ──────────────────────────────────────────────
    print(f"\n\n{'='*80}")
    print(f"  RESULTS SUMMARY — Nyx (aegis --browser-mode) vs Playwright (headless Chromium)")
    print(f"{'='*80}")
    print(f"{'Test':<40s} {'Nyx':^18} {'Playwright':^18}")
    print(f"{'-'*40} {'-'*18} {'-'*18}")

    nyx_w = pw_w = 0
    for r in results:
        ns = f"{'PASS' if r['nyx_pass'] else 'FAIL'} ({r['nyx_time']}s)"
        ps = f"{'PASS' if r['pw_pass'] else 'FAIL'} ({r['pw_time']}s)"
        print(f"{r['test']:<40s} {ns:^18} {ps:^18}")
        if r['nyx_pass']: nyx_w += 1
        if r['pw_pass']: pw_w += 1

    print(f"{'-'*40} {'-'*18} {'-'*18}")
    print(f"{'TOTAL':<40s} {nyx_w:^18} {pw_w:^18}")

    print(f"\nDetails:")
    for r in results:
        print(f"  {r['test']}:")
        print(f"    Nyx:        {r['nyx_detail'][:100]}")
        print(f"    Playwright: {r['pw_detail'][:100]}")
