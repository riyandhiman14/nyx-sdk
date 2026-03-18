"""
Demo 04: TLS Fingerprint — check what fingerprint Nyx presents.

Compares Nyx (browser-mode) vs raw mode to show the stealth difference.
"""

import json
from nyx import Nyx

# Browser mode (default) — stealth fingerprint
stealth = Nyx()
resp = stealth.get("https://tls.peet.ws/api/all")
stealth_data = resp.json()

print("=== Nyx (browser-mode) ===")
print(f"  JA3 hash:       {stealth_data.get('tls', {}).get('ja3_hash', 'n/a')}")
print(f"  JA4:             {stealth_data.get('tls', {}).get('ja4', 'n/a')}")
print(f"  H2 fingerprint:  {stealth_data.get('http2', {}).get('fingerprint', 'n/a')}")
print(f"  User-Agent:      {stealth_data.get('http1', {}).get('headers', {}).get('User-Agent', 'n/a')}")

# Raw mode — no browser headers
raw = Nyx(browser_mode=False)
resp = raw.get("https://tls.peet.ws/api/all")
raw_data = resp.json()

print("\n=== Nyx (raw mode) ===")
print(f"  JA3 hash:       {raw_data.get('tls', {}).get('ja3_hash', 'n/a')}")
print(f"  JA4:             {raw_data.get('tls', {}).get('ja4', 'n/a')}")
print(f"  H2 fingerprint:  {raw_data.get('http2', {}).get('fingerprint', 'n/a')}")
print(f"  User-Agent:      {raw_data.get('http1', {}).get('headers', {}).get('User-Agent', 'n/a')}")
