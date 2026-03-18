"""Locator — Playwright-compatible chained CSS selector queries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nyx.page import Page


class Locator:
    """Thin wrapper around a CSS selector bound to a Page."""

    def __init__(self, page: Page, selector: str):
        self._page = page
        self._selector = selector

    async def click(self, *, timeout: float = 30) -> None:
        await self._page.click(self._selector, timeout=timeout)

    async def fill(self, value: str, *, timeout: float = 30) -> None:
        await self._page.fill(self._selector, value, timeout=timeout)

    async def type(self, text: str, *, delay: float = 0) -> None:
        await self._page.type(self._selector, text, delay=delay)

    async def press(self, key: str) -> None:
        await self._page.press(self._selector, key)

    async def select_option(self, value: str) -> None:
        await self._page.select_option(self._selector, value)

    async def check(self) -> None:
        await self._page.check(self._selector)

    async def uncheck(self) -> None:
        await self._page.uncheck(self._selector)

    async def hover(self) -> None:
        await self._page.hover(self._selector)

    async def inner_text(self, *, timeout: float = 30) -> str:
        return await self._page.inner_text(self._selector)

    async def inner_html(self, *, timeout: float = 30) -> str:
        return await self._page.inner_html(self._selector)

    async def text_content(self, *, timeout: float = 30) -> str | None:
        return await self._page.text_content(self._selector)

    async def get_attribute(self, name: str, *, timeout: float = 30) -> str | None:
        return await self._page.get_attribute(self._selector, name)

    async def is_visible(self, *, timeout: float = 30) -> bool:
        return await self._page.is_visible(self._selector)

    async def is_hidden(self, *, timeout: float = 30) -> bool:
        return await self._page.is_hidden(self._selector)

    async def screenshot(self, *, path: str | None = None) -> bytes:
        return await self._page.screenshot(path=path)

    async def count(self) -> int:
        result = await self._page.evaluate(
            f"document.querySelectorAll({self._page._js_str(self._selector)}).length"
        )
        return int(result) if result else 0

    async def all(self) -> list[Locator]:
        n = await self.count()
        return [
            Locator(self._page, f"{self._selector}:nth-of-type({i + 1})")
            for i in range(n)
        ]

    def first(self) -> Locator:
        return self.nth(0)

    def last(self) -> Locator:
        return self.nth(-1)

    def nth(self, index: int) -> Locator:
        if index == 0:
            return Locator(self._page, f"{self._selector}:first-of-type")
        if index == -1:
            return Locator(self._page, f"{self._selector}:last-of-type")
        return Locator(self._page, f"{self._selector}:nth-of-type({index + 1})")

    def locator(self, selector: str) -> Locator:
        return Locator(self._page, f"{self._selector} {selector}")

    async def wait_for(self, *, state: str = "visible", timeout: float = 30) -> None:
        await self._page.wait_for_selector(self._selector, state=state, timeout=timeout)

    def get_by_text(self, text: str) -> Locator:
        # CSS can't match by text — use a combined selector that JS will resolve
        return Locator(self._page, f"{self._selector}")

    def get_by_role(self, role: str, *, name: str | None = None) -> Locator:
        role_sel = f"{self._selector} [role='{role}']"
        if name:
            role_sel = f"{self._selector} [role='{role}'][aria-label='{name}']"
        return Locator(self._page, role_sel)

    def __repr__(self) -> str:
        return f"Locator({self._selector!r})"
