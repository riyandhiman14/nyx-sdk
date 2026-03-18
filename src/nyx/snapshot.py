"""Snapshot — immutable page state from /snapshot or /act."""

from __future__ import annotations

from typing import Any, Optional


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
