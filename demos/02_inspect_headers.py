"""
Demo 02: Inspect what headers Nyx sends — proves browser-mode is active.
"""

from nyx import Nyx

client = Nyx()

# httpbin echoes back the headers we sent
resp = client.get("https://httpbin.org/headers")
data = resp.json()

print("Headers sent by Nyx (browser-mode):\n")
for key, val in sorted(data["headers"].items()):
    print(f"  {key}: {val}")
