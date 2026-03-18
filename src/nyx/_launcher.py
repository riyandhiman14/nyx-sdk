"""Browser process lifecycle management."""

from __future__ import annotations

import asyncio
import atexit
import signal
import socket
import subprocess
import sys
from urllib.request import urlopen

from nyx._paths import resolve_browser_executable
from nyx.errors import NyxBrowserCrashed, NyxLaunchError


def _find_free_port() -> int:
    """Find a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class BrowserProcess:
    """Manages a Nyx Browser subprocess."""

    def __init__(self, process: subprocess.Popen, port: int):
        self._process = process
        self.port = port
        self.pid = process.pid
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        if self._process.poll() is None:
            self._process.kill()

    @classmethod
    async def start(
        cls,
        *,
        headless: bool = True,
        port: int | None = None,
        proxy: str | None = None,
        profile: str | None = None,
        fingerprint: dict | str | None = None,
        version: str | None = None,
        auto_install: bool = True,
        extra_args: list[str] | None = None,
    ) -> BrowserProcess:
        """Start a new browser process.

        Args:
            headless: Run without GUI (default True).
            port: AgentServer port (auto-picked if None).
            proxy: Proxy URL (http://, socks5://, etc.).
            profile: Fingerprint profile name ("chrome131", "random", "windows").
            fingerprint: Raw fingerprint dict/JSON (overrides profile).
            version: Browser version to use (defaults to SDK version).
            auto_install: Auto-download browser if not found (default True).
            extra_args: Additional CLI args to pass to the browser.

        Returns:
            A BrowserProcess instance connected to the running browser.
        """
        try:
            executable = resolve_browser_executable(version)
        except FileNotFoundError:
            if not auto_install:
                raise
            sys.stderr.write("Nyx Browser not found. Installing...\n")
            from nyx._installer import install
            await install(version=version)
            executable = resolve_browser_executable(version)

        chosen_port = port or _find_free_port()

        args = [str(executable), "--agent-port", str(chosen_port)]
        if headless:
            args.append("--headless")
        if proxy:
            args.extend(["--proxy", proxy])

        # Resolve fingerprint: explicit dict/JSON > profile name > None
        fp = fingerprint
        if fp is None and profile is not None:
            from nyx._fingerprints import resolve_fingerprint
            fp = resolve_fingerprint(profile)
        if fp is not None:
            import json as _json
            fp_str = fp if isinstance(fp, str) else _json.dumps(fp)
            args.extend(["--fingerprint", fp_str])

        if extra_args:
            args.extend(extra_args)

        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise NyxLaunchError(
                f"Browser executable not found: {executable}\n"
                "Run 'nyx install' to download it."
            )
        except OSError as e:
            raise NyxLaunchError(f"Failed to start browser: {e}")

        instance = cls(proc, chosen_port)
        await instance.wait_ready()
        return instance

    async def wait_ready(self, timeout: float = 30) -> None:
        """Poll /status endpoint until the browser is ready."""
        url = f"http://127.0.0.1:{self.port}/status"
        deadline = asyncio.get_event_loop().time() + timeout
        delay = 0.1

        while asyncio.get_event_loop().time() < deadline:
            # Check if process crashed
            if self._process.poll() is not None:
                stderr = ""
                if self._process.stderr:
                    stderr = self._process.stderr.read().decode(errors="replace")
                raise NyxBrowserCrashed(
                    f"Browser process exited with code {self._process.returncode}"
                    + (f": {stderr[:500]}" if stderr else "")
                )

            try:
                resp = await asyncio.to_thread(urlopen, url, None, 2)
                if resp.status == 200:
                    return
            except Exception:
                pass

            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 2.0)

        raise NyxLaunchError(
            f"Browser didn't become ready within {timeout}s on port {self.port}"
        )

    def is_alive(self) -> bool:
        """Check if the browser process is still running."""
        return self._process.poll() is None

    async def terminate(self, timeout: float = 5) -> None:
        """Gracefully shut down: SIGTERM, wait, then SIGKILL if needed."""
        if self._process.poll() is not None:
            return

        self._process.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._process.wait),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self._process.kill()
            await asyncio.to_thread(self._process.wait)

    def kill(self) -> None:
        """Forcefully kill the browser process."""
        if self._process.poll() is None:
            self._process.kill()
