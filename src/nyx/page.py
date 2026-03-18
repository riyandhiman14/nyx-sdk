"""Page — Playwright-compatible tab API for Nyx Browser."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any, Pattern

if TYPE_CHECKING:
    from nyx.browser import Browser

from nyx._transport import Transport
from nyx.errors import NyxNotFound, NyxTimeout


class ElementHandle:
    """Lightweight handle to a DOM element returned by query_selector."""

    def __init__(self, page: Page, data: dict[str, Any]):
        self._page = page
        self._data = data
        self.tag: str = data.get("tag", "")
        self.text: str = data.get("text", "")
        self.attributes: dict[str, str] = data.get("attributes", {})

    async def click(self) -> None:
        await self._page.evaluate(
            f"document.querySelector({self._page._js_str(self._data.get('selector', ''))}).click()"
        )

    async def inner_text(self) -> str:
        return await self._page.evaluate(
            f"document.querySelector({self._page._js_str(self._data.get('selector', ''))})?.innerText || ''"
        )

    def __repr__(self) -> str:
        return f"ElementHandle(tag={self.tag!r}, text={self.text!r})"


class Page:
    """A single browser tab — Playwright-compatible API."""

    def __init__(self, browser: Browser, tab_id: str):
        self._browser = browser
        self._transport: Transport = browser._transport
        self._tab_id = tab_id
        self._url: str = ""
        self._closed = False

    async def _ensure_active(self) -> None:
        """Auto-switch to this tab before any action."""
        if self._closed:
            raise NyxNotFound("Page has been closed")
        tabs = await self._browser.tabs()
        for t in tabs:
            tid = t.get("id", t.get("tab_id", ""))
            if tid == self._tab_id:
                if not t.get("active", False):
                    await self._browser.switch_tab(self._tab_id)
                return
        raise NyxNotFound(f"Tab {self._tab_id} no longer exists")

    @staticmethod
    def _js_str(s: str) -> str:
        """Escape a Python string for safe JS injection."""
        escaped = s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        return f"'{escaped}'"

    # ── Navigation ──

    async def goto(self, url: str, *, wait_until: str = "load", timeout: float = 30) -> None:
        await self._ensure_active()
        await self._transport.post(
            "/navigate", {"url": url, "timeout": int(timeout * 1000)},
            timeout=timeout + 5,
        )
        self._url = url

    async def go_back(self, *, timeout: float = 30) -> None:
        await self._ensure_active()
        await self._transport.post("/back", timeout=timeout)
        try:
            await self._transport.get(
                "/status",
                params={"wait": "navigation", "timeout": "3000"},
                timeout=5,
            )
        except NyxTimeout:
            pass
        snap_data = await self._transport.get("/snapshot")
        self._url = snap_data.get("url", self._url) if isinstance(snap_data, dict) else self._url

    async def go_forward(self, *, timeout: float = 30) -> None:
        await self._ensure_active()
        await self._transport.post("/forward", timeout=timeout)
        try:
            await self._transport.get(
                "/status",
                params={"wait": "navigation", "timeout": "3000"},
                timeout=5,
            )
        except NyxTimeout:
            pass
        snap_data = await self._transport.get("/snapshot")
        self._url = snap_data.get("url", self._url) if isinstance(snap_data, dict) else self._url

    async def reload(self, *, timeout: float = 30) -> None:
        url = self._url or (await self._get_current_url())
        if url:
            await self._ensure_active()
            await self._transport.post(
                "/navigate", {"url": url, "timeout": int(timeout * 1000)},
                timeout=timeout + 5,
            )

    async def _get_current_url(self) -> str:
        snap = await self._transport.get("/snapshot")
        if isinstance(snap, dict):
            self._url = snap.get("url", "")
        return self._url

    # ── Properties ──

    @property
    def url(self) -> str:
        return self._url

    async def title(self) -> str:
        await self._ensure_active()
        snap = await self._transport.get("/snapshot")
        if isinstance(snap, dict):
            self._url = snap.get("url", self._url)
            return snap.get("title", "")
        return ""

    async def content(self) -> str:
        await self._ensure_active()
        result = await self._transport.get("/page-html")
        if isinstance(result, dict):
            return result.get("html", "")
        if isinstance(result, bytes):
            return result.decode("utf-8", errors="replace")
        return str(result)

    # ── Interaction (CSS selector based) ──

    async def click(self, selector: str, *, timeout: float = 30) -> None:
        await self._ensure_active()
        data = await self._transport.post(
            "/act",
            {"action": "click", "target": f"css:{selector}"},
            timeout=timeout,
        )
        self._check_act_error(data)

    async def fill(self, selector: str, value: str, *, timeout: float = 30) -> None:
        await self._ensure_active()
        data = await self._transport.post(
            "/act",
            {"action": "fill", "target": f"css:{selector}", "value": value},
            timeout=timeout,
        )
        self._check_act_error(data)

    async def type(self, selector: str, text: str, *, delay: float = 0) -> None:
        await self._ensure_active()
        await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.focus()"
        )
        data = await self._transport.post(
            "/act",
            {"action": "fill", "target": f"css:{selector}", "value": text},
            timeout=30,
        )
        self._check_act_error(data)

    async def press(self, selector: str, key: str) -> None:
        await self._ensure_active()
        await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.dispatchEvent("
            f"new KeyboardEvent('keydown', {{key: {self._js_str(key)}, bubbles: true}}))"
        )

    async def select_option(self, selector: str, value: str) -> None:
        await self._ensure_active()
        data = await self._transport.post(
            "/act",
            {"action": "select", "target": f"css:{selector}", "value": value},
        )
        self._check_act_error(data)

    async def check(self, selector: str) -> None:
        is_checked = await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.checked"
        )
        if not is_checked:
            await self.click(selector)

    async def uncheck(self, selector: str) -> None:
        is_checked = await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.checked"
        )
        if is_checked:
            await self.click(selector)

    async def hover(self, selector: str) -> None:
        await self._ensure_active()
        await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.dispatchEvent("
            f"new MouseEvent('mouseover', {{bubbles: true}}))"
        )

    # ── Query ──

    async def query_selector(self, selector: str) -> ElementHandle | None:
        result = await self.evaluate(
            f"(() => {{ const el = document.querySelector({self._js_str(selector)}); "
            f"if (!el) return null; "
            f"return {{tag: el.tagName.toLowerCase(), text: el.innerText || '', "
            f"selector: {self._js_str(selector)}, "
            f"attributes: Object.fromEntries([...el.attributes].map(a => [a.name, a.value]))}}; }})()"
        )
        if result is None:
            return None
        return ElementHandle(self, result)

    async def query_selector_all(self, selector: str) -> list[ElementHandle]:
        result = await self.evaluate(
            f"[...document.querySelectorAll({self._js_str(selector)})].map((el, i) => ({{ "
            f"tag: el.tagName.toLowerCase(), text: el.innerText || '', "
            f"selector: {self._js_str(selector)} + ':nth-of-type(' + (i+1) + ')', "
            f"attributes: Object.fromEntries([...el.attributes].map(a => [a.name, a.value])) }}))"
        )
        if not result:
            return []
        return [ElementHandle(self, item) for item in result]

    def locator(self, selector: str) -> Locator:
        from nyx.locator import Locator
        return Locator(self, selector)

    # ── Content extraction ──

    async def inner_text(self, selector: str) -> str:
        result = await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.innerText || ''"
        )
        return result or ""

    async def inner_html(self, selector: str) -> str:
        result = await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.innerHTML || ''"
        )
        return result or ""

    async def text_content(self, selector: str) -> str | None:
        return await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.textContent"
        )

    async def get_attribute(self, selector: str, name: str) -> str | None:
        return await self.evaluate(
            f"document.querySelector({self._js_str(selector)})?.getAttribute({self._js_str(name)})"
        )

    async def is_visible(self, selector: str) -> bool:
        result = await self.evaluate(
            f"(() => {{ const el = document.querySelector({self._js_str(selector)}); "
            f"if (!el) return false; "
            f"const s = getComputedStyle(el); "
            f"return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0'; }})()"
        )
        return bool(result)

    async def is_hidden(self, selector: str) -> bool:
        return not await self.is_visible(selector)

    # ── JavaScript ──

    async def evaluate(self, expression: str, arg: Any = None) -> Any:
        await self._ensure_active()
        result = await self._transport.post(
            "/eval-js", {"script": f"return {expression}"}
        )
        if isinstance(result, dict):
            val = result.get("result")
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (ValueError, TypeError):
                    return val
            return val
        return result

    async def evaluate_handle(self, expression: str) -> Any:
        return await self.evaluate(expression)

    # ── Wait ──

    async def wait_for_selector(
        self, selector: str, *, state: str = "visible", timeout: float = 30
    ) -> ElementHandle | None:
        await self._ensure_active()
        try:
            await self._transport.post(
                "/wait",
                {"selector": selector, "timeout": int(timeout * 1000)},
                timeout=timeout + 2,
            )
        except Exception:
            raise NyxTimeout(f"Timeout waiting for selector: {selector}")
        return await self.query_selector(selector)

    async def wait_for_url(
        self, url: str | Pattern, *, timeout: float = 30  # type: ignore[type-arg]
    ) -> None:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            current = await self._get_current_url()
            if isinstance(url, str):
                if url in current:
                    return
            elif hasattr(url, "search"):
                if url.search(current):
                    return
            await asyncio.sleep(0.5)
        raise NyxTimeout(f"Timeout waiting for URL: {url}")

    async def wait_for_load_state(self, state: str = "load", *, timeout: float = 30) -> None:
        await self._ensure_active()
        try:
            await self._transport.get(
                "/status",
                params={"wait": "navigation", "timeout": str(int(timeout * 1000))},
                timeout=timeout + 2,
            )
        except NyxTimeout:
            pass

    async def wait_for_timeout(self, timeout: float) -> None:
        await asyncio.sleep(timeout / 1000)

    async def wait_for_function(self, expression: str, *, timeout: float = 30) -> Any:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            result = await self.evaluate(expression)
            if result:
                return result
            await asyncio.sleep(0.25)
        raise NyxTimeout(f"Timeout waiting for function: {expression}")

    # ── Screenshot ──

    async def screenshot(self, *, path: str | None = None, full_page: bool = False) -> bytes:
        await self._ensure_active()
        data = await self._transport.get_bytes("/screenshot")
        if path:
            with open(path, "wb") as f:
                f.write(data)
        return data

    # ── Lifecycle ──

    async def close(self) -> None:
        if not self._closed:
            try:
                await self._browser.close_tab(self._tab_id)
            except Exception:
                pass
            self._closed = True

    def is_closed(self) -> bool:
        return self._closed

    # ── Nyx-specific (not in Playwright — our unique value) ──

    async def snapshot(self, *, full: bool = False):
        await self._ensure_active()
        return await self._browser.snapshot(full=full)

    async def act(self, action: str, target: str | None = None, **kwargs):
        await self._ensure_active()
        return await self._browser.act(action, target, **kwargs)

    async def wait_for_challenge(self, *, timeout: float = 15) -> None:
        await self._ensure_active()
        await self._browser.wait_challenge(timeout=int(timeout * 1000))

    # ── Helpers ──

    @staticmethod
    def _check_act_error(data: Any) -> None:
        """Raise NyxNotFound if the act response contains an error."""
        if isinstance(data, dict) and data.get("act_error"):
            msg = data["act_error"]
            hints = data.get("did_you_mean", [])
            raise NyxNotFound(f"{msg} (did_you_mean: {hints})")

    def __repr__(self) -> str:
        state = "closed" if self._closed else self._url or "blank"
        return f"Page(tab={self._tab_id!r}, {state})"
