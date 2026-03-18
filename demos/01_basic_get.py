"""
Demo 01: Basic GET — fetch a page with stealth browser headers.
"""

from nyx import Nyx

client = Nyx()

# Simple GET — aegis sends browser-like TLS fingerprint + headers
resp = client.get("https://example.com")

print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.content_type}")
print(f"Body size: {len(resp.body)} bytes")
print()
print(resp.text[:500])
