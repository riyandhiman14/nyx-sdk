"""Nyx Browser — async browser automation via the AgentServer API."""

from __future__ import annotations

from typing import Any

from nyx._launcher import BrowserProcess
from nyx._transport import Transport
from nyx.errors import NyxNotFound
from nyx.snapshot import Snapshot


class Browser:
    """Control the Nyx Browser via the AgentServer API.

    Playwright-compatible usage::

        async with await Browser.launch() as browser:
            page = await browser.new_page()
            await page.goto("https://example.com")
            print(await page.title())

    Legacy usage (still supported)::

        async with await Browser.launch() as b:
            snap = await b.goto("https://example.com")
            print(snap.page_text)
    """

    def __init__(
        self,
        transport: Transport,
        *,
        _process: BrowserProcess | None = None,
    ):
        self._transport = transport
        self._process = _process
        self._pages: list = []

    # ── Lifecycle ─────────────────────────────────────────

    @classmethod
    async def launch(
        cls,
        *,
        headless: bool = True,
        proxy: str | None = None,
        fingerprint: dict | str | None = None,
        timeout: float = 30,
        version: str | None = None,
        auto_install: bool = True,
        extra_args: list[str] | None = None,
    ) -> Browser:
        """Launch a new browser instance.

        Args:
            headless: Run without GUI (default True).
            proxy: Proxy URL (e.g. http://user:pass@host:port or socks5://...).
            fingerprint: Browser fingerprint profile (dict or JSON string).
            timeout: Max seconds to wait for browser readiness.
            version: Browser version to use (defaults to SDK version).
            auto_install: Auto-download browser if not found (default True).
            extra_args: Additional CLI args.
        """
        process = await BrowserProcess.start(
            headless=headless,
            proxy=proxy,
            fingerprint=fingerprint,
            version=version,
            auto_install=auto_install,
            extra_args=extra_args,
        )
        transport = Transport(
            f"http://127.0.0.1:{process.port}", timeout=timeout
        )
        return cls(transport, _process=process)

    @classmethod
    async def connect(
        cls,
        host: str = "http://localhost:8765",
        *,
        timeout: float = 30,
    ) -> Browser:
        """Connect to an already-running browser."""
        transport = Transport(host, timeout=timeout)
        await transport.wait_ready(timeout)
        return cls(transport)

    async def close(self) -> None:
        """Shut down the browser and clean up."""
        await self._transport.close()
        if self._process:
            await self._process.terminate()

    async def __aenter__(self) -> Browser:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    # ── Playwright-compatible: Page management ────────────

    async def new_page(self):
        """Create a new tab and return a Page object."""
        from nyx.page import Page

        result = await self.new_tab()
        tab_id = ""
        if isinstance(result, dict):
            tab_id = result.get("id", result.get("tab_id", ""))

        if not tab_id:
            tabs_list = await self.tabs()
            if tabs_list:
                last = tabs_list[-1]
                tab_id = last.get("id", last.get("tab_id", str(len(tabs_list) - 1)))

        page = Page(self, tab_id)
        self._pages.append(page)
        return page

    async def _get_pages(self):
        """Return list of Page objects for all open tabs."""
        from nyx.page import Page

        tabs_list = await self.tabs()
        pages = []
        for t in tabs_list:
            tid = t.get("id", t.get("tab_id", ""))
            existing = next((p for p in self._pages if p._tab_id == tid), None)
            if existing and not existing._closed:
                pages.append(existing)
            else:
                pages.append(Page(self, tid))
        return pages

    @property
    def pages(self):
        """Synchronous accessor — returns cached pages."""
        return list(self._pages)

    # ── v2 API ────────────────────────────────────────────

    async def snapshot(self, *, full: bool = False) -> Snapshot:
        params = {"full": "true"} if full else {}
        return Snapshot(await self._transport.get("/snapshot", params=params))

    async def act(self, action: str, target: str | None = None, **kwargs) -> Snapshot:
        body: dict[str, Any] = {"action": action}
        if target is not None:
            body["target"] = target
        body.update(kwargs)
        data = await self._transport.post("/act", body, timeout=max(self._transport.timeout, 15))
        snap = Snapshot(data)
        if snap.act_error:
            raise NyxNotFound(f"{snap.act_error} (did_you_mean: {snap.did_you_mean})")
        return snap

    async def act_sequence(self, steps: list[dict]) -> Snapshot:
        data = await self._transport.post(
            "/act-sequence", {"sequence": steps},
            timeout=max(self._transport.timeout, 30),
        )
        return Snapshot(data)

    # ── High-level actions (legacy, still supported) ──────

    async def goto(self, url: str) -> Snapshot:
        await self._transport.post("/navigate", {"url": url},
                                   timeout=max(self._transport.timeout, 15))
        return await self.snapshot()

    async def click(self, target: str) -> Snapshot:
        return await self.act("click", target=target)

    async def fill(self, target: str, value: str) -> Snapshot:
        return await self.act("fill", target=target, value=value)

    async def submit(self, target: str) -> Snapshot:
        return await self.act("submit", target=target)

    async def select(self, target: str, value: str) -> Snapshot:
        return await self.act("select", target=target, value=value)

    async def scroll(self, direction: str = "down") -> Snapshot:
        return await self.act("scroll", direction=direction)

    async def back(self) -> Snapshot:
        return await self.act("back")

    async def forward(self) -> Snapshot:
        return await self.act("forward")

    # ── Legacy API ────────────────────────────────────────

    async def status(self) -> dict:
        return await self._transport.get("/status")

    async def text(self) -> str:
        data = await self._transport.get("/text")
        return data.get("text", "") if isinstance(data, dict) else ""

    async def screenshot(self, path: str | None = None) -> bytes:
        data = await self._transport.get_bytes("/screenshot")
        if path:
            with open(path, "wb") as f:
                f.write(data)
        return data

    async def tabs(self) -> list:
        data = await self._transport.get("/tabs")
        return data if isinstance(data, list) else data.get("tabs", [])

    async def new_tab(self, url: str | None = None) -> dict:
        body = {"url": url} if url else {}
        return await self._transport.post("/new-tab", body)

    async def switch_tab(self, tab_id: str) -> dict:
        return await self._transport.post("/switch-tab", {"id": tab_id})

    async def close_tab(self, tab_id: str) -> dict:
        return await self._transport.post("/close-tab", {"id": tab_id})

    async def reset(self, url: str | None = None) -> dict:
        body = {"url": url} if url else {}
        return await self._transport.post("/reset", body)

    async def wait_for(self, selector: str, timeout: int = 5000) -> dict:
        return await self._transport.post(
            "/wait", {"selector": selector, "timeout": timeout},
            timeout=max(self._transport.timeout, timeout / 1000 + 2),
        )

    async def wait_challenge(self, timeout: int = 15000) -> dict:
        return await self._transport.post(
            "/wait-challenge", {"timeout": timeout},
            timeout=max(self._transport.timeout, timeout / 1000 + 2),
        )

    async def click_at(self, x: int, y: int) -> dict:
        return await self._transport.post("/click-at", {"x": x, "y": y})

    def __repr__(self) -> str:
        managed = " (managed)" if self._process else ""
        return f"Browser(host={self._transport.host!r}{managed})"
