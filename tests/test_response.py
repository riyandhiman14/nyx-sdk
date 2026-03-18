"""Unit tests for Response class — fully offline."""

import pytest

from nyx.response import Response
from nyx.errors import NyxError


class TestResponseBasics:
    def test_status_code(self, response_data):
        resp = Response(**response_data)
        assert resp.status_code == 200

    def test_ok(self, response_data):
        resp = Response(**response_data)
        assert resp.ok is True

    def test_not_ok(self, response_data):
        response_data["status_code"] = 404
        resp = Response(**response_data)
        assert resp.ok is False

    def test_url(self, response_data):
        resp = Response(**response_data)
        assert resp.url == "https://example.com"

    def test_headers(self, response_data):
        resp = Response(**response_data)
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert resp.headers["server"] == "nginx"

    def test_content_type(self, response_data):
        resp = Response(**response_data)
        assert "text/html" in resp.content_type


class TestResponseBody:
    def test_body_bytes(self, response_data):
        resp = Response(**response_data)
        assert isinstance(resp.body, bytes)
        assert b"<h1>Hello</h1>" in resp.body

    def test_text(self, response_data):
        resp = Response(**response_data)
        assert "<h1>Hello</h1>" in resp.text

    def test_json(self):
        resp = Response(
            status_code=200,
            headers={"content-type": "application/json"},
            body=b'{"key": "value", "count": 42}',
            url="https://api.example.com",
        )
        data = resp.json()
        assert data["key"] == "value"
        assert data["count"] == 42

    def test_json_invalid(self, response_data):
        resp = Response(**response_data)
        with pytest.raises(Exception):
            resp.json()


class TestResponseRaiseForStatus:
    def test_success_no_raise(self, response_data):
        resp = Response(**response_data)
        resp.raise_for_status()  # should not raise

    def test_client_error(self, response_data):
        response_data["status_code"] = 404
        resp = Response(**response_data)
        with pytest.raises(NyxError, match="HTTP 404"):
            resp.raise_for_status()

    def test_server_error(self, response_data):
        response_data["status_code"] = 500
        resp = Response(**response_data)
        with pytest.raises(NyxError, match="HTTP 500"):
            resp.raise_for_status()


class TestResponseRepr:
    def test_repr(self, response_data):
        resp = Response(**response_data)
        r = repr(resp)
        assert "Response(" in r
        assert "200" in r
        assert "example.com" in r
