"""Nyx — stealth HTTP client powered by Aegis CLI."""

from __future__ import annotations

import json as _json
import shutil
import subprocess

from nyx.errors import NyxConnectionError, NyxError, NyxTimeout
from nyx.response import Response


def _map_profile_to_browser(profile: str) -> str:
    """Map a profile name like 'chrome131' to a BrowserForge browser type."""
    profile = profile.lower()
    if profile.startswith("chrome"):
        return "chrome"
    if profile.startswith("firefox"):
        return "firefox"
    if profile.startswith("safari"):
        return "safari"
    # "random" or unknown — let BrowserForge pick
    return "chrome"


class Nyx:
    """Stealth HTTP client using Aegis with browser impersonation.

    Makes requests that look like a real browser at the TLS, HTTP/2,
    and header level. Bypasses bot detection by default.

    Usage::

        from nyx import Nyx

        client = Nyx()
        resp = client.get("https://example.com")
        print(resp.text)

        # Impersonate Chrome 131
        client = Nyx(profile="chrome131")
        resp = client.get("https://nowsecure.nl")

        # With hardware spoofing
        client = Nyx(profile="chrome131", spoof_hardware=True)

        # Rotating proxies — new session per proxy
        for proxy in proxies:
            client = Nyx(profile="chrome131", proxy=proxy)
            client.get("https://target.com")
    """

    def __init__(
        self,
        *,
        browser_mode: bool = True,
        user_agent: str | None = None,
        timeout: int = 30,
        follow_redirects: bool = True,
        max_redirects: int = 10,
        proxy: str | None = None,
        binary: str | None = None,
        profile: str | None = None,
        spoof_hardware: bool = False,
    ):
        """Create a new Nyx client.

        Args:
            browser_mode:    Send browser-like headers and TLS fingerprint (default True).
            user_agent:      Custom User-Agent string.
            timeout:         Request timeout in seconds.
            follow_redirects: Follow HTTP redirects (default True).
            max_redirects:   Maximum number of redirects to follow.
            proxy:           Proxy URL (http://, socks5://).
            binary:          Path to aegis binary (auto-detected if not set).
            profile:         Browser impersonation profile (e.g. "chrome131", "firefox134", "random").
            spoof_hardware:  Spoof hardware fingerprint (cores, GPU, screen) — requires profile.
        """
        self.browser_mode = browser_mode
        self.user_agent = user_agent
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self.proxy = proxy
        self.profile = profile
        self.spoof_hardware = spoof_hardware
        self._binary = binary or self._find_aegis()
        self._bf_headers: dict[str, str] = {}

        if not self._binary:
            raise NyxError(
                "aegis binary not found. Run 'nyx install' or pass binary='path/to/aegis'"
            )

        # Generate BrowserForge fingerprint once per session
        if profile:
            self._generate_browserforge_headers(profile)

    @staticmethod
    def _find_aegis() -> str | None:
        """Find the aegis binary: bundled install first, then PATH."""
        try:
            from nyx._paths import get_aegis_path, get_installed_versions
            versions = get_installed_versions()
            if versions:
                path = get_aegis_path(versions[-1])
                if path.exists():
                    return str(path)
        except Exception:
            pass
        return shutil.which("aegis")

    def _generate_browserforge_headers(self, profile: str) -> None:
        """Generate session-stable headers from BrowserForge."""
        try:
            from browserforge.fingerprints import FingerprintGenerator
        except ImportError:
            # BrowserForge not installed — profile still works at TLS/H2 level
            return

        browser = _map_profile_to_browser(profile)
        fg = FingerprintGenerator(browser=browser)
        fp = fg.generate()

        # Extract headers from BrowserForge fingerprint
        if hasattr(fp, "headers") and fp.headers:
            self._bf_headers = dict(fp.headers)

    def get(self, url: str, *, headers: dict | None = None, **kwargs) -> Response:
        """Send a GET request."""
        return self._request("GET", url, headers=headers, **kwargs)

    def post(self, url: str, *, data: str | None = None,
             json: dict | None = None, headers: dict | None = None,
             **kwargs) -> Response:
        """Send a POST request."""
        return self._request("POST", url, data=data, json=json,
                             headers=headers, **kwargs)

    def put(self, url: str, *, data: str | None = None,
            json: dict | None = None, headers: dict | None = None,
            **kwargs) -> Response:
        """Send a PUT request."""
        return self._request("PUT", url, data=data, json=json,
                             headers=headers, **kwargs)

    def delete(self, url: str, *, headers: dict | None = None,
               **kwargs) -> Response:
        """Send a DELETE request."""
        return self._request("DELETE", url, headers=headers, **kwargs)

    def head(self, url: str, *, headers: dict | None = None,
             **kwargs) -> Response:
        """Send a HEAD request."""
        return self._request("HEAD", url, headers=headers, **kwargs)

    def _request(
        self,
        method: str,
        url: str,
        *,
        data: str | None = None,
        json: dict | None = None,
        headers: dict | None = None,
        timeout: int | None = None,
        follow_redirects: bool | None = None,
    ) -> Response:
        """Build and execute an aegis CLI command."""
        cmd = [self._binary, "-s"]

        # Method
        cmd.extend(["-X", method])

        # Browser impersonation profile
        if self.profile:
            cmd.extend(["--profile", self.profile])
        elif self.browser_mode:
            cmd.append("--browser-mode")

        # Hardware spoofing
        if self.spoof_hardware and self.profile:
            cmd.append("--spoof-hardware")

        # User agent (overrides profile default)
        if self.user_agent:
            cmd.extend(["--user-agent", self.user_agent])

        # Inject BrowserForge headers (session-stable, generated once in __init__)
        user_header_keys = {k.lower() for k in (headers or {})}
        for key, val in self._bf_headers.items():
            # Don't override user-provided headers
            if key.lower() in user_header_keys:
                continue
            cmd.extend(["-H", f"{key}: {val}"])

        # User headers (highest priority)
        if headers:
            for key, val in headers.items():
                cmd.extend(["-H", f"{key}: {val}"])

        # Body
        if json is not None:
            cmd.extend(["-d", _json.dumps(json)])
            cmd.extend(["-H", "Content-Type: application/json"])
            cmd.extend(["-H", "Accept: application/json"])
        elif data is not None:
            cmd.extend(["-d", data])

        # Redirects
        follow = follow_redirects if follow_redirects is not None else self.follow_redirects
        if not follow:
            cmd.append("--no-follow")
        else:
            cmd.extend(["--max-redirects", str(self.max_redirects)])

        # Timeout
        cmd.extend(["--timeout", str(timeout or self.timeout)])

        # Proxy
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])

        # Include response headers so we can parse them
        cmd.append("-i")

        # URL (must be last)
        cmd.append(url)

        return self._exec(cmd, url)

    def _exec(self, cmd: list[str], url: str) -> Response:
        """Run aegis and parse the output into a Response."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.timeout + 5,
            )
        except subprocess.TimeoutExpired:
            raise NyxTimeout(f"Request timed out after {self.timeout}s: {url}")
        except FileNotFoundError:
            raise NyxError(f"aegis binary not found at {self._binary}")

        if result.returncode == 28:
            raise NyxTimeout(f"Request timed out: {url}")
        if result.returncode == 1:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise NyxConnectionError(f"Connection failed: {url} — {stderr}")

        output = result.stdout

        # Parse response: -i output has headers then blank line then body
        # Format: "HTTP/2 200\r\nheader: value\r\n\r\nbody..."
        status_code, headers, body = self._parse_response(output)

        return Response(
            status_code=status_code,
            headers=headers,
            body=body,
            url=url,
        )

    def _parse_response(self, raw: bytes) -> tuple[int, dict[str, str], bytes]:
        """Parse aegis -i output into (status, headers, body)."""
        # Find the header/body separator
        sep = b"\r\n\r\n"
        sep_idx = raw.find(sep)
        if sep_idx == -1:
            # Try LF-only separator
            sep = b"\n\n"
            sep_idx = raw.find(sep)

        if sep_idx == -1:
            # No headers found — treat entire output as body
            return 0, {}, raw

        header_block = raw[:sep_idx].decode("utf-8", errors="replace")
        body = raw[sep_idx + len(sep):]

        lines = header_block.split("\n")

        # First line: "HTTP/2 200" or "HTTP/1.1 200 OK"
        status_code = 0
        if lines:
            parts = lines[0].strip().split(None, 2)
            if len(parts) >= 2:
                try:
                    status_code = int(parts[1])
                except ValueError:
                    pass

        # Parse headers
        headers: dict[str, str] = {}
        for line in lines[1:]:
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                headers[key.strip().lower()] = val.strip()

        return status_code, headers, body

    def __repr__(self) -> str:
        if self.profile:
            return f"Nyx(profile={self.profile!r}, binary={self._binary!r})"
        mode = "browser" if self.browser_mode else "raw"
        return f"Nyx(mode={mode!r}, binary={self._binary!r})"
