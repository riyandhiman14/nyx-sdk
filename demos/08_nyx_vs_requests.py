"""
Demo 08: Nyx vs requests — side-by-side comparison.

Shows that Nyx sends proper browser headers while requests sends obvious bot headers.
"""

import requests as req
from nyx import Nyx

nyx = Nyx()

# Compare headers sent
print("=== Headers comparison (httpbin echo) ===\n")

nyx_resp = nyx.get("https://httpbin.org/headers")
nyx_headers = nyx_resp.json()["headers"]

req_resp = req.get("https://httpbin.org/headers")
req_headers = req_resp.json()["headers"]

all_keys = sorted(set(list(nyx_headers.keys()) + list(req_headers.keys())))

print(f"{'Header':<30s} {'Nyx (browser-mode)':<45s} {'requests'}")
print(f"{'-'*30} {'-'*45} {'-'*30}")
for key in all_keys:
    nyx_val = nyx_headers.get(key, "—")[:44]
    req_val = req_headers.get(key, "—")[:29]
    print(f"{key:<30s} {nyx_val:<45s} {req_val}")

print(f"\nNyx sends {len(nyx_headers)} headers, requests sends {len(req_headers)} headers")
print("Nyx includes sec-ch-ua, sec-fetch-*, Accept-Language — requests doesn't.")
