#!/usr/bin/env python3
"""
Claude Web Test Cases — HTTP-testable subset.

TC-18: Cloudflare protected sites
TC-19: navigator.webdriver / bot detection pages
TC-20: Fingerprint consistency
TC-21: Login-gated content (redirect behavior)
TC-22: CAPTCHA appearance under rapid requests
TC-23: Rate limiting by behavior (50 rapid hits)

Plus additional stealth tests derived from the categories.
"""

import time
import re
import json
import traceback

results = []


def run_test(tc_id, name, nyx_fn, pw_fn):
    print(f"\n{'='*75}")
    print(f"  {tc_id}: {name}")
    print(f"{'='*75}")

    print("\n  [Nyx]")
    nyx_ok, nyx_time, nyx_detail = _run(nyx_fn)

    print("\n  [Playwright]")
    pw_ok, pw_time, pw_detail = _run(pw_fn)

    results.append({
        "tc": tc_id, "test": name,
        "nyx_pass": nyx_ok, "nyx_time": nyx_time, "nyx_detail": nyx_detail,
        "pw_pass": pw_ok, "pw_time": pw_time, "pw_detail": pw_detail,
    })


def _run(fn):
    start = time.time()
    try:
        detail = fn()
        elapsed = round(time.time() - start, 2)
        print(f"    PASS ({elapsed}s) — {detail[:100]}")
        return True, elapsed, detail
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        err = str(e)[:150]
        print(f"    FAIL ({elapsed}s) — {err}")
        return False, elapsed, err


# ═══════════════════════════════════════════════════════════
#  TC-18: Cloudflare Protected Sites (battery of 6)
# ═══════════════════════════════════════════════════════════

CF_SITES = [
    ("nowsecure.nl",     "https://nowsecure.nl"),
    ("stockx.com",       "https://stockx.com/"),
    ("indeed.com",       "https://www.indeed.com/jobs?q=engineer"),
    ("coinbase.com",     "https://www.coinbase.com/explore"),
    ("ticketmaster.com", "https://www.ticketmaster.com/"),
    ("glassdoor.com",    "https://www.glassdoor.com/"),
]

def _is_cf_blocked(text):
    low = text[:3000].lower()
    markers = ["just a moment", "checking your browser", "ray id",
               "cf-browser-verification", "challenge-platform",
               "attention required", "enable javascript"]
    return any(m in low for m in markers)

def tc18_nyx():
    from nyx import Nyx
    c = Nyx(timeout=15)
    passed = 0
    blocked = 0
    details = []
    for name, url in CF_SITES:
        try:
            r = c.get(url)
            b = _is_cf_blocked(r.text) or r.status_code in (403, 503)
            if b:
                blocked += 1
                details.append(f"{name}:BLOCKED({r.status_code})")
            else:
                passed += 1
                details.append(f"{name}:OK({r.status_code})")
        except Exception as e:
            blocked += 1
            details.append(f"{name}:ERROR")
    return f"passed={passed}/6, blocked={blocked}/6 — {', '.join(details)}"

def tc18_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        passed = 0
        blocked = 0
        details = []
        for name, url in CF_SITES:
            try:
                r = page.goto(url, timeout=15000)
                time.sleep(3)
                text = page.content()
                status = r.status if r else 0
                bl = _is_cf_blocked(text) or status in (403, 503)
                if bl:
                    blocked += 1
                    details.append(f"{name}:BLOCKED({status})")
                else:
                    passed += 1
                    details.append(f"{name}:OK({status})")
            except Exception as e:
                blocked += 1
                details.append(f"{name}:TIMEOUT")
        b.close()
        return f"passed={passed}/6, blocked={blocked}/6 — {', '.join(details)}"


# ═══════════════════════════════════════════════════════════
#  TC-19a: Bot Detection — bot.sannysoft.com
# ═══════════════════════════════════════════════════════════

def tc19a_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://bot.sannysoft.com/")
    has_page = len(r.body) > 1000
    # Nyx is HTTP only — can't execute JS checks, but can we even load the page?
    has_test_table = "webdriver" in r.text.lower()
    return f"status={r.status_code}, loaded={has_page}, has_tests={has_test_table}, size={len(r.body)}"

def tc19a_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://bot.sannysoft.com/", timeout=15000)
        time.sleep(3)
        # Check specific bot detection results
        checks = {}
        for test_name in ["webdriver", "chrome", "permissions", "plugins", "languages"]:
            try:
                el = page.query_selector(f"#result-{test_name}, td:has-text('{test_name}')")
                if el:
                    row = el.evaluate("el => el.closest('tr')?.innerText || ''")
                    checks[test_name] = "FAIL" if "failed" in row.lower() or "missing" in row.lower() else "PASS"
            except Exception:
                pass
        # Get overall
        failed = page.query_selector_all("td.failed, .result-fail")
        passed_els = page.query_selector_all("td.passed, .result-pass")
        text = page.content()
        webdriver_val = page.evaluate("() => navigator.webdriver")
        b.close()
        return f"webdriver={webdriver_val}, failed={len(failed)}, passed={len(passed_els)}, checks={checks}"


# ═══════════════════════════════════════════════════════════
#  TC-19b: Bot Detection — antoinevastel headless check
# ═══════════════════════════════════════════════════════════

def tc19b_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://arh.antoinevastel.com/bots/areyouheadless")
    has_result = "you are" in r.text.lower()
    is_headless = "headless" in r.text.lower() and "you are" in r.text.lower()
    return f"status={r.status_code}, detected_headless={is_headless}, size={len(r.body)}"

def tc19b_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        try:
            page.goto("https://arh.antoinevastel.com/bots/areyouheadless", timeout=15000)
            time.sleep(3)
            text = page.inner_text("body")
            is_headless = "headless" in text.lower() and "you are" in text.lower()
            b.close()
            return f"detected_headless={is_headless}, text={text[:80]}"
        except Exception as e:
            b.close()
            raise


# ═══════════════════════════════════════════════════════════
#  TC-20a: Fingerprint — TLS fingerprint via tls.peet.ws
# ═══════════════════════════════════════════════════════════

def tc20a_nyx():
    from nyx import Nyx
    r = Nyx(timeout=15).get("https://tls.peet.ws/api/all")
    data = r.json()
    tls = data.get("tls", {})
    h2 = data.get("http2", {})
    return (f"ja3={tls.get('ja3_hash','?')[:16]}, "
            f"ja4={tls.get('ja4','?')[:20]}, "
            f"h2_fp={h2.get('fingerprint','?')[:20]}, "
            f"akamai_hash={h2.get('akamai_fingerprint_hash','?')[:16]}")

def tc20a_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://tls.peet.ws/api/all", timeout=15000)
        text = page.inner_text("body")
        data = json.loads(text)
        tls = data.get("tls", {})
        h2 = data.get("http2", {})
        b.close()
        return (f"ja3={tls.get('ja3_hash','?')[:16]}, "
                f"ja4={tls.get('ja4','?')[:20]}, "
                f"h2_fp={h2.get('fingerprint','?')[:20]}, "
                f"akamai_hash={h2.get('akamai_fingerprint_hash','?')[:16]}")


# ═══════════════════════════════════════════════════════════
#  TC-20b: Fingerprint consistency — 3 requests, same print?
# ═══════════════════════════════════════════════════════════

def tc20b_nyx():
    from nyx import Nyx
    c = Nyx(timeout=15)
    ja3s = []
    for i in range(3):
        r = c.get("https://tls.peet.ws/api/all")
        data = r.json()
        ja3s.append(data.get("tls", {}).get("ja3_hash", "?"))
    consistent = len(set(ja3s)) == 1
    return f"consistent={consistent}, ja3s={ja3s}"

def tc20b_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ja3s = []
        for i in range(3):
            page = b.new_page()
            page.goto("https://tls.peet.ws/api/all", timeout=15000)
            text = page.inner_text("body")
            data = json.loads(text)
            ja3s.append(data.get("tls", {}).get("ja3_hash", "?"))
            page.close()
        b.close()
        consistent = len(set(ja3s)) == 1
        return f"consistent={consistent}, ja3s={ja3s}"


# ═══════════════════════════════════════════════════════════
#  TC-20c: Fingerprint — header ordering & count
# ═══════════════════════════════════════════════════════════

def tc20c_nyx():
    from nyx import Nyx
    r = Nyx().get("https://httpbin.org/headers")
    h = r.json()["headers"]
    browser_markers = ["Sec-Ch-Ua", "Sec-Fetch-Dest", "Sec-Fetch-Mode",
                       "Sec-Fetch-Site", "Accept-Language", "Priority",
                       "Upgrade-Insecure-Requests"]
    present = [m for m in browser_markers if m in h]
    return f"headers={len(h)}, browser_markers={len(present)}/{len(browser_markers)}, present={present}"

def tc20c_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://httpbin.org/headers")
        text = page.inner_text("body")
        h = json.loads(text)["headers"]
        browser_markers = ["Sec-Ch-Ua", "Sec-Fetch-Dest", "Sec-Fetch-Mode",
                           "Sec-Fetch-Site", "Accept-Language", "Priority",
                           "Upgrade-Insecure-Requests"]
        present = [m for m in browser_markers if m in h]
        b.close()
        return f"headers={len(h)}, browser_markers={len(present)}/{len(browser_markers)}, present={present}"


# ═══════════════════════════════════════════════════════════
#  TC-21: Login-gated content (redirect to login vs content)
# ═══════════════════════════════════════════════════════════

def tc21_nyx():
    from nyx import Nyx
    c = Nyx(timeout=15)
    urls = {
        "github_settings": "https://github.com/settings/profile",
        "gmail":           "https://mail.google.com/mail/u/0/",
        "linkedin_feed":   "https://www.linkedin.com/feed/",
    }
    results = {}
    for name, url in urls.items():
        try:
            r = c.get(url)
            redirected_to_login = ("login" in r.text.lower()[:2000] or
                                   "signin" in r.text.lower()[:2000] or
                                   "sign in" in r.text.lower()[:2000] or
                                   r.status_code in (401, 403))
            results[name] = f"{'login_redirect' if redirected_to_login else 'content'}({r.status_code})"
        except Exception as e:
            results[name] = f"error"
    return f"{results}"

def tc21_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        urls = {
            "github_settings": "https://github.com/settings/profile",
            "gmail":           "https://mail.google.com/mail/u/0/",
            "linkedin_feed":   "https://www.linkedin.com/feed/",
        }
        results = {}
        for name, url in urls.items():
            try:
                r = page.goto(url, timeout=15000)
                time.sleep(2)
                text = page.content().lower()[:2000]
                status = r.status if r else 0
                redirected_to_login = ("login" in text or "signin" in text or
                                       "sign in" in text or status in (401, 403))
                results[name] = f"{'login_redirect' if redirected_to_login else 'content'}({status})"
            except Exception as e:
                results[name] = f"error"
        b.close()
        return f"{results}"


# ═══════════════════════════════════════════════════════════
#  TC-22: CAPTCHA trigger — rapid requests to rate-limited site
# ═══════════════════════════════════════════════════════════

def tc22_nyx():
    from nyx import Nyx
    c = Nyx(timeout=10)
    captcha_count = 0
    ok_count = 0
    for i in range(15):
        try:
            r = c.get(f"https://www.google.com/search?q=captcha+test+{i}+{time.time()}")
            if "sorry" in r.url.lower() or "captcha" in r.text.lower()[:1000]:
                captcha_count += 1
            else:
                ok_count += 1
        except Exception:
            captcha_count += 1
    return f"ok={ok_count}/15, captcha={captcha_count}/15"

def tc22_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        captcha_count = 0
        ok_count = 0
        for i in range(15):
            try:
                page.goto(f"https://www.google.com/search?q=captcha+test+{i}+{time.time()}", timeout=10000)
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            url = page.url
            text = page.content()[:1000].lower()
            if "sorry" in url.lower() or "captcha" in text:
                captcha_count += 1
            else:
                ok_count += 1
        b.close()
        return f"ok={ok_count}/15, captcha={captcha_count}/15"


# ═══════════════════════════════════════════════════════════
#  TC-23a: Rate limiting — 20 rapid hits to Amazon
# ═══════════════════════════════════════════════════════════

def tc23a_nyx():
    from nyx import Nyx
    c = Nyx(timeout=10)
    ok = blocked = errors = 0
    for i in range(20):
        try:
            r = c.get(f"https://www.amazon.com/s?k=test+{i}")
            if r.status_code == 503 or "captcha" in r.text.lower()[:500] or "robot" in r.text.lower()[:500]:
                blocked += 1
            else:
                ok += 1
        except Exception:
            errors += 1
    return f"ok={ok}/20, blocked={blocked}/20, errors={errors}/20"

def tc23a_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        ok = blocked = errors = 0
        for i in range(20):
            try:
                r = page.goto(f"https://www.amazon.com/s?k=test+{i}", timeout=10000)
                time.sleep(0.5)
                text = page.content()[:500].lower()
                status = r.status if r else 0
                if status == 503 or "captcha" in text or "robot" in text:
                    blocked += 1
                else:
                    ok += 1
            except Exception:
                errors += 1
        b.close()
        return f"ok={ok}/20, blocked={blocked}/20, errors={errors}/20"


# ═══════════════════════════════════════════════════════════
#  TC-23b: Rate limiting — 20 rapid hits to Google
# ═══════════════════════════════════════════════════════════

def tc23b_nyx():
    from nyx import Nyx
    c = Nyx(timeout=10)
    ok = blocked = 0
    for i in range(20):
        try:
            r = c.get(f"https://www.google.com/search?q=rate+limit+{i}")
            if "sorry" in r.url.lower() or r.status_code == 429:
                blocked += 1
            else:
                ok += 1
        except Exception:
            blocked += 1
    return f"ok={ok}/20, blocked={blocked}/20"

def tc23b_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        ok = blocked = 0
        for i in range(20):
            try:
                page.goto(f"https://www.google.com/search?q=rate+limit+{i}", timeout=10000)
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            if "sorry" in page.url.lower():
                blocked += 1
            else:
                ok += 1
        b.close()
        return f"ok={ok}/20, blocked={blocked}/20"


# ═══════════════════════════════════════════════════════════
#  TC-EXTRA-1: PerimeterX sites (Zillow, Expedia, Ticketmaster)
# ═══════════════════════════════════════════════════════════

PX_SITES = [
    ("zillow",       "https://www.zillow.com/san-francisco-ca/"),
    ("expedia",      "https://www.expedia.com/Hotels"),
    ("ticketmaster", "https://www.ticketmaster.com/"),
]

def tc_px_nyx():
    from nyx import Nyx
    c = Nyx(timeout=15)
    details = []
    ok = 0
    for name, url in PX_SITES:
        try:
            r = c.get(url)
            b = r.status_code in (403, 429, 503) or "blocked" in r.text[:500].lower() or "captcha" in r.text[:500].lower()
            if b:
                details.append(f"{name}:BLOCKED({r.status_code})")
            else:
                ok += 1
                details.append(f"{name}:OK({r.status_code},{len(r.body)}b)")
        except Exception as e:
            details.append(f"{name}:ERROR")
    return f"passed={ok}/3 — {', '.join(details)}"

def tc_px_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        details = []
        ok = 0
        for name, url in PX_SITES:
            try:
                r = page.goto(url, timeout=15000)
                time.sleep(3)
                text = page.content()
                status = r.status if r else 0
                bl = status in (403, 429, 503) or "blocked" in text[:500].lower() or "captcha" in text[:500].lower()
                if bl:
                    details.append(f"{name}:BLOCKED({status})")
                else:
                    ok += 1
                    details.append(f"{name}:OK({status},{len(text)}b)")
            except Exception as e:
                details.append(f"{name}:TIMEOUT")
        b.close()
        return f"passed={ok}/3 — {', '.join(details)}"


# ═══════════════════════════════════════════════════════════
#  TC-EXTRA-2: Akamai Bot Manager sites
# ═══════════════════════════════════════════════════════════

AKAMAI_SITES = [
    ("united",  "https://www.united.com/en/us"),
    ("nike",    "https://www.nike.com/"),
    ("target",  "https://www.target.com/"),
]

def tc_akamai_nyx():
    from nyx import Nyx
    c = Nyx(timeout=15)
    details = []
    ok = 0
    for name, url in AKAMAI_SITES:
        try:
            r = c.get(url)
            b = r.status_code in (403, 429, 503)
            if b:
                details.append(f"{name}:BLOCKED({r.status_code})")
            else:
                ok += 1
                details.append(f"{name}:OK({r.status_code},{len(r.body)}b)")
        except Exception as e:
            details.append(f"{name}:ERROR")
    return f"passed={ok}/3 — {', '.join(details)}"

def tc_akamai_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        details = []
        ok = 0
        for name, url in AKAMAI_SITES:
            try:
                r = page.goto(url, timeout=15000)
                time.sleep(3)
                text = page.content()
                status = r.status if r else 0
                bl = status in (403, 429, 503)
                if bl:
                    details.append(f"{name}:BLOCKED({status})")
                else:
                    ok += 1
                    details.append(f"{name}:OK({status},{len(text)}b)")
            except Exception as e:
                details.append(f"{name}:TIMEOUT/ERROR")
        b.close()
        return f"passed={ok}/3 — {', '.join(details)}"


# ═══════════════════════════════════════════════════════════
#  TC-EXTRA-3: DataDome sites
# ═══════════════════════════════════════════════════════════

DD_SITES = [
    ("bet365",     "https://www.bet365.com/"),
    ("soundcloud", "https://soundcloud.com/discover"),
    ("reddit_new", "https://www.reddit.com/r/programming/"),
]

def tc_dd_nyx():
    from nyx import Nyx
    c = Nyx(timeout=15)
    details = []
    ok = 0
    for name, url in DD_SITES:
        try:
            r = c.get(url)
            b = (r.status_code in (403, 429, 503) or
                 "datadome" in r.text[:2000].lower() or
                 "captcha" in r.text[:2000].lower() or
                 "blocked" in r.text[:500].lower())
            if b:
                details.append(f"{name}:BLOCKED({r.status_code})")
            else:
                ok += 1
                details.append(f"{name}:OK({r.status_code},{len(r.body)}b)")
        except Exception as e:
            details.append(f"{name}:ERROR")
    return f"passed={ok}/3 — {', '.join(details)}"

def tc_dd_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        details = []
        ok = 0
        for name, url in DD_SITES:
            try:
                r = page.goto(url, timeout=15000)
                time.sleep(3)
                text = page.content()
                status = r.status if r else 0
                bl = (status in (403, 429, 503) or
                      "datadome" in text[:2000].lower() or
                      "captcha" in text[:2000].lower() or
                      "blocked" in text[:500].lower())
                if bl:
                    details.append(f"{name}:BLOCKED({status})")
                else:
                    ok += 1
                    details.append(f"{name}:OK({status},{len(text)}b)")
            except Exception as e:
                details.append(f"{name}:TIMEOUT/ERROR")
        b.close()
        return f"passed={ok}/3 — {', '.join(details)}"


# ═══════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        ("TC-18",  "Cloudflare (6 sites)",              tc18_nyx,  tc18_pw),
        ("TC-19a", "Bot detection (sannysoft)",          tc19a_nyx, tc19a_pw),
        ("TC-19b", "Headless detection (antoinevastel)", tc19b_nyx, tc19b_pw),
        ("TC-20a", "TLS fingerprint",                    tc20a_nyx, tc20a_pw),
        ("TC-20b", "Fingerprint consistency (3 reqs)",   tc20b_nyx, tc20b_pw),
        ("TC-20c", "Browser header markers",             tc20c_nyx, tc20c_pw),
        ("TC-21",  "Login-gated redirect behavior",      tc21_nyx,  tc21_pw),
        ("TC-22",  "CAPTCHA trigger (15 rapid Google)",  tc22_nyx,  tc22_pw),
        ("TC-23a", "Rate limit: 20x Amazon",             tc23a_nyx, tc23a_pw),
        ("TC-23b", "Rate limit: 20x Google",             tc23b_nyx, tc23b_pw),
        ("TC-PX",  "PerimeterX (Zillow/Expedia/TM)",    tc_px_nyx, tc_px_pw),
        ("TC-AK",  "Akamai BM (United/Nike/Target)",    tc_akamai_nyx, tc_akamai_pw),
        ("TC-DD",  "DataDome (Bet365/SC/Reddit)",        tc_dd_nyx, tc_dd_pw),
    ]

    for tc_id, name, nfn, pfn in tests:
        run_test(tc_id, name, nfn, pfn)

    # ── Summary ──────────────────────────────────────────
    print(f"\n\n{'='*95}")
    print(f"  TEST CASE RESULTS — Nyx (aegis --browser-mode) vs Playwright (headless Chromium)")
    print(f"{'='*95}")
    print(f"{'TC':<8s} {'Test':<42s} {'Nyx':^20} {'Playwright':^20}")
    print(f"{'-'*8} {'-'*42} {'-'*20} {'-'*20}")

    nyx_w = pw_w = 0
    for r in results:
        ns = f"{'PASS' if r['nyx_pass'] else 'FAIL'} ({r['nyx_time']}s)"
        ps = f"{'PASS' if r['pw_pass'] else 'FAIL'} ({r['pw_time']}s)"
        print(f"{r['tc']:<8s} {r['test']:<42s} {ns:^20} {ps:^20}")
        if r['nyx_pass']: nyx_w += 1
        if r['pw_pass']: pw_w += 1

    print(f"{'-'*8} {'-'*42} {'-'*20} {'-'*20}")
    print(f"{'':8s} {'TOTAL':<42s} {nyx_w:^20} {pw_w:^20}")

    nyx_t = sum(r["nyx_time"] for r in results)
    pw_t = sum(r["pw_time"] for r in results)
    print(f"\nTotal execution time: Nyx {nyx_t:.1f}s vs Playwright {pw_t:.1f}s")

    # ── Winner breakdown ─────────────────────────────────
    print(f"\n{'─'*95}")
    print(f"  DETAILED ANALYSIS")
    print(f"{'─'*95}")

    for r in results:
        nyx_d = r["nyx_detail"]
        pw_d = r["pw_detail"]

        # Determine winner
        tag = ""
        if r["nyx_pass"] and not r["pw_pass"]:
            tag = " ★ NYX WINS (PW failed)"
        elif r["pw_pass"] and not r["nyx_pass"]:
            tag = " ★ PW WINS (Nyx failed)"
        else:
            # Both passed — compare blocked counts or content
            nyx_blocked_count = nyx_d.count("BLOCKED")
            pw_blocked_count = pw_d.count("BLOCKED")
            if pw_blocked_count > nyx_blocked_count:
                tag = f" ★ NYX WINS ({pw_blocked_count} vs {nyx_blocked_count} blocked)"
            elif nyx_blocked_count > pw_blocked_count:
                tag = f" ★ PW WINS ({nyx_blocked_count} vs {pw_blocked_count} blocked)"

            # Rate limit tests
            nyx_ok_match = re.search(r'ok=(\d+)', nyx_d)
            pw_ok_match = re.search(r'ok=(\d+)', pw_d)
            if nyx_ok_match and pw_ok_match:
                nyx_ok = int(nyx_ok_match.group(1))
                pw_ok = int(pw_ok_match.group(1))
                if nyx_ok > pw_ok:
                    tag = f" ★ NYX WINS ({nyx_ok} vs {pw_ok} OK)"
                elif pw_ok > nyx_ok:
                    tag = f" ★ PW WINS ({pw_ok} vs {nyx_ok} OK)"

        print(f"\n  {r['tc']}: {r['test']}{tag}")
        print(f"    Nyx:        {nyx_d[:120]}")
        print(f"    Playwright: {pw_d[:120]}")
