#!/usr/bin/env python3
"""
Heavy anti-bot comparison — Nyx vs Playwright headless.

Targets real-world sites with aggressive bot detection:
  - Cloudflare
  - DataDome
  - Akamai
  - PerimeterX / HUMAN
  - TLS fingerprint checkers
  - Rate-limited APIs
  - JS challenge pages
"""

import time
import traceback
import json


results = []

def run_test(name, nyx_fn, pw_fn):
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")

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
        print(f"    PASS ({elapsed}s) — {detail[:80]}")
        return True, elapsed, detail
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        err = str(e)[:120]
        print(f"    FAIL ({elapsed}s) — {err}")
        return False, elapsed, err


def is_blocked(status, text):
    """Detect common block pages."""
    if status in (403, 429, 503):
        return True
    low = text[:2000].lower()
    markers = [
        "captcha", "challenge", "blocked", "access denied",
        "sorry/index", "attention required", "just a moment",
        "checking your browser", "ray id", "cf-browser-verification",
        "datadome", "are you a robot", "bot detected",
        "please verify", "unusual traffic", "automated",
    ]
    return any(m in low for m in markers)


# ═══════════════════════════════════════════════════════════
#  1. Cloudflare — strict JS challenge
# ═══════════════════════════════════════════════════════════

def t1_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://nowsecure.nl")
    blocked = is_blocked(resp.status_code, resp.text)
    return f"status={resp.status_code}, {'BLOCKED' if blocked else 'OK'}"

def t1_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://nowsecure.nl", timeout=15000)
        time.sleep(5)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  2. Cloudflare — Nike (heavy WAF)
# ═══════════════════════════════════════════════════════════

def t2_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.nike.com/")
    blocked = is_blocked(resp.status_code, resp.text)
    return f"status={resp.status_code}, size={len(resp.body)}, {'BLOCKED' if blocked else 'OK'}"

def t2_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.nike.com/", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, size={len(text)}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  3. Akamai Bot Manager — LinkedIn public page
# ═══════════════════════════════════════════════════════════

def t3_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.linkedin.com/robots.txt")
    blocked = is_blocked(resp.status_code, resp.text)
    has_content = "user-agent" in resp.text.lower() or "disallow" in resp.text.lower()
    return f"status={resp.status_code}, has_robots={'yes' if has_content else 'no'}, {'BLOCKED' if blocked else 'OK'}"

def t3_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.linkedin.com/robots.txt", timeout=15000)
        text = page.inner_text("body") if r else ""
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        has_content = "user-agent" in text.lower() or "disallow" in text.lower()
        b.close()
        return f"status={status}, has_robots={'yes' if has_content else 'no'}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  4. Google Search — aggressive rate limit + bot check
# ═══════════════════════════════════════════════════════════

def t4_nyx():
    from nyx import Nyx
    c = Nyx()
    resp = c.get("https://www.google.com/search?q=best+restaurants+near+me")
    blocked = is_blocked(resp.status_code, resp.text) or "sorry" in resp.url.lower()
    return f"status={resp.status_code}, url={resp.url[:60]}, {'BLOCKED' if blocked else 'OK'}"

def t4_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://www.google.com/search?q=best+restaurants+near+me", timeout=10000)
        page.wait_for_load_state("networkidle", timeout=10000)
        url = page.url
        text = page.content()
        blocked = is_blocked(0, text) or "sorry" in url.lower()
        b.close()
        return f"url={url[:60]}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  5. Amazon — sophisticated bot detection
# ═══════════════════════════════════════════════════════════

def t5_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.amazon.com/dp/B0D77BX8Y9")
    blocked = is_blocked(resp.status_code, resp.text)
    has_product = "price" in resp.text.lower() or "add to cart" in resp.text.lower() or "product" in resp.text.lower()
    return f"status={resp.status_code}, product_page={'yes' if has_product else 'no'}, {'BLOCKED' if blocked else 'OK'}"

def t5_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.amazon.com/dp/B0D77BX8Y9", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        has_product = "price" in text.lower() or "add to cart" in text.lower() or "product" in text.lower()
        b.close()
        return f"status={status}, product_page={'yes' if has_product else 'no'}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  6. Ticketmaster — PerimeterX / HUMAN
# ═══════════════════════════════════════════════════════════

def t6_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.ticketmaster.com/")
    blocked = is_blocked(resp.status_code, resp.text)
    return f"status={resp.status_code}, size={len(resp.body)}, {'BLOCKED' if blocked else 'OK'}"

def t6_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.ticketmaster.com/", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, size={len(text)}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  7. Zillow — aggressive Akamai + Incapsula
# ═══════════════════════════════════════════════════════════

def t7_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.zillow.com/homedetails/123-Main-St/1234567_zpid/")
    blocked = is_blocked(resp.status_code, resp.text)
    return f"status={resp.status_code}, size={len(resp.body)}, {'BLOCKED' if blocked else 'OK'}"

def t7_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.zillow.com/homedetails/123-Main-St/1234567_zpid/", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, size={len(text)}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  8. Instagram — Meta's bot detection
# ═══════════════════════════════════════════════════════════

def t8_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.instagram.com/")
    blocked = is_blocked(resp.status_code, resp.text)
    has_content = len(resp.body) > 5000
    return f"status={resp.status_code}, size={len(resp.body)}, {'BLOCKED' if blocked else 'OK'}"

def t8_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.instagram.com/", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, size={len(text)}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  9. Bet365 — DataDome protected
# ═══════════════════════════════════════════════════════════

def t9_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.bet365.com/")
    blocked = is_blocked(resp.status_code, resp.text)
    return f"status={resp.status_code}, size={len(resp.body)}, {'BLOCKED' if blocked else 'OK'}"

def t9_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.bet365.com/", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, size={len(text)}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  10. StockX — Cloudflare + custom bot detection
# ═══════════════════════════════════════════════════════════

def t10_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://stockx.com/")
    blocked = is_blocked(resp.status_code, resp.text)
    return f"status={resp.status_code}, size={len(resp.body)}, {'BLOCKED' if blocked else 'OK'}"

def t10_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://stockx.com/", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, size={len(text)}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  11. Booking.com — PerimeterX
# ═══════════════════════════════════════════════════════════

def t11_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.booking.com/")
    blocked = is_blocked(resp.status_code, resp.text)
    return f"status={resp.status_code}, size={len(resp.body)}, {'BLOCKED' if blocked else 'OK'}"

def t11_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.booking.com/", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, size={len(text)}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  12. Glassdoor — Cloudflare + fingerprinting
# ═══════════════════════════════════════════════════════════

def t12_nyx():
    from nyx import Nyx
    resp = Nyx(timeout=15).get("https://www.glassdoor.com/")
    blocked = is_blocked(resp.status_code, resp.text)
    return f"status={resp.status_code}, size={len(resp.body)}, {'BLOCKED' if blocked else 'OK'}"

def t12_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.glassdoor.com/", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        blocked = is_blocked(status, text)
        b.close()
        return f"status={status}, size={len(text)}, {'BLOCKED' if blocked else 'OK'}"


# ═══════════════════════════════════════════════════════════
#  RUN ALL
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        ("1.  Cloudflare (nowsecure.nl)",          t1_nyx,  t1_pw),
        ("2.  Cloudflare WAF (nike.com)",           t2_nyx,  t2_pw),
        ("3.  Akamai (linkedin.com)",               t3_nyx,  t3_pw),
        ("4.  Google Search",                       t4_nyx,  t4_pw),
        ("5.  Amazon Product Page",                 t5_nyx,  t5_pw),
        ("6.  PerimeterX (ticketmaster.com)",       t6_nyx,  t6_pw),
        ("7.  Incapsula (zillow.com)",              t7_nyx,  t7_pw),
        ("8.  Meta (instagram.com)",                t8_nyx,  t8_pw),
        ("9.  DataDome (bet365.com)",               t9_nyx,  t9_pw),
        ("10. Cloudflare (stockx.com)",             t10_nyx, t10_pw),
        ("11. PerimeterX (booking.com)",            t11_nyx, t11_pw),
        ("12. Cloudflare (glassdoor.com)",          t12_nyx, t12_pw),
    ]

    for name, nfn, pfn in tests:
        run_test(name, nfn, pfn)

    # ── Summary ──────────────────────────────────────────────
    print(f"\n\n{'='*85}")
    print(f"  HEAVY ANTI-BOT RESULTS — Nyx (aegis --browser-mode) vs Playwright (headless)")
    print(f"{'='*85}")
    print(f"{'Test':<42s} {'Nyx':^20} {'Playwright':^20}")
    print(f"{'-'*42} {'-'*20} {'-'*20}")

    nyx_w = pw_w = 0
    for r in results:
        ns = f"{'PASS' if r['nyx_pass'] else 'FAIL'} ({r['nyx_time']}s)"
        ps = f"{'PASS' if r['pw_pass'] else 'FAIL'} ({r['pw_time']}s)"
        print(f"{r['test']:<42s} {ns:^20} {ps:^20}")
        if r['nyx_pass']: nyx_w += 1
        if r['pw_pass']: pw_w += 1

    print(f"{'-'*42} {'-'*20} {'-'*20}")
    print(f"{'TOTAL PASSED':<42s} {nyx_w:^20} {pw_w:^20}")

    # Blocked breakdown
    print(f"\nDetailed results:")
    for r in results:
        nyx_status = "PASS" if r["nyx_pass"] else "FAIL"
        pw_status = "PASS" if r["pw_pass"] else "FAIL"
        winner = ""
        if r["nyx_pass"] and not r["pw_pass"]:
            winner = " << NYX WINS"
        elif r["pw_pass"] and not r["nyx_pass"]:
            winner = " << PW WINS"
        elif r["nyx_pass"] and r["pw_pass"]:
            # Check if one was blocked in detail
            nyx_blocked = "BLOCKED" in r["nyx_detail"]
            pw_blocked = "BLOCKED" in r["pw_detail"]
            if pw_blocked and not nyx_blocked:
                winner = " << NYX WINS (PW blocked)"
            elif nyx_blocked and not pw_blocked:
                winner = " << PW WINS (NYX blocked)"
        print(f"  {r['test']}{winner}")
        print(f"    Nyx:        {r['nyx_detail'][:100]}")
        print(f"    Playwright: {r['pw_detail'][:100]}")
