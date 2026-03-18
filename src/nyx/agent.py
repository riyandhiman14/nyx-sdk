"""AgentBrowser — direct AgentServer API for AI agents.

Thin wrapper over the AgentServer REST API. No translation, no abstraction.
Every method maps 1:1 to an endpoint. Snapshots in, snapshots out.
"""

from __future__ import annotations

import json
from typing import Any

from nyx._launcher import BrowserProcess
from nyx._transport import Transport
from nyx.errors import NyxNotFound
from nyx.snapshot import Snapshot


class AgentBrowser:
    """Direct API to the Nyx AgentServer — built for AI agents.

    Usage::

        from nyx.agent import AgentBrowser

        async with await AgentBrowser.launch() as browser:
            # See the page
            snap = await browser.snapshot()
            print(snap.page_text)
            print(snap.elements)  # [{action_id, tag, text}, ...]

            # Act on it
            snap = await browser.act("click", "b_4f2a1c")
            snap = await browser.act("fill", "i_8e3f2a", value="Tokyo")
            snap = await browser.act("submit", "i_8e3f2a")
            snap = await browser.act("navigate", "https://example.com")
            snap = await browser.act("scroll", direction="down")

            # Batch actions
            snap = await browser.act_sequence([
                {"action": "fill", "target": "i_3a2b", "value": "Tokyo"},
                {"action": "submit", "target": "i_3a2b"},
            ])

    Target resolution (server-side, tried in order):
        1. action_id  — exact match from snapshot tree (preferred)
        2. text:Submit — match by visible text
        3. href:/hotel — match by link URL substring
        4. css:input#q — CSS selector fallback
    """

    def __init__(self, transport: Transport, *,
                 _process: BrowserProcess | None = None):
        self._transport = transport
        self._process = _process

    # ── Lifecycle ──

    @classmethod
    async def launch(cls, *, headless: bool = True, proxy: str | None = None,
                     fingerprint: dict | str | None = None,
                     timeout: float = 30, version: str | None = None,
                     auto_install: bool = True,
                     extra_args: list[str] | None = None) -> AgentBrowser:
        """Launch a new browser and return an AgentBrowser connected to it."""
        process = await BrowserProcess.start(
            headless=headless, proxy=proxy, fingerprint=fingerprint,
            version=version, auto_install=auto_install, extra_args=extra_args,
        )
        transport = Transport(
            f"http://127.0.0.1:{process.port}", timeout=timeout
        )
        return cls(transport, _process=process)

    @classmethod
    async def connect(cls, host: str = "http://localhost:8765", *,
                      timeout: float = 30) -> AgentBrowser:
        """Connect to an already-running AgentServer."""
        transport = Transport(host, timeout=timeout)
        await transport.get("/status")
        return cls(transport)

    async def close(self) -> None:
        await self._transport.close()
        if self._process:
            await self._process.terminate()

    async def __aenter__(self) -> AgentBrowser:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    # ══════════════════════════════════════════════════════════
    # v2 API (preferred)
    # ══════════════════════════════════════════════════════════

    async def snapshot(self, *, full: bool = False) -> Snapshot:
        """GET /snapshot — semantic tree with action_ids.

        Args:
            full: Include off-screen elements (default: viewport only).
        """
        params = {"full": "true"} if full else {}
        return Snapshot(await self._transport.get("/snapshot", params=params))

    async def act(self, action: str, target: str | None = None, **kwargs) -> Snapshot:
        """POST /act — perform one action, returns updated snapshot.

        Element actions (target = action_id from snapshot):
            click, fill (+ value=), submit, select (+ value=)

        Navigation actions:
            navigate (target = URL), back, forward, scroll (+ direction=)

        Target formats:
            "b_4f2a1c"           — action_id (preferred)
            "text:Sign In"       — match by text
            "href:/login"        — match by link URL
            "css:button.primary" — CSS selector
        """
        # Route "navigate" to dedicated /navigate endpoint (blocks until loaded)
        if action == "navigate" and target:
            await self._transport.post(
                "/navigate", {"url": target},
                timeout=max(self._transport.timeout, 60),
            )
            return await self.snapshot(full=True)

        body: dict[str, Any] = {"action": action}
        if target is not None:
            body["target"] = target
        body.update(kwargs)
        data = await self._transport.post(
            "/act", body, timeout=max(self._transport.timeout, 60)
        )
        snap = Snapshot(data)

        if snap.act_error:
            raise NyxNotFound(
                f"{snap.act_error} (did_you_mean: {snap.did_you_mean})")
        return snap

    async def act_sequence(self, steps: list[dict]) -> Snapshot:
        """POST /act-sequence — batch multiple actions, single response.

        Example:
            await browser.act_sequence([
                {"action": "fill", "target": "i_8e3f2a", "value": "Mumbai"},
                {"action": "fill", "target": "i_3c4d5e", "value": "2025-04-01"},
                {"action": "submit", "target": "i_8e3f2a"},
            ])
        """
        data = await self._transport.post(
            "/act-sequence", {"sequence": steps},
            timeout=max(self._transport.timeout, 30),
        )
        return Snapshot(data)

    # ══════════════════════════════════════════════════════════
    # Navigation & Interaction (legacy, still works)
    # ══════════════════════════════════════════════════════════

    async def navigate(self, url: str, timeout: int = 15000) -> dict:
        """POST /navigate — go to URL, blocks until loaded."""
        return await self._transport.post(
            "/navigate", {"url": url, "timeout": timeout},
            timeout=timeout / 1000 + 5,
        )

    async def click_element(self, element_id: int, timeout: int = 5000) -> dict:
        """POST /click — click element by integer ID (legacy)."""
        return await self._transport.post("/click", {"id": element_id, "timeout": timeout})

    async def click_at(self, x: int, y: int) -> dict:
        """POST /click-at — click at pixel coordinates."""
        return await self._transport.post("/click-at", {"x": x, "y": y})

    async def type_text(self, element_id: int, text: str) -> dict:
        """POST /type — type into element by integer ID (legacy)."""
        return await self._transport.post("/type", {"id": element_id, "text": text})

    async def submit_element(self, element_id: int) -> dict:
        """POST /submit — submit form by integer ID (legacy)."""
        return await self._transport.post("/submit", {"id": element_id})

    async def select_option(self, element_id: int, value: str) -> dict:
        """POST /select — select dropdown option (legacy)."""
        return await self._transport.post("/select", {"id": element_id, "value": value})

    async def back(self) -> dict:
        """POST /back"""
        return await self._transport.post("/back")

    async def forward(self) -> dict:
        """POST /forward"""
        return await self._transport.post("/forward")

    async def reset(self, url: str | None = None) -> dict:
        """POST /reset — reset browser state."""
        return await self._transport.post("/reset", {"url": url} if url else {})

    # ══════════════════════════════════════════════════════════
    # DOM & Content
    # ══════════════════════════════════════════════════════════

    async def map(self) -> dict:
        """GET /map — flat action map with integer IDs (legacy)."""
        return await self._transport.get("/map")

    async def text(self) -> str:
        """GET /text — extracted page text."""
        data = await self._transport.get("/text")
        return data.get("text", "") if isinstance(data, dict) else ""

    async def page_html(self) -> str:
        """GET /page-html — full page HTML."""
        data = await self._transport.get("/page-html")
        if isinstance(data, dict):
            return data.get("html", "")
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        return str(data)

    async def eval_js(self, script: str) -> Any:
        """POST /eval-js — execute JavaScript, return result."""
        result = await self._transport.post("/eval-js", {"script": script})
        if isinstance(result, dict):
            val = result.get("result")
            if isinstance(val, str):
                stripped = val.strip()
                if stripped and stripped[0] in ('{', '[', '"') or stripped in ('true', 'false', 'null'):
                    try:
                        return json.loads(val)
                    except (ValueError, TypeError):
                        pass
                return val
            return val
        return result

    async def locator(self, selector: str) -> dict:
        """POST /locator — find element by CSS selector."""
        return await self._transport.post("/locator", {"selector": selector})

    async def media(self) -> dict:
        """GET /media — detect media elements."""
        return await self._transport.get("/media")

    async def screenshot(self, path: str | None = None) -> bytes:
        """GET /screenshot — PNG screenshot."""
        data = await self._transport.get_bytes("/screenshot")
        if path:
            with open(path, "wb") as f:
                f.write(data)
        return data

    # ══════════════════════════════════════════════════════════
    # Scrolling & Extraction
    # ══════════════════════════════════════════════════════════

    async def scroll_legacy(self, dx: int = 0, dy: int = -300) -> dict:
        """POST /scroll — scroll by pixel offset (legacy)."""
        return await self._transport.post("/scroll", {"dx": dx, "dy": dy})

    async def scroll_up(self) -> dict:
        """POST /scroll-up"""
        return await self._transport.post("/scroll-up")

    async def extract(self) -> dict:
        """POST /extract — force re-extract action map."""
        return await self._transport.post("/extract")

    async def request_more(self) -> dict:
        """POST /request-more — scroll down + re-extract."""
        return await self._transport.post("/request-more")

    # ══════════════════════════════════════════════════════════
    # Polling / Waiting
    # ══════════════════════════════════════════════════════════

    async def status(self, *, wait: str | None = None,
                     timeout: int | None = None) -> dict:
        """GET /status — check server, optionally wait for navigation."""
        params = {}
        if wait:
            params["wait"] = wait
        if timeout is not None:
            params["timeout"] = str(timeout)
        return await self._transport.get("/status", params=params or None)

    async def wait_for(self, selector: str, timeout: int = 5000) -> dict:
        """POST /wait — block until CSS selector found."""
        return await self._transport.post(
            "/wait", {"selector": selector, "timeout": timeout},
            timeout=timeout / 1000 + 5,
        )

    async def wait_challenge(self, timeout: int = 15000) -> dict:
        """POST /wait-challenge — wait for anti-bot challenge."""
        return await self._transport.post(
            "/wait-challenge", {"timeout": timeout},
            timeout=timeout / 1000 + 5,
        )

    # ══════════════════════════════════════════════════════════
    # Tab Management
    # ══════════════════════════════════════════════════════════

    async def tabs(self) -> list:
        """GET /tabs — list open tabs."""
        data = await self._transport.get("/tabs")
        return data if isinstance(data, list) else data.get("tabs", [])

    async def new_tab(self, url: str | None = None) -> dict:
        """POST /new-tab — open new tab, optionally navigate."""
        return await self._transport.post("/new-tab", {"url": url} if url else {})

    async def switch_tab(self, tab_id: str) -> dict:
        """POST /switch-tab"""
        return await self._transport.post("/switch-tab", {"id": tab_id})

    async def close_tab(self, tab_id: str) -> dict:
        """POST /close-tab"""
        return await self._transport.post("/close-tab", {"id": tab_id})

    # ══════════════════════════════════════════════════════════
    # Session Management
    # ══════════════════════════════════════════════════════════

    async def session_create(self, **config) -> dict:
        """POST /session/create"""
        return await self._transport.post("/session/create", config)

    async def session_status(self) -> dict:
        """GET /session/status"""
        return await self._transport.get("/session/status")

    async def session_destroy(self) -> dict:
        """POST /session/destroy"""
        return await self._transport.post("/session/destroy")

    async def session_health(self) -> dict:
        """GET /session/health"""
        return await self._transport.get("/session/health")

    def __repr__(self) -> str:
        managed = " (managed)" if self._process else ""
        return f"AgentBrowser(host={self._transport.host!r}{managed})"
