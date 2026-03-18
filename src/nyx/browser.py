"""Nyx Browser — async browser automation via the AgentServer API."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import aiohttp

from nyx._launcher import BrowserProcess
from nyx.errors import NyxConnectionError, NyxError, NyxNotFound, NyxTimeout


class Snapshot:
    """Page state from /snapshot or /act response."""

    def __init__(self, data: dict[str, Any]):
        self._raw = data
        self.url: str = data.get("url", "")
        self.title: str = data.get("title", "")
        self.tree = data.get("tree", {})
        self.scroll_y: float = data.get("scroll_y", 0)
        self.has_more: bool = data.get("has_more", False)
        self.viewport_height: int = data.get("viewport_height", 0)
        self.page_text: str = data.get("page_text", "")
        self.history: list = data.get("history", [])
        self.act_error: Optional[str] = data.get("act_error")
        self.did_you_mean: list = data.get("did_you_mean", [])
        self.failed_step: Optional[dict] = data.get("failed_step")
        self.elements: list[dict] = self._flatten(self.tree)

    def _flatten(self, root) -> list[dict]:
        nodes = [root] if isinstance(root, dict) else (root if isinstance(root, list) else [])
        result = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("action_id"):
                el = dict(node)
                if not el.get("text"):
                    el["text"] = self._collect_text(node)
                result.append(el)
            for child in node.get("children", []):
                if isinstance(child, dict):
                    result.extend(self._flatten(child))
        return result

    def _collect_text(self, node: dict) -> str:
        parts = []
        if "text" in node:
            parts.append(node["text"])
        for child in node.get("children", []):
            if isinstance(child, dict):
                parts.append(self._collect_text(child))
        return " ".join(p for p in parts if p).strip()

    def find(self, text: str) -> Optional[dict]:
        q = text.lower()
        for el in self.elements:
            if q in (el.get("text") or "").lower():
                return el
        return None

    def find_all(self, text: str) -> list[dict]:
        q = text.lower()
        return [el for el in self.elements if q in (el.get("text") or "").lower()]

    def by_tag(self, tag: str) -> list[dict]:
        return [el for el in self.elements if el.get("tag") == tag]

    def inputs(self) -> list[dict]:
        return [el for el in self.elements if el.get("tag") in ("input", "textarea")]

    def links(self) -> list[dict]:
        return [el for el in self.elements if el.get("tag") == "a"]

    def buttons(self) -> list[dict]:
        return [el for el in self.elements if el.get("tag") == "button"]

    def __repr__(self) -> str:
        return f"Snapshot(url={self.url!r}, title={self.title!r}, elements={len(self.elements)})"


class Browser:
    """Control the Nyx Browser via the AgentServer API.

    Usage::

        import asyncio
        from nyx import Browser

        async def main():
            async with await Browser.launch() as b:
                snap = await b.goto("https://example.com")
                print(snap.page_text)

        asyncio.run(main())

    Or connect to an already-running browser::

        async with await Browser.connect("http://localhost:8765") as b:
            snap = await b.snapshot()
    """

    def __init__(
        self,
        host: str = "http://localhost:8765",
        *,
        timeout: float = 15,
        _process: BrowserProcess | None = None,
    ):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self._process = _process
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    # ── Lifecycle ─────────────────────────────────────────

    @classmethod
    async def launch(
        cls,
        *,
        headless: bool = True,
        proxy: str | None = None,
        timeout: float = 30,
        version: str | None = None,
        extra_args: list[str] | None = None,
    ) -> Browser:
        """Launch a new browser instance.

        Args:
            headless: Run without GUI (default True).
            proxy: Proxy URL (reserved for future use).
            timeout: Max seconds to wait for browser readiness.
            version: Browser version to use (defaults to SDK version).
            extra_args: Additional CLI args.
        """
        process = await BrowserProcess.start(
            headless=headless,
            version=version,
            extra_args=extra_args,
        )
        browser = cls(
            host=f"http://127.0.0.1:{process.port}",
            timeout=timeout,
            _process=process,
        )
        return browser

    @classmethod
    async def connect(
        cls,
        host: str = "http://localhost:8765",
        *,
        timeout: float = 30,
    ) -> Browser:
        """Connect to an already-running browser."""
        browser = cls(host=host, timeout=timeout)
        await browser._wait_ready(timeout)
        return browser

    async def _wait_ready(self, max_wait: float = 30) -> None:
        url = f"{self.host}/status"
        deadline = asyncio.get_event_loop().time() + max_wait
        session = self._get_session()

        while asyncio.get_event_loop().time() < deadline:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as r:
                    if r.status == 200:
                        return
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
                pass
            await asyncio.sleep(1)

        raise NyxConnectionError(f"Nyx Browser not responding at {self.host}")

    async def close(self) -> None:
        """Shut down the browser and clean up."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        if self._process:
            await self._process.terminate()

    async def __aenter__(self) -> Browser:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    # ── HTTP helpers ──────────────────────────────────────

    async def _get(self, path: str, **params) -> Any:
        session = self._get_session()
        try:
            async with session.get(f"{self.host}{path}", params=params) as r:
                r.raise_for_status()
                ct = r.headers.get("content-type", "")
                if "json" in ct:
                    return await r.json()
                return await r.read()
        except aiohttp.ClientError as e:
            raise NyxConnectionError(f"Request failed: {e}") from e

    async def _post(self, path: str, body: dict | None = None, timeout: float | None = None) -> Any:
        session = self._get_session()
        t = aiohttp.ClientTimeout(total=timeout or self.timeout)
        try:
            async with session.post(f"{self.host}{path}", json=body or {}, timeout=t) as r:
                r.raise_for_status()
                ct = r.headers.get("content-type", "")
                if "json" in ct:
                    return await r.json()
                return await r.read()
        except aiohttp.ClientError as e:
            raise NyxConnectionError(f"Request failed: {e}") from e

    # ── v2 API ────────────────────────────────────────────

    async def snapshot(self, *, full: bool = False) -> Snapshot:
        params = {"full": "true"} if full else {}
        return Snapshot(await self._get("/snapshot", **params))

    async def act(self, action: str, target: str | None = None, **kwargs) -> Snapshot:
        body: dict[str, Any] = {"action": action}
        if target is not None:
            body["target"] = target
        body.update(kwargs)
        data = await self._post("/act", body, timeout=max(self.timeout, 15))
        snap = Snapshot(data)
        if snap.act_error:
            raise NyxNotFound(f"{snap.act_error} (did_you_mean: {snap.did_you_mean})")
        return snap

    async def act_sequence(self, steps: list[dict]) -> Snapshot:
        data = await self._post("/act-sequence", {"sequence": steps}, timeout=max(self.timeout, 30))
        return Snapshot(data)

    # ── High-level actions ────────────────────────────────

    async def goto(self, url: str) -> Snapshot:
        await self._post("/navigate", {"url": url}, timeout=max(self.timeout, 15))
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
        return await self._get("/status")

    async def text(self) -> str:
        data = await self._post("/text")
        return data.get("text", "") if isinstance(data, dict) else ""

    async def screenshot(self, path: str | None = None) -> bytes:
        session = self._get_session()
        async with session.get(f"{self.host}/screenshot") as r:
            data = await r.read()
        if path:
            with open(path, "wb") as f:
                f.write(data)
        return data

    async def tabs(self) -> list:
        data = await self._get("/tabs")
        return data if isinstance(data, list) else data.get("tabs", [])

    async def new_tab(self, url: str | None = None) -> dict:
        body = {"url": url} if url else {}
        return await self._post("/new-tab", body)

    async def switch_tab(self, tab_id: str) -> dict:
        return await self._post("/switch-tab", {"id": tab_id})

    async def close_tab(self, tab_id: str) -> dict:
        return await self._post("/close-tab", {"id": tab_id})

    async def reset(self, url: str | None = None) -> dict:
        body = {"url": url} if url else {}
        return await self._post("/reset", body)

    async def wait_for(self, selector: str, timeout: int = 5000) -> dict:
        return await self._post(
            "/wait", {"selector": selector, "timeout": timeout},
            timeout=max(self.timeout, timeout / 1000 + 2),
        )

    async def wait_challenge(self, timeout: int = 15000) -> dict:
        return await self._post(
            "/wait-challenge", {"timeout": timeout},
            timeout=max(self.timeout, timeout / 1000 + 2),
        )

    async def click_at(self, x: int, y: int) -> dict:
        return await self._post("/click-at", {"x": x, "y": y})

    def __repr__(self) -> str:
        managed = " (managed)" if self._process else ""
        return f"Browser(host={self.host!r}{managed})"
