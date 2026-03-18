"""
Demo 03: POST JSON — send and receive JSON data.
"""

from nyx import Nyx

client = Nyx()

resp = client.post("https://httpbin.org/post", json={
    "name": "nyx",
    "version": "0.1.0",
    "stealth": True,
})

data = resp.json()
print(f"Status: {resp.status_code}")
print(f"Server saw our body: {data['data']}")
print(f"Content-Type sent: {data['headers'].get('Content-Type', '?')}")
