"""Unit tests for Page and Locator with mocked browser — fully offline."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nyx.page import Page, ElementHandle
from nyx.locator import Locator
from nyx.errors import NyxNotFound, NyxTimeout


@pytest.fixture
def mock_browser():
    browser = MagicMock()
    browser.host = "http://127.0.0.1:9999"
    browser.timeout = 15

    browser.tabs = AsyncMock(return_value=[
        {"id": "tab1", "active": True, "url": "about:blank"},
    ])
    browser.switch_tab = AsyncMock(return_value={})
    browser.close_tab = AsyncMock(return_value={})
    browser.new_tab = AsyncMock(return_value={"id": "tab2"})
    browser.screenshot = AsyncMock(return_value=b"\x89PNG fake image data")

    browser._get = AsyncMock(return_value={
        "url": "https://example.com",
        "title": "Example Domain",
        "tree": {},
    })
    browser._post = AsyncMock(return_value={
        "result": "test_value",
    })

    browser.snapshot = AsyncMock(return_value=MagicMock(
        url="https://example.com",
        title="Example Domain",
    ))
    browser.act = AsyncMock(return_value=MagicMock(
        url="https://example.com",
    ))
    browser.wait_challenge = AsyncMock(return_value={})

    return browser


@pytest.fixture
def page(mock_browser):
    return Page(mock_browser, "tab1")


class TestPageNavigation:
    @pytest.mark.asyncio
    async def test_goto(self, page, mock_browser):
        await page.goto("https://example.com")
        mock_browser._post.assert_called_with(
            "/navigate", {"url": "https://example.com"}, timeout=30
        )
        assert page.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_go_back(self, page, mock_browser):
        await page.go_back()
        mock_browser._post.assert_any_call("/back", None, timeout=30)

    @pytest.mark.asyncio
    async def test_go_forward(self, page, mock_browser):
        await page.go_forward()
        mock_browser._post.assert_any_call("/forward", None, timeout=30)


class TestPageProperties:
    @pytest.mark.asyncio
    async def test_title(self, page, mock_browser):
        title = await page.title()
        assert title == "Example Domain"

    @pytest.mark.asyncio
    async def test_url_property(self, page):
        page._url = "https://test.com"
        assert page.url == "https://test.com"

    @pytest.mark.asyncio
    async def test_content(self, page, mock_browser):
        mock_browser._post.return_value = {"html": "<html><body>Hello</body></html>"}
        html = await page.content()
        assert "<html>" in html


class TestPageInteraction:
    @pytest.mark.asyncio
    async def test_click(self, page, mock_browser):
        await page.click("button#submit")
        mock_browser._post.assert_called()

    @pytest.mark.asyncio
    async def test_fill(self, page, mock_browser):
        await page.fill("input#name", "John")
        mock_browser._post.assert_called()

    @pytest.mark.asyncio
    async def test_evaluate(self, page, mock_browser):
        mock_browser._post.return_value = {"result": "Example Domain"}
        result = await page.evaluate("document.title")
        assert result == "Example Domain"


class TestPageScreenshot:
    @pytest.mark.asyncio
    async def test_screenshot_returns_bytes(self, page, mock_browser):
        data = await page.screenshot()
        assert isinstance(data, bytes)

    @pytest.mark.asyncio
    async def test_screenshot_with_path(self, page, mock_browser, tmp_path):
        path = str(tmp_path / "test.png")
        data = await page.screenshot(path=path)
        assert isinstance(data, bytes)
        with open(path, "rb") as f:
            assert f.read() == data


class TestPageLifecycle:
    @pytest.mark.asyncio
    async def test_close(self, page, mock_browser):
        assert not page.is_closed()
        await page.close()
        assert page.is_closed()
        mock_browser.close_tab.assert_called_with("tab1")

    @pytest.mark.asyncio
    async def test_closed_page_raises(self, page):
        await page.close()
        with pytest.raises(NyxNotFound, match="closed"):
            await page.goto("https://example.com")

    def test_repr(self, page):
        page._url = "https://example.com"
        r = repr(page)
        assert "Page(" in r
        assert "tab1" in r


class TestPageWait:
    @pytest.mark.asyncio
    async def test_wait_for_timeout(self, page):
        # Just verify it doesn't raise — sleeps 10ms
        await page.wait_for_timeout(10)


class TestLocatorBasics:
    def test_locator_creation(self, page):
        loc = page.locator("div.content")
        assert isinstance(loc, Locator)
        assert loc._selector == "div.content"

    def test_locator_chaining(self, page):
        loc = page.locator("div").locator("span")
        assert loc._selector == "div span"

    def test_locator_first(self, page):
        loc = page.locator("li").first()
        assert "first-of-type" in loc._selector

    def test_locator_last(self, page):
        loc = page.locator("li").last()
        assert "last-of-type" in loc._selector

    def test_locator_nth(self, page):
        loc = page.locator("li").nth(2)
        assert "nth-of-type(3)" in loc._selector

    def test_locator_repr(self, page):
        loc = page.locator("div.test")
        assert "div.test" in repr(loc)

    def test_get_by_role(self, page):
        loc = page.locator("div").get_by_role("button", name="Submit")
        assert "role='button'" in loc._selector
        assert "Submit" in loc._selector


class TestLocatorActions:
    @pytest.mark.asyncio
    async def test_locator_click(self, page, mock_browser):
        loc = page.locator("button#go")
        await loc.click()
        mock_browser._post.assert_called()

    @pytest.mark.asyncio
    async def test_locator_fill(self, page, mock_browser):
        loc = page.locator("input#email")
        await loc.fill("test@example.com")
        mock_browser._post.assert_called()

    @pytest.mark.asyncio
    async def test_locator_inner_text(self, page, mock_browser):
        mock_browser._post.return_value = {"result": "Hello World"}
        loc = page.locator("h1")
        text = await loc.inner_text()
        assert text == "Hello World"

    @pytest.mark.asyncio
    async def test_locator_count(self, page, mock_browser):
        mock_browser._post.return_value = {"result": 3}
        loc = page.locator("li")
        count = await loc.count()
        assert count == 3


class TestElementHandle:
    def test_element_handle_attrs(self):
        page = MagicMock()
        eh = ElementHandle(page, {
            "tag": "button",
            "text": "Click me",
            "selector": "button",
            "attributes": {"class": "primary"},
        })
        assert eh.tag == "button"
        assert eh.text == "Click me"
        assert eh.attributes["class"] == "primary"

    def test_element_handle_repr(self):
        page = MagicMock()
        eh = ElementHandle(page, {"tag": "div", "text": "Hello"})
        assert "ElementHandle(" in repr(eh)
