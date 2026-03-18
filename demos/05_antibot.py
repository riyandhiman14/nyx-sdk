"""
Demo 05: Anti-Bot Bypass — hit sites that block bots.

Nyx's browser-mode TLS + headers should get through where requests/urllib fail.
"""

from nyx import Nyx

client = Nyx()

sites = [
    ("Cloudflare", "https://nowsecure.nl"),
    ("httpbin", "https://httpbin.org/get"),
]

for name, url in sites:
    print(f"[{name}] {url}")
    try:
        resp = client.get(url)
        blocked = resp.status_code in (403, 503) or "captcha" in resp.text.lower()
        status = "BLOCKED" if blocked else "OK"
        print(f"  Status: {resp.status_code} — {status}")
        print(f"  Body: {resp.text[:150]}...")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
