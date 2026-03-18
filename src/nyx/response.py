"""Response object returned by Nyx requests."""

from __future__ import annotations
import json as _json


class Response:
    """HTTP response from an Aegis request.

    Attributes:
        status_code:  HTTP status code (200, 404, etc.).
        headers:      Dict of response headers.
        body:         Raw response body as bytes.
        url:          Final URL after redirects.
        ok:           True if status is 2xx.
    """

    def __init__(self, status_code: int, headers: dict[str, str],
                 body: bytes, url: str):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.url = url

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def text(self) -> str:
        """Decode body as UTF-8 text."""
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        """Parse body as JSON."""
        return _json.loads(self.body)

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "")

    def raise_for_status(self):
        """Raise NyxError if status is 4xx/5xx."""
        if self.status_code >= 400:
            from nyx.errors import NyxError
            raise NyxError(f"HTTP {self.status_code}: {self.url}")

    def __repr__(self) -> str:
        return f"Response(status={self.status_code}, url={self.url!r}, size={len(self.body)})"
