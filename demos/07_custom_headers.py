"""
Demo 07: Custom Headers & Methods — PUT, DELETE, custom headers on top of browser-mode.
"""

from nyx import Nyx

client = Nyx()

# PUT with custom headers
print("=== PUT request ===")
resp = client.put("https://httpbin.org/put",
                  json={"updated": True},
                  headers={"X-Custom": "nyx-demo"})
data = resp.json()
print(f"Status: {resp.status_code}")
print(f"Server saw X-Custom: {data['headers'].get('X-Custom', 'missing')}")

# DELETE
print("\n=== DELETE request ===")
resp = client.delete("https://httpbin.org/delete")
print(f"Status: {resp.status_code}")

# HEAD
print("\n=== HEAD request ===")
resp = client.head("https://httpbin.org/get")
print(f"Status: {resp.status_code}")
print(f"Body: {len(resp.body)} bytes (should be 0)")
print(f"Content-Type header: {resp.headers.get('content-type', 'none')}")
