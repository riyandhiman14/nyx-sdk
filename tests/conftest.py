"""Shared fixtures for Nyx tests."""

import pytest


@pytest.fixture
def snapshot_data():
    """Sample snapshot data for unit tests."""
    return {
        "url": "https://example.com",
        "title": "Example Domain",
        "tree": {
            "tag": "body",
            "children": [
                {
                    "tag": "h1",
                    "action_id": "1",
                    "text": "Example Domain",
                    "children": [],
                },
                {
                    "tag": "p",
                    "action_id": "2",
                    "text": "This domain is for use in illustrative examples.",
                    "children": [],
                },
                {
                    "tag": "a",
                    "action_id": "3",
                    "text": "More information...",
                    "attributes": {"href": "https://www.iana.org/domains/example"},
                    "children": [],
                },
                {
                    "tag": "input",
                    "action_id": "4",
                    "text": "",
                    "attributes": {"type": "text", "name": "q"},
                    "children": [],
                },
                {
                    "tag": "button",
                    "action_id": "5",
                    "text": "Submit",
                    "children": [],
                },
            ],
        },
        "scroll_y": 0,
        "has_more": False,
        "viewport_height": 768,
        "page_text": "Example Domain\nThis domain is for use in illustrative examples.",
        "history": ["https://example.com"],
    }


@pytest.fixture
def snapshot_with_error():
    """Snapshot data with an act_error."""
    return {
        "url": "https://example.com",
        "title": "Example Domain",
        "tree": {},
        "act_error": "Element not found: #missing",
        "did_you_mean": ["#content", "#main"],
    }


@pytest.fixture
def response_data():
    """Sample response components for unit tests."""
    return {
        "status_code": 200,
        "headers": {
            "content-type": "text/html; charset=utf-8",
            "server": "nginx",
            "x-request-id": "abc123",
        },
        "body": b"<html><body><h1>Hello</h1></body></html>",
        "url": "https://example.com",
    }
