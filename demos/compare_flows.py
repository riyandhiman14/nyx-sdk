#!/usr/bin/env python3
"""
Automation Flows — Nyx vs Playwright (headless).

Real-world scenarios developers actually build with Playwright:
  1. Search + scrape results
  2. Login flow
  3. Multi-page scraping with pagination
  4. Form submission
  5. API behind a website (fetch JSON)
  6. Price monitoring (product page scrape)
  7. Multi-step navigation (drill into nested pages)
  8. File download
  9. Scrape behind Cloudflare
  10. Extract structured data from a listing
"""

import time
import traceback
import json
from html.parser import HTMLParser


results = []


def run_test(name, nyx_fn, pw_fn):
    print(f"\n{'='*70}")
    print(f"  FLOW: {name}")
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
        err = str(e)[:120]
        print(f"    FAIL ({elapsed}s) — {err}")
        return False, elapsed, err


# ── HTML parsing helpers ─────────────────────────────────────

class TagExtractor(HTMLParser):
    """Extract text from specific tags."""
    def __init__(self, target_tags=None, target_class=None):
        super().__init__()
        self.results = []
        self.target_tags = target_tags or []
        self.target_class = target_class
        self._capture = False
        self._text = ""
        self._attrs = {}

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag in self.target_tags:
            if self.target_class:
                cls = attrs_d.get("class", "")
                if self.target_class in cls:
                    self._capture = True
                    self._text = ""
                    self._attrs = attrs_d
            else:
                self._capture = True
                self._text = ""
                self._attrs = attrs_d

    def handle_data(self, data):
        if self._capture:
            self._text += data

    def handle_endtag(self, tag):
        if self._capture and tag in self.target_tags:
            self._capture = False
            if self._text.strip():
                self.results.append({
                    "text": self._text.strip(),
                    "href": self._attrs.get("href", ""),
                })


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._in_a = False
        self._href = ""
        self._text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_a = True
            self._text = ""
            for n, v in attrs:
                if n == "href":
                    self._href = v or ""

    def handle_data(self, data):
        if self._in_a:
            self._text += data

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            self._in_a = False
            if self._href and self._text.strip():
                self.links.append((self._text.strip(), self._href))


class FormExtractor(HTMLParser):
    """Extract input fields from a page."""
    def __init__(self):
        super().__init__()
        self.inputs = []
        self.form_action = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "form":
            self.form_action = d.get("action", "")
        if tag in ("input", "textarea", "select"):
            self.inputs.append({
                "tag": tag,
                "name": d.get("name", ""),
                "type": d.get("type", "text"),
                "value": d.get("value", ""),
            })


# ═══════════════════════════════════════════════════════════
#  FLOW 1: Search Google + scrape results
# ═══════════════════════════════════════════════════════════

def flow1_nyx():
    from nyx import Nyx
    c = Nyx()
    resp = c.get("https://www.google.com/search?q=python+web+scraping+tutorial")
    if "sorry" in resp.url.lower():
        return "BLOCKED by Google"
    parser = LinkExtractor()
    parser.feed(resp.text)
    real_links = [(t, h) for t, h in parser.links
                  if h.startswith("http") and "google" not in h]
    titles = [t[:50] for t, _ in real_links[:5]]
    return f"Found {len(real_links)} result links: {titles}"

def flow1_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://www.google.com/search?q=python+web+scraping+tutorial", timeout=10000)
        page.wait_for_load_state("networkidle", timeout=10000)
        if "sorry" in page.url.lower():
            b.close()
            return "BLOCKED by Google"
        results = page.query_selector_all("h3")
        titles = [r.inner_text()[:50] for r in results[:5]]
        b.close()
        return f"Found {len(results)} result titles: {titles}"


# ═══════════════════════════════════════════════════════════
#  FLOW 2: Login flow (quotes.toscrape.com)
# ═══════════════════════════════════════════════════════════

def flow2_nyx():
    from nyx import Nyx
    import re
    c = Nyx()
    # Get login page + extract CSRF token
    resp = c.get("https://quotes.toscrape.com/login")
    token_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resp.text)
    token = token_match.group(1) if token_match else ""
    # POST login
    resp = c.post("https://quotes.toscrape.com/login",
                  data=f"csrf_token={token}&username=admin&password=admin",
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    logged_in = "logout" in resp.text.lower()
    return f"login={'success' if logged_in else 'failed'}, has_logout={logged_in}"

def flow2_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://quotes.toscrape.com/login")
        page.fill("#username", "admin")
        page.fill("#password", "admin")
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle", timeout=5000)
        logged_in = "logout" in page.content().lower()
        b.close()
        return f"login={'success' if logged_in else 'failed'}, has_logout={logged_in}"


# ═══════════════════════════════════════════════════════════
#  FLOW 3: Multi-page scraping with pagination
# ═══════════════════════════════════════════════════════════

def flow3_nyx():
    from nyx import Nyx
    import re
    c = Nyx()
    all_quotes = []
    url = "https://quotes.toscrape.com/"
    for page_num in range(1, 4):
        resp = c.get(url)
        # Extract quotes (between <span class="text"> tags)
        quotes = re.findall(r'class="text"[^>]*>(.*?)</span>', resp.text)
        all_quotes.extend(quotes)
        # Find next page link
        next_match = re.search(r'<li class="next"><a href="([^"]+)"', resp.text)
        if next_match:
            url = "https://quotes.toscrape.com" + next_match.group(1)
        else:
            break
    return f"Scraped {len(all_quotes)} quotes across {page_num} pages"

def flow3_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://quotes.toscrape.com/")
        all_quotes = []
        for page_num in range(1, 4):
            quotes = page.query_selector_all(".quote .text")
            all_quotes.extend([q.inner_text() for q in quotes])
            nxt = page.query_selector("li.next a")
            if nxt:
                nxt.click()
                page.wait_for_load_state("networkidle", timeout=5000)
            else:
                break
        b.close()
        return f"Scraped {len(all_quotes)} quotes across {page_num} pages"


# ═══════════════════════════════════════════════════════════
#  FLOW 4: Form submission (httpbin)
# ═══════════════════════════════════════════════════════════

def flow4_nyx():
    from nyx import Nyx
    c = Nyx()
    resp = c.post("https://httpbin.org/post",
                  data="custname=John+Doe&custtel=555-1234&custemail=john@example.com&size=large&topping=bacon&delivery=12:00&comments=Extra+cheese",
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    data = resp.json()
    form = data.get("form", {})
    return f"Submitted: name={form.get('custname')}, tel={form.get('custtel')}, size={form.get('size')}"

def flow4_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://httpbin.org/forms/post")
        page.fill("input[name='custname']", "John Doe")
        page.fill("input[name='custtel']", "555-1234")
        page.fill("input[name='custemail']", "john@example.com")
        page.check("input[value='large']")
        page.check("input[value='bacon']")
        page.fill("input[name='delivery']", "12:00")
        page.fill("textarea[name='comments']", "Extra cheese")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle", timeout=5000)
        text = page.inner_text("body")
        b.close()
        has_data = "John Doe" in text
        return f"Submitted: response_has_name={has_data}, body_size={len(text)}"


# ═══════════════════════════════════════════════════════════
#  FLOW 5: Fetch JSON API behind a website
# ═══════════════════════════════════════════════════════════

def flow5_nyx():
    from nyx import Nyx
    c = Nyx()
    resp = c.get("https://api.github.com/repos/anthropics/claude-code",
                 headers={"Accept": "application/vnd.github.v3+json"})
    data = resp.json()
    return f"Repo: {data.get('full_name')}, stars={data.get('stargazers_count')}, lang={data.get('language')}"

def flow5_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        resp = page.goto("https://api.github.com/repos/anthropics/claude-code")
        text = page.inner_text("body")
        data = json.loads(text)
        b.close()
        return f"Repo: {data.get('full_name')}, stars={data.get('stargazers_count')}, lang={data.get('language')}"


# ═══════════════════════════════════════════════════════════
#  FLOW 6: Price monitoring (scrape a product page)
# ═══════════════════════════════════════════════════════════

def flow6_nyx():
    from nyx import Nyx
    import re
    c = Nyx()
    resp = c.get("https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")
    price = re.search(r'class="price_color"[^>]*>([^<]+)', resp.text)
    title = re.search(r'<h1>([^<]+)', resp.text)
    stock = re.search(r'class="instock[^"]*"[^>]*>\s*<[^>]*>\s*([^<]+)', resp.text)
    return f"title={title.group(1) if title else '?'}, price={price.group(1) if price else '?'}, stock={stock.group(1).strip() if stock else '?'}"

def flow6_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")
        title = page.inner_text("h1")
        price = page.inner_text(".price_color")
        stock = page.inner_text(".instock.availability")
        b.close()
        return f"title={title}, price={price}, stock={stock.strip()}"


# ═══════════════════════════════════════════════════════════
#  FLOW 7: Multi-step drill-down (category → product)
# ═══════════════════════════════════════════════════════════

def flow7_nyx():
    from nyx import Nyx
    import re
    c = Nyx()
    # Step 1: Get categories
    resp = c.get("https://books.toscrape.com/")
    cats = re.findall(r'<a href="(catalogue/category/books/[^"]+)"[^>]*>\s*([^<]+)', resp.text)
    assert cats, "no categories found"
    # Step 2: Pick first category
    cat_url = "https://books.toscrape.com/" + cats[0][0].strip()
    cat_name = cats[0][1].strip()
    resp = c.get(cat_url)
    # Step 3: Get first book
    books = re.findall(r'<h3><a href="([^"]+)" title="([^"]+)"', resp.text)
    assert books, "no books in category"
    book_url = cat_url.rsplit("/", 1)[0] + "/" + books[0][0]
    # Step 4: Get book details
    resp = c.get(book_url)
    price = re.search(r'class="price_color"[^>]*>([^<]+)', resp.text)
    return f"category={cat_name}, book={books[0][1][:40]}, price={price.group(1) if price else '?'}"

def flow7_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        # Step 1: Home page
        page.goto("https://books.toscrape.com/")
        # Step 2: Click first category
        cat_link = page.query_selector(".side_categories ul li ul li a")
        cat_name = cat_link.inner_text().strip()
        cat_link.click()
        page.wait_for_load_state("networkidle", timeout=5000)
        # Step 3: Click first book
        book_link = page.query_selector("h3 a")
        book_title = book_link.get_attribute("title")
        book_link.click()
        page.wait_for_load_state("networkidle", timeout=5000)
        # Step 4: Read details
        price = page.inner_text(".price_color")
        b.close()
        return f"category={cat_name}, book={book_title[:40]}, price={price}"


# ═══════════════════════════════════════════════════════════
#  FLOW 8: Download a file
# ═══════════════════════════════════════════════════════════

def flow8_nyx():
    from nyx import Nyx
    c = Nyx()
    resp = c.get("https://httpbin.org/image/png")
    assert len(resp.body) > 1000, f"too small: {len(resp.body)}"
    with open("/tmp/nyx_download.png", "wb") as f:
        f.write(resp.body)
    return f"Downloaded {len(resp.body)} bytes to /tmp/nyx_download.png"

def flow8_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        resp = page.goto("https://httpbin.org/image/png")
        body = resp.body()
        assert len(body) > 1000, f"too small: {len(body)}"
        with open("/tmp/pw_download.png", "wb") as f:
            f.write(body)
        b.close()
        return f"Downloaded {len(body)} bytes to /tmp/pw_download.png"


# ═══════════════════════════════════════════════════════════
#  FLOW 9: Scrape behind Cloudflare (real site)
# ═══════════════════════════════════════════════════════════

def flow9_nyx():
    from nyx import Nyx
    import re
    c = Nyx(timeout=15)
    resp = c.get("https://www.zillow.com/san-francisco-ca/")
    if resp.status_code == 403:
        return f"BLOCKED status=403, size={len(resp.body)}"
    # Try to extract some listing data
    titles = re.findall(r'<address[^>]*>([^<]+)</address>', resp.text)
    prices = re.findall(r'\$[\d,]+', resp.text)
    return f"status={resp.status_code}, addresses={len(titles)}, prices={len(prices)}, size={len(resp.body)}"

def flow9_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        r = page.goto("https://www.zillow.com/san-francisco-ca/", timeout=15000)
        time.sleep(3)
        status = r.status if r else 0
        text = page.content()
        if status == 403 or "captcha" in text.lower() or "access denied" in text.lower():
            b.close()
            return f"BLOCKED status={status}, size={len(text)}"
        addresses = page.query_selector_all("address")
        prices = page.query_selector_all("[data-test='property-card-price']")
        b.close()
        return f"status={status}, addresses={len(addresses)}, prices={len(prices)}, size={len(text)}"


# ═══════════════════════════════════════════════════════════
#  FLOW 10: Structured data extraction from listing
# ═══════════════════════════════════════════════════════════

def flow10_nyx():
    from nyx import Nyx
    import re
    c = Nyx()
    resp = c.get("https://books.toscrape.com/catalogue/page-1.html")
    # Extract all books: title, price, rating, availability
    books = []
    titles = re.findall(r'<h3><a[^>]*title="([^"]+)"', resp.text)
    prices = re.findall(r'class="price_color">([^<]+)', resp.text)
    ratings = re.findall(r'class="star-rating (\w+)"', resp.text)
    for i in range(min(len(titles), len(prices))):
        books.append({
            "title": titles[i],
            "price": prices[i],
            "rating": ratings[i] if i < len(ratings) else "?",
        })
    return f"Extracted {len(books)} books, first: {books[0]['title'][:30]} @ {books[0]['price']}" if books else "no books"

def flow10_pw():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page()
        page.goto("https://books.toscrape.com/catalogue/page-1.html")
        articles = page.query_selector_all("article.product_pod")
        books = []
        for art in articles:
            title = art.query_selector("h3 a").get_attribute("title")
            price = art.query_selector(".price_color").inner_text()
            rating_cls = art.query_selector(".star-rating").get_attribute("class")
            rating = rating_cls.replace("star-rating ", "") if rating_cls else "?"
            books.append({"title": title, "price": price, "rating": rating})
        b.close()
        return f"Extracted {len(books)} books, first: {books[0]['title'][:30]} @ {books[0]['price']}" if books else "no books"


# ═══════════════════════════════════════════════════════════
#  RUN ALL
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    flows = [
        ("1.  Google Search → scrape results",     flow1_nyx, flow1_pw),
        ("2.  Login flow (CSRF + form POST)",       flow2_nyx, flow2_pw),
        ("3.  Paginated scraping (3 pages)",        flow3_nyx, flow3_pw),
        ("4.  Form submission",                     flow4_nyx, flow4_pw),
        ("5.  JSON API fetch (GitHub)",             flow5_nyx, flow5_pw),
        ("6.  Price monitoring (product page)",     flow6_nyx, flow6_pw),
        ("7.  Multi-step drill-down (4 pages)",     flow7_nyx, flow7_pw),
        ("8.  File download (PNG)",                 flow8_nyx, flow8_pw),
        ("9.  Scrape behind Cloudflare (Zillow)",   flow9_nyx, flow9_pw),
        ("10. Structured data extraction",          flow10_nyx, flow10_pw),
    ]

    for name, nfn, pfn in flows:
        run_test(name, nfn, pfn)

    # ── Summary ──────────────────────────────────────────────
    print(f"\n\n{'='*90}")
    print(f"  AUTOMATION FLOW RESULTS — Nyx (aegis --browser-mode) vs Playwright (headless)")
    print(f"{'='*90}")
    print(f"{'Flow':<48s} {'Nyx':^20} {'Playwright':^20}")
    print(f"{'-'*48} {'-'*20} {'-'*20}")

    nyx_w = pw_w = 0
    for r in results:
        ns = f"{'PASS' if r['nyx_pass'] else 'FAIL'} ({r['nyx_time']}s)"
        ps = f"{'PASS' if r['pw_pass'] else 'FAIL'} ({r['pw_time']}s)"
        print(f"{r['test']:<48s} {ns:^20} {ps:^20}")
        if r['nyx_pass']: nyx_w += 1
        if r['pw_pass']: pw_w += 1

    print(f"{'-'*48} {'-'*20} {'-'*20}")
    print(f"{'TOTAL PASSED':<48s} {nyx_w:^20} {pw_w:^20}")

    # Speed comparison
    nyx_total = sum(r["nyx_time"] for r in results if r["nyx_pass"])
    pw_total = sum(r["pw_time"] for r in results if r["pw_pass"])
    print(f"\nTotal time (passing tests): Nyx {nyx_total:.1f}s vs Playwright {pw_total:.1f}s")
    if pw_total > 0:
        print(f"Nyx is {pw_total/nyx_total:.1f}x {'faster' if nyx_total < pw_total else 'slower'} overall")

    print(f"\nDetailed breakdown:")
    for r in results:
        winner = ""
        if r["nyx_pass"] and not r["pw_pass"]:
            winner = " ← NYX WINS"
        elif r["pw_pass"] and not r["nyx_pass"]:
            winner = " ← PW WINS"
        elif r["nyx_pass"] and r["pw_pass"]:
            nyx_b = "BLOCKED" in r["nyx_detail"]
            pw_b = "BLOCKED" in r["pw_detail"]
            if pw_b and not nyx_b:
                winner = " ← NYX WINS (PW blocked)"
            elif nyx_b and not pw_b:
                winner = " ← PW WINS (NYX blocked)"
            elif r["nyx_time"] < r["pw_time"] * 0.5:
                winner = f" ← NYX {r['pw_time']/r['nyx_time']:.0f}x faster"
            elif r["pw_time"] < r["nyx_time"] * 0.5:
                winner = f" ← PW {r['nyx_time']/r['pw_time']:.0f}x faster"
        print(f"  {r['test']}{winner}")
        print(f"    Nyx:        {r['nyx_detail'][:100]}")
        print(f"    Playwright: {r['pw_detail'][:100]}")
