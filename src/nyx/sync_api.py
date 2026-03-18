"""Synchronous API wrappers — matches Playwright's sync_api pattern."""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Pattern


def _run_sync(coro):
    """Run a coroutine synchronously using a background event loop."""
    if not hasattr(_run_sync, "_loop"):
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop.run_forever, daemon=True)
        thread.start()
        _run_sync._loop = loop
    return asyncio.run_coroutine_threadsafe(coro, _run_sync._loop).result()


class SyncLocator:
    """Sync wrapper for Locator."""

    def __init__(self, _async_locator):
        self._impl = _async_locator

    def click(self, *, timeout: float = 30) -> None:
        _run_sync(self._impl.click(timeout=timeout))

    def fill(self, value: str, *, timeout: float = 30) -> None:
        _run_sync(self._impl.fill(value, timeout=timeout))

    def type(self, text: str, *, delay: float = 0) -> None:
        _run_sync(self._impl.type(text, delay=delay))

    def press(self, key: str) -> None:
        _run_sync(self._impl.press(key))

    def select_option(self, value: str) -> None:
        _run_sync(self._impl.select_option(value))

    def check(self) -> None:
        _run_sync(self._impl.check())

    def uncheck(self) -> None:
        _run_sync(self._impl.uncheck())

    def hover(self) -> None:
        _run_sync(self._impl.hover())

    def inner_text(self, *, timeout: float = 30) -> str:
        return _run_sync(self._impl.inner_text(timeout=timeout))

    def inner_html(self, *, timeout: float = 30) -> str:
        return _run_sync(self._impl.inner_html(timeout=timeout))

    def text_content(self, *, timeout: float = 30) -> str | None:
        return _run_sync(self._impl.text_content(timeout=timeout))

    def get_attribute(self, name: str, *, timeout: float = 30) -> str | None:
        return _run_sync(self._impl.get_attribute(name, timeout=timeout))

    def is_visible(self, *, timeout: float = 30) -> bool:
        return _run_sync(self._impl.is_visible(timeout=timeout))

    def is_hidden(self, *, timeout: float = 30) -> bool:
        return _run_sync(self._impl.is_hidden(timeout=timeout))

    def screenshot(self, *, path: str | None = None) -> bytes:
        return _run_sync(self._impl.screenshot(path=path))

    def count(self) -> int:
        return _run_sync(self._impl.count())

    def all(self) -> list[SyncLocator]:
        return [SyncLocator(loc) for loc in _run_sync(self._impl.all())]

    def first(self) -> SyncLocator:
        return SyncLocator(self._impl.first())

    def last(self) -> SyncLocator:
        return SyncLocator(self._impl.last())

    def nth(self, index: int) -> SyncLocator:
        return SyncLocator(self._impl.nth(index))

    def locator(self, selector: str) -> SyncLocator:
        return SyncLocator(self._impl.locator(selector))

    def wait_for(self, *, state: str = "visible", timeout: float = 30) -> None:
        _run_sync(self._impl.wait_for(state=state, timeout=timeout))

    def __repr__(self) -> str:
        return f"SyncLocator({self._impl._selector!r})"


class SyncPage:
    """Sync wrapper for Page."""

    def __init__(self, _async_page):
        self._impl = _async_page

    # ── Navigation ──

    def goto(self, url: str, *, wait_until: str = "load", timeout: float = 30) -> None:
        _run_sync(self._impl.goto(url, wait_until=wait_until, timeout=timeout))

    def go_back(self, *, timeout: float = 30) -> None:
        _run_sync(self._impl.go_back(timeout=timeout))

    def go_forward(self, *, timeout: float = 30) -> None:
        _run_sync(self._impl.go_forward(timeout=timeout))

    def reload(self, *, timeout: float = 30) -> None:
        _run_sync(self._impl.reload(timeout=timeout))

    # ── Properties ──

    @property
    def url(self) -> str:
        return self._impl.url

    def title(self) -> str:
        return _run_sync(self._impl.title())

    def content(self) -> str:
        return _run_sync(self._impl.content())

    # ── Interaction ──

    def click(self, selector: str, *, timeout: float = 30) -> None:
        _run_sync(self._impl.click(selector, timeout=timeout))

    def fill(self, selector: str, value: str, *, timeout: float = 30) -> None:
        _run_sync(self._impl.fill(selector, value, timeout=timeout))

    def type(self, selector: str, text: str, *, delay: float = 0) -> None:
        _run_sync(self._impl.type(selector, text, delay=delay))

    def press(self, selector: str, key: str) -> None:
        _run_sync(self._impl.press(selector, key))

    def select_option(self, selector: str, value: str) -> None:
        _run_sync(self._impl.select_option(selector, value))

    def check(self, selector: str) -> None:
        _run_sync(self._impl.check(selector))

    def uncheck(self, selector: str) -> None:
        _run_sync(self._impl.uncheck(selector))

    def hover(self, selector: str) -> None:
        _run_sync(self._impl.hover(selector))

    # ── Query ──

    def query_selector(self, selector: str):
        return _run_sync(self._impl.query_selector(selector))

    def query_selector_all(self, selector: str) -> list:
        return _run_sync(self._impl.query_selector_all(selector))

    def locator(self, selector: str) -> SyncLocator:
        return SyncLocator(self._impl.locator(selector))

    # ── Content extraction ──

    def inner_text(self, selector: str) -> str:
        return _run_sync(self._impl.inner_text(selector))

    def inner_html(self, selector: str) -> str:
        return _run_sync(self._impl.inner_html(selector))

    def text_content(self, selector: str) -> str | None:
        return _run_sync(self._impl.text_content(selector))

    def get_attribute(self, selector: str, name: str) -> str | None:
        return _run_sync(self._impl.get_attribute(selector, name))

    def is_visible(self, selector: str) -> bool:
        return _run_sync(self._impl.is_visible(selector))

    def is_hidden(self, selector: str) -> bool:
        return _run_sync(self._impl.is_hidden(selector))

    # ── JavaScript ──

    def evaluate(self, expression: str, arg: Any = None) -> Any:
        return _run_sync(self._impl.evaluate(expression, arg))

    # ── Wait ──

    def wait_for_selector(self, selector: str, *, state: str = "visible", timeout: float = 30):
        return _run_sync(self._impl.wait_for_selector(selector, state=state, timeout=timeout))

    def wait_for_url(self, url: str, *, timeout: float = 30) -> None:
        _run_sync(self._impl.wait_for_url(url, timeout=timeout))

    def wait_for_load_state(self, state: str = "load", *, timeout: float = 30) -> None:
        _run_sync(self._impl.wait_for_load_state(state, timeout=timeout))

    def wait_for_timeout(self, timeout: float) -> None:
        _run_sync(self._impl.wait_for_timeout(timeout))

    def wait_for_function(self, expression: str, *, timeout: float = 30) -> Any:
        return _run_sync(self._impl.wait_for_function(expression, timeout=timeout))

    # ── Screenshot ──

    def screenshot(self, *, path: str | None = None, full_page: bool = False) -> bytes:
        return _run_sync(self._impl.screenshot(path=path, full_page=full_page))

    # ── Lifecycle ──

    def close(self) -> None:
        _run_sync(self._impl.close())

    def is_closed(self) -> bool:
        return self._impl.is_closed()

    # ── Nyx-specific ──

    def snapshot(self, *, full: bool = False):
        return _run_sync(self._impl.snapshot(full=full))

    def act(self, action: str, target: str | None = None, **kwargs):
        return _run_sync(self._impl.act(action, target, **kwargs))

    def wait_for_challenge(self, *, timeout: float = 15) -> None:
        _run_sync(self._impl.wait_for_challenge(timeout=timeout))

    def __repr__(self) -> str:
        return f"Sync{self._impl!r}"


class SyncBrowser:
    """Sync wrapper for Browser."""

    def __init__(self, _async_browser):
        self._impl = _async_browser

    @classmethod
    def launch(
        cls,
        *,
        headless: bool = True,
        proxy: str | None = None,
        timeout: float = 30,
        version: str | None = None,
        auto_install: bool = True,
        extra_args: list[str] | None = None,
    ) -> SyncBrowser:
        from nyx.browser import Browser
        browser = _run_sync(Browser.launch(
            headless=headless, proxy=proxy, timeout=timeout,
            version=version, auto_install=auto_install,
            extra_args=extra_args,
        ))
        return cls(browser)

    @classmethod
    def connect(cls, host: str = "http://localhost:8765", *, timeout: float = 30) -> SyncBrowser:
        from nyx.browser import Browser
        browser = _run_sync(Browser.connect(host, timeout=timeout))
        return cls(browser)

    def new_page(self) -> SyncPage:
        page = _run_sync(self._impl.new_page())
        return SyncPage(page)

    @property
    def pages(self) -> list[SyncPage]:
        async_pages = _run_sync(self._impl._get_pages())
        return [SyncPage(p) for p in async_pages]

    def close(self) -> None:
        _run_sync(self._impl.close())

    def __enter__(self) -> SyncBrowser:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # Backward-compat delegates
    def goto(self, url: str):
        return _run_sync(self._impl.goto(url))

    def click(self, target: str):
        return _run_sync(self._impl.click(target))

    def fill(self, target: str, value: str):
        return _run_sync(self._impl.fill(target, value))

    def snapshot(self, *, full: bool = False):
        return _run_sync(self._impl.snapshot(full=full))

    def screenshot(self, path: str | None = None) -> bytes:
        return _run_sync(self._impl.screenshot(path=path))

    def tabs(self) -> list:
        return _run_sync(self._impl.tabs())

    def new_tab(self, url: str | None = None) -> dict:
        return _run_sync(self._impl.new_tab(url))

    def switch_tab(self, tab_id: str) -> dict:
        return _run_sync(self._impl.switch_tab(tab_id))

    def close_tab(self, tab_id: str) -> dict:
        return _run_sync(self._impl.close_tab(tab_id))

    def __repr__(self) -> str:
        return f"Sync{self._impl!r}"


class SyncAgentBrowser:
    """Sync wrapper for AgentBrowser."""

    def __init__(self, _async_agent):
        self._impl = _async_agent

    @classmethod
    def launch(
        cls,
        *,
        headless: bool = True,
        proxy: str | None = None,
        timeout: float = 30,
        version: str | None = None,
        auto_install: bool = True,
        extra_args: list[str] | None = None,
    ) -> SyncAgentBrowser:
        from nyx.agent import AgentBrowser
        agent = _run_sync(AgentBrowser.launch(
            headless=headless, proxy=proxy, timeout=timeout,
            version=version, auto_install=auto_install,
            extra_args=extra_args,
        ))
        return cls(agent)

    @classmethod
    def connect(cls, host: str = "http://localhost:8765", *,
                timeout: float = 30) -> SyncAgentBrowser:
        from nyx.agent import AgentBrowser
        agent = _run_sync(AgentBrowser.connect(host, timeout=timeout))
        return cls(agent)

    def close(self) -> None:
        _run_sync(self._impl.close())

    def __enter__(self) -> SyncAgentBrowser:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def snapshot(self, *, full: bool = False):
        return _run_sync(self._impl.snapshot(full=full))

    def act(self, action: str, target: str | None = None, **kwargs):
        return _run_sync(self._impl.act(action, target, **kwargs))

    def act_sequence(self, steps: list[dict]):
        return _run_sync(self._impl.act_sequence(steps))

    def navigate(self, url: str, timeout: int = 15000) -> dict:
        return _run_sync(self._impl.navigate(url, timeout))

    def text(self) -> str:
        return _run_sync(self._impl.text())

    def page_html(self) -> str:
        return _run_sync(self._impl.page_html())

    def eval_js(self, script: str) -> Any:
        return _run_sync(self._impl.eval_js(script))

    def screenshot(self, path: str | None = None) -> bytes:
        return _run_sync(self._impl.screenshot(path))

    def status(self, *, wait: str | None = None, timeout: int | None = None) -> dict:
        return _run_sync(self._impl.status(wait=wait, timeout=timeout))

    def wait_for(self, selector: str, timeout: int = 5000) -> dict:
        return _run_sync(self._impl.wait_for(selector, timeout))

    def wait_challenge(self, timeout: int = 15000) -> dict:
        return _run_sync(self._impl.wait_challenge(timeout))

    def back(self) -> dict:
        return _run_sync(self._impl.back())

    def forward(self) -> dict:
        return _run_sync(self._impl.forward())

    def tabs(self) -> list:
        return _run_sync(self._impl.tabs())

    def new_tab(self, url: str | None = None) -> dict:
        return _run_sync(self._impl.new_tab(url))

    def switch_tab(self, tab_id: str) -> dict:
        return _run_sync(self._impl.switch_tab(tab_id))

    def close_tab(self, tab_id: str) -> dict:
        return _run_sync(self._impl.close_tab(tab_id))

    def media(self) -> dict:
        return _run_sync(self._impl.media())

    def reset(self, url: str | None = None) -> dict:
        return _run_sync(self._impl.reset(url))

    def session_create(self, **config) -> dict:
        return _run_sync(self._impl.session_create(**config))

    def session_status(self) -> dict:
        return _run_sync(self._impl.session_status())

    def session_destroy(self) -> dict:
        return _run_sync(self._impl.session_destroy())

    def session_health(self) -> dict:
        return _run_sync(self._impl.session_health())

    def __repr__(self) -> str:
        return f"Sync{self._impl!r}"
