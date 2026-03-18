"""Shared HTTP transport layer for the AgentServer REST API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from nyx.errors import NyxConnectionError, NyxNotFound, NyxTimeout


class Transport:
    """HTTP client for the AgentServer REST API.

    Single source of truth for HTTP communication. Both Browser and
    AgentBrowser use this instead of duplicating request logic.
    """

    def __init__(self, host: str, *, timeout: float = 30):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def get(self, path: str, *, params: dict | None = None,
                  timeout: float | None = None) -> Any:
        """GET request. Returns parsed JSON or raw bytes."""
        session = self._get_session()
        t = aiohttp.ClientTimeout(total=timeout or self.timeout)
        try:
            async with session.get(
                f"{self.host}{path}", params=params, timeout=t
            ) as r:
                return await self._handle_response(r, path)
        except asyncio.TimeoutError as e:
            raise NyxTimeout(f"GET {path} timed out") from e
        except aiohttp.ClientError as e:
            raise NyxConnectionError(f"GET {path} failed: {e}") from e

    async def post(self, path: str, body: dict | None = None, *,
                   timeout: float | None = None) -> Any:
        """POST request. Returns parsed JSON or raw bytes."""
        session = self._get_session()
        t = aiohttp.ClientTimeout(total=timeout or self.timeout)
        try:
            async with session.post(
                f"{self.host}{path}", json=body or {}, timeout=t
            ) as r:
                return await self._handle_response(r, path)
        except asyncio.TimeoutError as e:
            raise NyxTimeout(f"POST {path} timed out") from e
        except aiohttp.ClientError as e:
            raise NyxConnectionError(f"POST {path} failed: {e}") from e

    async def get_bytes(self, path: str) -> bytes:
        """GET request returning raw bytes (for /screenshot)."""
        session = self._get_session()
        try:
            async with session.get(f"{self.host}{path}") as r:
                r.raise_for_status()
                return await r.read()
        except aiohttp.ClientError as e:
            raise NyxConnectionError(f"GET {path} failed: {e}") from e

    async def wait_ready(self, timeout: float = 30) -> None:
        """Poll /status until 200."""
        deadline = asyncio.get_event_loop().time() + timeout
        session = self._get_session()

        while asyncio.get_event_loop().time() < deadline:
            try:
                async with session.get(
                    f"{self.host}/status",
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as r:
                    if r.status == 200:
                        return
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
                pass
            await asyncio.sleep(1)

        raise NyxConnectionError(
            f"Nyx Browser not responding at {self.host}"
        )

    async def close(self) -> None:
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @staticmethod
    async def _handle_response(r: aiohttp.ClientResponse, path: str) -> Any:
        """Parse response, mapping HTTP errors to Nyx exceptions."""
        if r.status == 404:
            text = await r.text()
            raise NyxNotFound(f"{path}: {text}")
        if r.status == 400:
            try:
                data = await r.json()
                msg = data.get("error", str(data))
            except Exception:
                msg = await r.text()
            raise NyxConnectionError(f"{path}: {msg}")
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "json" in ct:
            return await r.json()
        return await r.read()
