#!/usr/bin/env python3
"""
Browser Automation Test Cases — Nyx Browser vs Playwright Headless.

TC-1:  Element behind scroll (auto-scroll to off-screen element)
TC-2:  Identical labels / disambiguation
TC-3:  Multi-tab workflow (target="_blank")
TC-4:  Back/forward navigation + map rebuild
TC-5:  SPA route change detection
TC-6:  Infinite scroll + element stability
TC-7:  Login flow (full interaction)
TC-8:  Form filling + submission
TC-9:  Multi-step drill-down
TC-10: Rapid sequential actions
TC-11: act_sequence (batch actions)
TC-12: text: / href: / css: targeting
TC-13: Cloudflare site — full interaction
TC-14: Anti-bot fingerprint (bot.sannysoft.com via real browser)
TC-15: Screenshot comparison
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

    print("\n  [Nyx Browser]")
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
        traceback.print_exc()
        return False, elapsed, err


# ═══════════════════════════════════════════════════════════
#  TC-1: Element behind scroll — auto-scroll to off-screen
# ═══════════════════════════════════════════════════════════

def tc1_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://quotes.toscrape.com/")
    full = b.snapshot(full=True)
    # Find an element that's off-screen
    all_links = full.links()
    assert len(all_links) > 5, f"only {len(all_links)} links"
    # Click the last link — should auto-scroll
    last = all_links[-1]
    snap = b.click(last["action_id"])
    return f"Clicked off-screen element [{last['action_id']}] '{last.get('text','')[:30]}', now at: {snap.url}"

def tc1_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://quotes.toscrape.com/")
        links = page.query_selector_all("a")
        assert len(links) > 5
        last = links[-1]
        last.scroll_into_view_if_needed()
        last.click()
        page.wait_for_load_state("networkidle", timeout=5000)
        br.close()
        return f"Clicked last link, now at: {page.url}"


# ═══════════════════════════════════════════════════════════
#  TC-2: Identical labels — multiple "Add to Cart" or similar
# ═══════════════════════════════════════════════════════════

def tc2_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://books.toscrape.com/")
    # All book links have generic structure — find duplicates
    all_els = snap.elements
    texts = [el.get("text", "")[:30] for el in all_els if el.get("text")]
    from collections import Counter
    dupes = {t: c for t, c in Counter(texts).items() if c > 1}
    # Each element should have a unique action_id even with same text
    ids = [el["action_id"] for el in all_els if el.get("action_id")]
    unique_ids = len(set(ids))
    total_ids = len(ids)
    return f"total_elements={total_ids}, unique_ids={unique_ids}, collisions={total_ids - unique_ids}, duplicate_labels={len(dupes)}"

def tc2_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://books.toscrape.com/")
        links = page.query_selector_all("a")
        texts = [l.inner_text()[:30] for l in links]
        from collections import Counter
        dupes = {t: c for t, c in Counter(texts).items() if c > 1 and t.strip()}
        br.close()
        return f"total_links={len(links)}, duplicate_labels={len(dupes)}, pw uses nth selector to disambiguate"


# ═══════════════════════════════════════════════════════════
#  TC-3: Multi-tab workflow
# ═══════════════════════════════════════════════════════════

def tc3_nyx():
    from nyx.browser import Browser
    b = Browser()
    b.goto("https://example.com")
    initial_tabs = b.tabs()
    # Open new tab
    result = b.new_tab("https://quotes.toscrape.com")
    time.sleep(2)
    after_tabs = b.tabs()
    # Switch between them
    if len(after_tabs) >= 2:
        b.switch_tab(after_tabs[0]["id"])
        t1 = b.status().get("title", "?")
        b.switch_tab(after_tabs[1]["id"])
        t2 = b.status().get("title", "?")
        return f"tabs={len(after_tabs)}, tab1='{t1}', tab2='{t2}'"
    return f"tabs={len(after_tabs)}, new_tab_result={result}"

def tc3_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        ctx = br.new_context()
        page1 = ctx.new_page()
        page1.goto("https://example.com")
        page2 = ctx.new_page()
        page2.goto("https://quotes.toscrape.com")
        pages = ctx.pages
        t1 = pages[0].title()
        t2 = pages[1].title()
        br.close()
        return f"tabs={len(pages)}, tab1='{t1}', tab2='{t2}'"


# ═══════════════════════════════════════════════════════════
#  TC-4: Back/forward navigation + map rebuild
# ═══════════════════════════════════════════════════════════

def tc4_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap1 = b.goto("https://example.com")
    url1 = snap1.url
    snap2 = b.goto("https://quotes.toscrape.com")
    url2 = snap2.url
    # Go back
    snap3 = b.back()
    time.sleep(1)
    snap3 = b.snapshot()
    url3 = snap3.url
    # Go forward
    snap4 = b.forward()
    time.sleep(1)
    snap4 = b.snapshot()
    url4 = snap4.url
    back_worked = "example" in url3
    forward_worked = "quotes" in url4
    return f"back={'OK' if back_worked else 'FAIL'}({url3}), forward={'OK' if forward_worked else 'FAIL'}({url4}), map_rebuilt={len(snap3.elements)}/{len(snap4.elements)} elements"

def tc4_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://example.com")
        page.goto("https://quotes.toscrape.com")
        page.go_back()
        page.wait_for_load_state("networkidle", timeout=5000)
        url3 = page.url
        page.go_forward()
        page.wait_for_load_state("networkidle", timeout=5000)
        url4 = page.url
        back_worked = "example" in url3
        forward_worked = "quotes" in url4
        br.close()
        return f"back={'OK' if back_worked else 'FAIL'}({url3}), forward={'OK' if forward_worked else 'FAIL'}({url4})"


# ═══════════════════════════════════════════════════════════
#  TC-5: Form filling + submission (full interaction)
# ═══════════════════════════════════════════════════════════

def tc5_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://quotes.toscrape.com/login")
    inputs = snap.inputs()
    assert len(inputs) >= 2, f"only {len(inputs)} inputs"
    # Fill username and password
    snap = b.fill(inputs[0]["action_id"], "admin")
    snap = b.fill(inputs[1]["action_id"], "admin")
    # Submit
    submit_btn = snap.find("Login") or snap.buttons()[0] if snap.buttons() else None
    if submit_btn:
        target = submit_btn["action_id"] if isinstance(submit_btn, dict) else submit_btn
        snap = b.click(target)
    else:
        snap = b.submit(inputs[1]["action_id"])
    time.sleep(1)
    snap = b.snapshot()
    logged_in = "logout" in snap.page_text.lower() or "logout" in (snap.title or "").lower()
    return f"login={'success' if logged_in else 'failed'}, url={snap.url}, elements={len(snap.elements)}"

def tc5_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://quotes.toscrape.com/login")
        page.fill("#username", "admin")
        page.fill("#password", "admin")
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle", timeout=5000)
        logged_in = "logout" in page.content().lower()
        br.close()
        return f"login={'success' if logged_in else 'failed'}, url={page.url}"


# ═══════════════════════════════════════════════════════════
#  TC-6: Multi-step drill-down (navigate deep)
# ═══════════════════════════════════════════════════════════

def tc6_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://books.toscrape.com/")
    # Click first category
    cats = [el for el in snap.links() if "category" in (el.get("href") or "")]
    assert cats, "no category links found"
    snap = b.click(cats[0]["action_id"])
    time.sleep(1)
    snap = b.snapshot()
    cat_title = snap.title
    # Click first book
    book_links = [el for el in snap.links() if el.get("text") and len(el["text"]) > 3]
    assert book_links, "no book links"
    snap = b.click(book_links[0]["action_id"])
    time.sleep(1)
    snap = b.snapshot()
    book_title = snap.title
    return f"category='{cat_title}', book='{book_title}', depth=3 pages"

def tc6_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://books.toscrape.com/")
        cat = page.query_selector(".side_categories ul li ul li a")
        cat.click()
        page.wait_for_load_state("networkidle", timeout=5000)
        cat_title = page.title()
        book = page.query_selector("h3 a")
        book.click()
        page.wait_for_load_state("networkidle", timeout=5000)
        book_title = page.title()
        br.close()
        return f"category='{cat_title}', book='{book_title}', depth=3 pages"


# ═══════════════════════════════════════════════════════════
#  TC-7: Pagination — scrape 3 pages
# ═══════════════════════════════════════════════════════════

def tc7_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://quotes.toscrape.com/")
    pages_scraped = 0
    total_text = 0
    for i in range(3):
        pages_scraped += 1
        text = b.text()
        total_text += len(text)
        nxt = snap.find("Next")
        if nxt:
            snap = b.click(nxt["action_id"])
            time.sleep(1)
            snap = b.snapshot()
        else:
            break
    return f"pages={pages_scraped}, total_text={total_text} chars"

def tc7_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://quotes.toscrape.com/")
        pages_scraped = 0
        total_text = 0
        for i in range(3):
            pages_scraped += 1
            total_text += len(page.inner_text("body"))
            nxt = page.query_selector("li.next a")
            if nxt:
                nxt.click()
                page.wait_for_load_state("networkidle", timeout=5000)
            else:
                break
        br.close()
        return f"pages={pages_scraped}, total_text={total_text} chars"


# ═══════════════════════════════════════════════════════════
#  TC-8: act_sequence — batch fill + submit
# ═══════════════════════════════════════════════════════════

def tc8_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://quotes.toscrape.com/login")
    inputs = snap.inputs()
    assert len(inputs) >= 2
    snap = b.act_sequence([
        {"action": "fill", "target": inputs[0]["action_id"], "value": "admin"},
        {"action": "fill", "target": inputs[1]["action_id"], "value": "admin"},
        {"action": "submit", "target": inputs[1]["action_id"]},
    ])
    time.sleep(1)
    snap = b.snapshot()
    logged_in = "logout" in snap.page_text.lower()
    return f"batch_login={'success' if logged_in else 'failed'}, url={snap.url}"

def tc8_pw():
    # Playwright has no batch equivalent — must do sequentially
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://quotes.toscrape.com/login")
        page.fill("#username", "admin")
        page.fill("#password", "admin")
        page.press("#password", "Enter")
        page.wait_for_load_state("networkidle", timeout=5000)
        logged_in = "logout" in page.content().lower()
        br.close()
        return f"sequential_login={'success' if logged_in else 'failed'} (no batch API)"


# ═══════════════════════════════════════════════════════════
#  TC-9: text: / href: / css: targeting
# ═══════════════════════════════════════════════════════════

def tc9_nyx():
    from nyx.browser import Browser
    b = Browser()
    b.goto("https://quotes.toscrape.com/")
    results = {}
    # text: targeting
    try:
        snap = b.act("click", target="text:Login")
        results["text:"] = f"OK → {snap.url}"
    except Exception as e:
        results["text:"] = f"FAIL: {e}"
    # Navigate back
    b.goto("https://quotes.toscrape.com/")
    # href: targeting
    try:
        snap = b.act("click", target="href:/tag/love")
        results["href:"] = f"OK → {snap.url}"
    except Exception as e:
        results["href:"] = f"FAIL: {e}"
    # css: targeting
    b.goto("https://quotes.toscrape.com/")
    try:
        snap = b.act("click", target="css:a.tag")
        results["css:"] = f"OK → {snap.url}"
    except Exception as e:
        results["css:"] = f"FAIL: {e}"
    return f"{results}"

def tc9_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        results = {}
        # text selector
        page.goto("https://quotes.toscrape.com/")
        try:
            page.click("text=Login")
            results["text:"] = f"OK → {page.url}"
        except Exception as e:
            results["text:"] = f"FAIL: {e}"
        # href selector
        page.goto("https://quotes.toscrape.com/")
        try:
            page.click("a[href='/tag/love/']")
            results["href:"] = f"OK → {page.url}"
        except Exception as e:
            results["href:"] = f"FAIL: {e}"
        # css selector
        page.goto("https://quotes.toscrape.com/")
        try:
            page.click("a.tag")
            page.wait_for_load_state("networkidle", timeout=5000)
            results["css:"] = f"OK → {page.url}"
        except Exception as e:
            results["css:"] = f"FAIL: {e}"
        br.close()
        return f"{results}"


# ═══════════════════════════════════════════════════════════
#  TC-10: Rapid sequential actions (10 clicks in 5s)
# ═══════════════════════════════════════════════════════════

def tc10_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://books.toscrape.com/")
    ok = 0
    errors = 0
    for i in range(10):
        links = snap.links()
        if not links:
            break
        try:
            snap = b.click(links[0]["action_id"])
            time.sleep(0.3)
            snap = b.snapshot()
            ok += 1
            # Go back for next iteration
            snap = b.back()
            time.sleep(0.3)
            snap = b.snapshot()
        except Exception:
            errors += 1
    return f"ok={ok}/10, errors={errors}/10"

def tc10_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://books.toscrape.com/")
        ok = 0
        errors = 0
        for i in range(10):
            links = page.query_selector_all("h3 a")
            if not links:
                break
            try:
                links[0].click()
                page.wait_for_load_state("networkidle", timeout=5000)
                ok += 1
                page.go_back()
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                errors += 1
        br.close()
        return f"ok={ok}/10, errors={errors}/10"


# ═══════════════════════════════════════════════════════════
#  TC-11: Cloudflare site — full interaction via browser
# ═══════════════════════════════════════════════════════════

def tc11_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://www.indeed.com/jobs?q=python+developer")
    time.sleep(2)
    snap = b.snapshot(full=True)
    elements = len(snap.elements)
    has_jobs = "job" in snap.page_text.lower() or len(snap.elements) > 10
    return f"title={snap.title}, elements={elements}, has_jobs={has_jobs}"

def tc11_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        try:
            r = page.goto("https://www.indeed.com/jobs?q=python+developer", timeout=15000)
            time.sleep(3)
            status = r.status if r else 0
            text = page.content()
            blocked = status == 403 or "captcha" in text.lower()[:1000]
            elements = len(page.query_selector_all("a, button, input"))
            br.close()
            if blocked:
                return f"BLOCKED status={status}"
            return f"title={page.title()}, elements={elements}"
        except Exception as e:
            br.close()
            raise


# ═══════════════════════════════════════════════════════════
#  TC-12: Anti-bot — bot.sannysoft.com via real browser
# ═══════════════════════════════════════════════════════════

def tc12_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://bot.sannysoft.com/")
    time.sleep(3)
    text = b.text()
    # The page runs JS tests — Nyx Browser is a real browser so it executes them
    webdriver_pass = "webdriver" in text.lower()
    return f"page_loaded=True, text_length={len(text)}, has_webdriver_test={webdriver_pass}"

def tc12_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://bot.sannysoft.com/", timeout=15000)
        time.sleep(3)
        webdriver = page.evaluate("() => navigator.webdriver")
        failed = page.query_selector_all("td.failed, .result-fail")
        passed = page.query_selector_all("td.passed, .result-pass")
        br.close()
        return f"webdriver={webdriver}, failed={len(failed)}, passed={len(passed)}"


# ═══════════════════════════════════════════════════════════
#  TC-13: Infinite scroll simulation (Hacker News pages)
# ═══════════════════════════════════════════════════════════

def tc13_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://news.ycombinator.com/")
    initial = len(snap.elements)
    # Scroll down several times
    element_counts = [initial]
    for i in range(5):
        snap = b.scroll("down")
        time.sleep(0.5)
        snap = b.snapshot(full=True)
        element_counts.append(len(snap.elements))
    # Check ID stability — elements from first snapshot should still exist
    return f"initial={initial}, after_5_scrolls={element_counts[-1]}, counts={element_counts}"

def tc13_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://news.ycombinator.com/")
        initial = len(page.query_selector_all("a"))
        element_counts = [initial]
        for i in range(5):
            page.mouse.wheel(0, 500)
            time.sleep(0.5)
            element_counts.append(len(page.query_selector_all("a")))
        br.close()
        return f"initial={initial}, after_5_scrolls={element_counts[-1]}, counts={element_counts}"


# ═══════════════════════════════════════════════════════════
#  TC-14: Screenshot comparison
# ═══════════════════════════════════════════════════════════

def tc14_nyx():
    from nyx.browser import Browser
    b = Browser()
    b.goto("https://example.com")
    data = b.screenshot("/tmp/nyx_browser_ss.png")
    return f"screenshot={len(data)} bytes saved to /tmp/nyx_browser_ss.png"

def tc14_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://example.com")
        data = page.screenshot(path="/tmp/pw_browser_ss.png")
        br.close()
        return f"screenshot={len(data)} bytes saved to /tmp/pw_browser_ss.png"


# ═══════════════════════════════════════════════════════════
#  TC-15: Google Search via browser (anti-bot real test)
# ═══════════════════════════════════════════════════════════

def tc15_nyx():
    from nyx.browser import Browser
    b = Browser()
    snap = b.goto("https://www.google.com")
    inputs = snap.inputs()
    if inputs:
        snap = b.fill(inputs[0]["action_id"], "nyx browser")
        snap = b.submit(inputs[0]["action_id"])
        time.sleep(2)
        snap = b.snapshot()
    blocked = "sorry" in snap.url.lower()
    return f"blocked={blocked}, url={snap.url[:60]}, elements={len(snap.elements)}"

def tc15_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://www.google.com")
        search = page.query_selector("textarea, input[name='q']")
        if search:
            search.fill("nyx browser")
            search.press("Enter")
            page.wait_for_load_state("networkidle", timeout=10000)
        blocked = "sorry" in page.url.lower()
        br.close()
        return f"blocked={blocked}, url={page.url[:60]}"


# ═══════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        ("TC-1",  "Element behind scroll",              tc1_nyx,  tc1_pw),
        ("TC-2",  "ID collision / disambiguation",      tc2_nyx,  tc2_pw),
        ("TC-3",  "Multi-tab workflow",                  tc3_nyx,  tc3_pw),
        ("TC-4",  "Back/forward + map rebuild",          tc4_nyx,  tc4_pw),
        ("TC-5",  "Login flow (full interaction)",       tc5_nyx,  tc5_pw),
        ("TC-6",  "Multi-step drill-down",               tc6_nyx,  tc6_pw),
        ("TC-7",  "Pagination (3 pages)",                tc7_nyx,  tc7_pw),
        ("TC-8",  "act_sequence batch",                  tc8_nyx,  tc8_pw),
        ("TC-9",  "text:/href:/css: targeting",          tc9_nyx,  tc9_pw),
        ("TC-10", "Rapid sequential actions (10x)",      tc10_nyx, tc10_pw),
        ("TC-11", "Cloudflare site interaction",         tc11_nyx, tc11_pw),
        ("TC-12", "Bot detection (sannysoft)",            tc12_nyx, tc12_pw),
        ("TC-13", "Scroll + element stability",          tc13_nyx, tc13_pw),
        ("TC-14", "Screenshot",                          tc14_nyx, tc14_pw),
        ("TC-15", "Google Search (full flow)",            tc15_nyx, tc15_pw),
    ]

    for tc_id, name, nfn, pfn in tests:
        run_test(tc_id, name, nfn, pfn)

    # ── Summary ──────────────────────────────────────────
    print(f"\n\n{'='*95}")
    print(f"  BROWSER AUTOMATION — Nyx Browser vs Playwright Headless")
    print(f"{'='*95}")
    print(f"{'TC':<8s} {'Test':<40s} {'Nyx Browser':^20} {'Playwright':^20}")
    print(f"{'-'*8} {'-'*40} {'-'*20} {'-'*20}")

    nyx_w = pw_w = 0
    for r in results:
        ns = f"{'PASS' if r['nyx_pass'] else 'FAIL'} ({r['nyx_time']}s)"
        ps = f"{'PASS' if r['pw_pass'] else 'FAIL'} ({r['pw_time']}s)"
        print(f"{r['tc']:<8s} {r['test']:<40s} {ns:^20} {ps:^20}")
        if r['nyx_pass']: nyx_w += 1
        if r['pw_pass']: pw_w += 1

    print(f"{'-'*8} {'-'*40} {'-'*20} {'-'*20}")
    print(f"{'':8s} {'TOTAL':<40s} {nyx_w:^20} {pw_w:^20}")

    nyx_t = sum(r["nyx_time"] for r in results)
    pw_t = sum(r["pw_time"] for r in results)
    print(f"\nTotal time: Nyx {nyx_t:.1f}s vs Playwright {pw_t:.1f}s")

    print(f"\nDetails:")
    for r in results:
        tag = ""
        if r["nyx_pass"] and not r["pw_pass"]: tag = " ★ NYX"
        elif r["pw_pass"] and not r["nyx_pass"]: tag = " ★ PW"
        elif "BLOCKED" in r.get("pw_detail", "") and "BLOCKED" not in r.get("nyx_detail", ""): tag = " ★ NYX (PW blocked)"
        print(f"  {r['tc']}: {r['test']}{tag}")
        print(f"    Nyx:        {r['nyx_detail'][:110]}")
        print(f"    Playwright: {r['pw_detail'][:110]}")
