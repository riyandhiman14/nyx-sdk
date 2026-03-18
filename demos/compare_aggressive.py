#!/usr/bin/env python3
"""
Aggressive real-world scenarios — the stuff developers actually get blocked on.

Tests the hardest scraping targets across industries:
  - E-commerce (Amazon search, eBay, Target)
  - Travel (Airbnb, Expedia, United Airlines)
  - Social (Reddit, Twitter/X, LinkedIn)
  - Finance (Yahoo Finance, Coinbase)
  - Real estate (Redfin, Realtor.com)
  - Jobs (Indeed)
  - News (Medium, Bloomberg)
  - Rapid-fire requests (rate limit stress)
  - Protected APIs
"""

import time
import re
import json
import traceback

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
        print(f"    PASS ({elapsed}s) — {detail[:90]}")
        return True, elapsed, detail
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        err = str(e)[:150]
        print(f"    FAIL ({elapsed}s) — {err}")
        return False, elapsed, err


def blocked(status, text, url=""):
    low = text[:3000].lower()
    if status in (403, 429, 503):
        return True
    markers = [
        "captcha", "challenge", "blocked", "access denied",
        "sorry/index", "attention required", "just a moment",
        "checking your browser", "ray id", "datadome",
        "are you a robot", "bot detected", "please verify",
        "unusual traffic", "automated", "cf-browser-verification",
        "press & hold", "verify you are human", "security check",
        "pardon our interruption",
    ]
    if any(m in low for m in markers):
        return True
    if "sorry" in url.lower():
        return True
    return False


def verdict(status, text, url=""):
    b = blocked(status, text, url)
    return ("BLOCKED", True) if b else ("OK", False)


# ═══════════════════════════════════════════════════════════
#  1. Amazon — search results page
# ═══════════════════════════════════════════════════════════

def t1_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.amazon.com/s?k=wireless+earbuds")
    v, b = verdict(r.status_code, r.text, r.url)
    products = len(re.findall(r'data-asin="[A-Z0-9]{10}"', r.text))
    return f"status={r.status_code}, {v}, products={products}, size={len(r.body)}"

def t1_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.amazon.com/s?k=wireless+earbuds", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        v, bl = verdict(status, text, page.url)
        products = len(page.query_selector_all("[data-asin]"))
        b.close()
        return f"status={status}, {v}, products={products}, size={len(text)}"


# ═══════════════════════════════════════════════════════════
#  2. eBay — search results
# ═══════════════════════════════════════════════════════════

def t2_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.ebay.com/sch/i.html?_nkw=laptop+stand")
    v, b = verdict(r.status_code, r.text, r.url)
    items = len(re.findall(r'class="s-item__title"', r.text))
    return f"status={r.status_code}, {v}, items={items}, size={len(r.body)}"

def t2_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.ebay.com/sch/i.html?_nkw=laptop+stand", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        v, bl = verdict(status, text, page.url)
        items = len(page.query_selector_all(".s-item__title"))
        b.close()
        return f"status={status}, {v}, items={items}, size={len(text)}"


# ═══════════════════════════════════════════════════════════
#  3. Target.com — heavy Akamai
# ═══════════════════════════════════════════════════════════

def t3_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.target.com/c/headphones/-/N-5xtb7")
    v, b = verdict(r.status_code, r.text, r.url)
    return f"status={r.status_code}, {v}, size={len(r.body)}"

def t3_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.target.com/c/headphones/-/N-5xtb7", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            b.close()
            return f"status={status}, {v}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  4. Airbnb — listings page
# ═══════════════════════════════════════════════════════════

def t4_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.airbnb.com/s/San-Francisco/homes")
    v, b = verdict(r.status_code, r.text, r.url)
    return f"status={r.status_code}, {v}, size={len(r.body)}"

def t4_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.airbnb.com/s/San-Francisco/homes", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            b.close()
            return f"status={status}, {v}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  5. United Airlines — Akamai Bot Manager
# ═══════════════════════════════════════════════════════════

def t5_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.united.com/en/us")
    v, b = verdict(r.status_code, r.text, r.url)
    return f"status={r.status_code}, {v}, size={len(r.body)}"

def t5_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.united.com/en/us", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            b.close()
            return f"status={status}, {v}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  6. Reddit — old.reddit (less JS, tests header-level detection)
# ═══════════════════════════════════════════════════════════

def t6_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://old.reddit.com/r/programming/top/?t=week")
    v, b = verdict(r.status_code, r.text, r.url)
    posts = len(re.findall(r'class="thing"', r.text))
    return f"status={r.status_code}, {v}, posts={posts}, size={len(r.body)}"

def t6_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://old.reddit.com/r/programming/top/?t=week", timeout=15000)
        time.sleep(3)
        text = page.content()
        status = r.status if r else 0
        v, bl = verdict(status, text, page.url)
        posts = len(page.query_selector_all(".thing"))
        b.close()
        return f"status={status}, {v}, posts={posts}, size={len(text)}"


# ═══════════════════════════════════════════════════════════
#  7. LinkedIn — public job listing
# ═══════════════════════════════════════════════════════════

def t7_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.linkedin.com/jobs/search/?keywords=python+developer&location=San+Francisco")
    v, b = verdict(r.status_code, r.text, r.url)
    jobs = len(re.findall(r'class="base-card', r.text))
    return f"status={r.status_code}, {v}, jobs={jobs}, size={len(r.body)}"

def t7_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.linkedin.com/jobs/search/?keywords=python+developer&location=San+Francisco", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            jobs = len(page.query_selector_all(".base-card"))
            b.close()
            return f"status={status}, {v}, jobs={jobs}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  8. Yahoo Finance — stock data
# ═══════════════════════════════════════════════════════════

def t8_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://finance.yahoo.com/quote/AAPL/")
    v, b = verdict(r.status_code, r.text, r.url)
    has_price = bool(re.search(r'\$[\d,.]+', r.text))
    return f"status={r.status_code}, {v}, has_price={has_price}, size={len(r.body)}"

def t8_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://finance.yahoo.com/quote/AAPL/", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            has_price = bool(re.search(r'\$[\d,.]+', text))
            b.close()
            return f"status={status}, {v}, has_price={has_price}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  9. Coinbase — prices API (Cloudflare)
# ═══════════════════════════════════════════════════════════

def t9_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.coinbase.com/explore")
    v, b = verdict(r.status_code, r.text, r.url)
    return f"status={r.status_code}, {v}, size={len(r.body)}"

def t9_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.coinbase.com/explore", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            b.close()
            return f"status={status}, {v}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  10. Redfin — real estate (heavy bot detection)
# ═══════════════════════════════════════════════════════════

def t10_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.redfin.com/city/17151/CA/San-Francisco")
    v, b = verdict(r.status_code, r.text, r.url)
    return f"status={r.status_code}, {v}, size={len(r.body)}"

def t10_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.redfin.com/city/17151/CA/San-Francisco", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            b.close()
            return f"status={status}, {v}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  11. Indeed — job search (Cloudflare + custom)
# ═══════════════════════════════════════════════════════════

def t11_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.indeed.com/jobs?q=software+engineer&l=New+York")
    v, b = verdict(r.status_code, r.text, r.url)
    jobs = len(re.findall(r'class="job_seen_beacon"', r.text)) or len(re.findall(r'class="resultContent"', r.text))
    return f"status={r.status_code}, {v}, jobs={jobs}, size={len(r.body)}"

def t11_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.indeed.com/jobs?q=software+engineer&l=New+York", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            b.close()
            return f"status={status}, {v}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  12. Medium — article behind soft-wall
# ═══════════════════════════════════════════════════════════

def t12_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://medium.com/tag/programming/recommended")
    v, b = verdict(r.status_code, r.text, r.url)
    articles = len(re.findall(r'<article', r.text))
    return f"status={r.status_code}, {v}, articles={articles}, size={len(r.body)}"

def t12_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://medium.com/tag/programming/recommended", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            articles = len(page.query_selector_all("article"))
            b.close()
            return f"status={status}, {v}, articles={articles}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  13. Rapid-fire — 10 requests to same domain
# ═══════════════════════════════════════════════════════════

def t13_nyx():
    from nyx import Nyx
    c = Nyx()
    ok = 0
    blocked_count = 0
    for i in range(10):
        r = c.get(f"https://www.google.com/search?q=test+query+{i}")
        if "sorry" in r.url.lower() or r.status_code == 429:
            blocked_count += 1
        else:
            ok += 1
    return f"ok={ok}/10, blocked={blocked_count}/10"

def t13_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        ok = 0
        blocked_count = 0
        for i in range(10):
            try:
                page.goto(f"https://www.google.com/search?q=test+query+{i}", timeout=10000)
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            if "sorry" in page.url.lower():
                blocked_count += 1
            else:
                ok += 1
        b.close()
        return f"ok={ok}/10, blocked={blocked_count}/10"


# ═══════════════════════════════════════════════════════════
#  14. Expedia — travel search (PerimeterX)
# ═══════════════════════════════════════════════════════════

def t14_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.expedia.com/Hotel-Search?destination=New+York")
    v, b = verdict(r.status_code, r.text, r.url)
    return f"status={r.status_code}, {v}, size={len(r.body)}"

def t14_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.expedia.com/Hotel-Search?destination=New+York", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            b.close()
            return f"status={status}, {v}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  15. Realtor.com — listings (Incapsula/Imperva)
# ═══════════════════════════════════════════════════════════

def t15_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://www.realtor.com/realestateandhomes-search/San-Francisco_CA")
    v, b = verdict(r.status_code, r.text, r.url)
    return f"status={r.status_code}, {v}, size={len(r.body)}"

def t15_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            r = page.goto("https://www.realtor.com/realestateandhomes-search/San-Francisco_CA", timeout=15000)
            time.sleep(3)
            text = page.content()
            status = r.status if r else 0
            v, bl = verdict(status, text, page.url)
            b.close()
            return f"status={status}, {v}, size={len(text)}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  RUN ALL
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        ("1.  Amazon Search",               t1_nyx,  t1_pw),
        ("2.  eBay Search",                  t2_nyx,  t2_pw),
        ("3.  Target (Akamai)",              t3_nyx,  t3_pw),
        ("4.  Airbnb Listings",              t4_nyx,  t4_pw),
        ("5.  United Airlines (Akamai BM)",  t5_nyx,  t5_pw),
        ("6.  Reddit (old.reddit)",          t6_nyx,  t6_pw),
        ("7.  LinkedIn Jobs",                t7_nyx,  t7_pw),
        ("8.  Yahoo Finance",                t8_nyx,  t8_pw),
        ("9.  Coinbase (Cloudflare)",        t9_nyx,  t9_pw),
        ("10. Redfin (bot detection)",       t10_nyx, t10_pw),
        ("11. Indeed Jobs (Cloudflare)",      t11_nyx, t11_pw),
        ("12. Medium Articles",              t12_nyx, t12_pw),
        ("13. Rapid-fire Google (10 reqs)",  t13_nyx, t13_pw),
        ("14. Expedia (PerimeterX)",         t14_nyx, t14_pw),
        ("15. Realtor.com (Imperva)",        t15_nyx, t15_pw),
    ]

    for name, nfn, pfn in tests:
        run_test(name, nfn, pfn)

    # ── Summary ──────────────────────────────────────────────
    print(f"\n\n{'='*90}")
    print(f"  AGGRESSIVE TEST RESULTS — Nyx vs Playwright Headless")
    print(f"{'='*90}")
    print(f"{'Test':<45s} {'Nyx':^20} {'Playwright':^20}")
    print(f"{'-'*45} {'-'*20} {'-'*20}")

    nyx_w = pw_w = 0
    nyx_unblocked = pw_unblocked = 0

    for r in results:
        ns = f"{'PASS' if r['nyx_pass'] else 'FAIL'} ({r['nyx_time']}s)"
        ps = f"{'PASS' if r['pw_pass'] else 'FAIL'} ({r['pw_time']}s)"
        print(f"{r['test']:<45s} {ns:^20} {ps:^20}")
        if r['nyx_pass']:
            nyx_w += 1
            if "BLOCKED" not in r["nyx_detail"]:
                nyx_unblocked += 1
        if r['pw_pass']:
            pw_w += 1
            if "BLOCKED" not in r["pw_detail"]:
                pw_unblocked += 1

    print(f"{'-'*45} {'-'*20} {'-'*20}")
    print(f"{'COMPLETED':<45s} {nyx_w:^20} {pw_w:^20}")
    print(f"{'NOT BLOCKED':<45s} {nyx_unblocked:^20} {pw_unblocked:^20}")

    nyx_total = sum(r["nyx_time"] for r in results)
    pw_total = sum(r["pw_time"] for r in results)
    print(f"\nTotal time: Nyx {nyx_total:.1f}s vs Playwright {pw_total:.1f}s")

    print(f"\n{'─'*90}")
    print(f"  DETAILED BREAKDOWN")
    print(f"{'─'*90}")

    for r in results:
        nyx_b = "BLOCKED" in r.get("nyx_detail", "")
        pw_b = "BLOCKED" in r.get("pw_detail", "")
        pw_fail = not r["pw_pass"]

        if (pw_b or pw_fail) and not nyx_b and r["nyx_pass"]:
            tag = "  ** NYX WINS **"
        elif nyx_b and not pw_b and r["pw_pass"]:
            tag = "  ** PW WINS **"
        elif not nyx_b and not pw_b and r["nyx_pass"] and r["pw_pass"]:
            ratio = r["pw_time"] / r["nyx_time"] if r["nyx_time"] > 0 else 0
            if ratio > 2:
                tag = f"  (Nyx {ratio:.0f}x faster)"
            elif ratio < 0.5:
                tag = f"  (PW {1/ratio:.0f}x faster)"
            else:
                tag = ""
        else:
            tag = ""

        print(f"\n  {r['test']}{tag}")
        print(f"    Nyx:        {r['nyx_detail'][:110]}")
        print(f"    Playwright: {r['pw_detail'][:110]}")
