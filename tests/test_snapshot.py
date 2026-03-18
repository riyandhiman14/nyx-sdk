"""Unit tests for Snapshot class — fully offline."""

from nyx.browser import Snapshot


class TestSnapshotBasics:
    def test_url_and_title(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert snap.url == "https://example.com"
        assert snap.title == "Example Domain"

    def test_page_text(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert "Example Domain" in snap.page_text

    def test_scroll_y(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert snap.scroll_y == 0

    def test_has_more(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert snap.has_more is False

    def test_viewport_height(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert snap.viewport_height == 768

    def test_history(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert snap.history == ["https://example.com"]


class TestSnapshotElements:
    def test_flatten_finds_elements(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert len(snap.elements) == 5

    def test_find_by_text(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        el = snap.find("Example Domain")
        assert el is not None
        assert el["tag"] == "h1"

    def test_find_case_insensitive(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        el = snap.find("example domain")
        assert el is not None

    def test_find_not_found(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert snap.find("nonexistent text") is None

    def test_find_all(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        results = snap.find_all("Domain")
        assert len(results) >= 1

    def test_by_tag(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        links = snap.by_tag("a")
        assert len(links) == 1
        assert links[0]["text"] == "More information..."

    def test_inputs(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        inputs = snap.inputs()
        assert len(inputs) == 1
        assert inputs[0]["tag"] == "input"

    def test_links(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        links = snap.links()
        assert len(links) == 1

    def test_buttons(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        buttons = snap.buttons()
        assert len(buttons) == 1
        assert buttons[0]["text"] == "Submit"


class TestSnapshotErrors:
    def test_act_error(self, snapshot_with_error):
        snap = Snapshot(snapshot_with_error)
        assert snap.act_error == "Element not found: #missing"
        assert snap.did_you_mean == ["#content", "#main"]

    def test_no_error(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        assert snap.act_error is None
        assert snap.did_you_mean == []


class TestSnapshotDefaults:
    def test_empty_data(self):
        snap = Snapshot({})
        assert snap.url == ""
        assert snap.title == ""
        assert snap.elements == []
        assert snap.scroll_y == 0
        assert snap.has_more is False
        assert snap.act_error is None

    def test_repr(self, snapshot_data):
        snap = Snapshot(snapshot_data)
        r = repr(snap)
        assert "Snapshot(" in r
        assert "example.com" in r
        assert "Example Domain" in r


class TestSnapshotNestedTree:
    def test_nested_children(self):
        data = {
            "url": "https://test.com",
            "title": "Test",
            "tree": {
                "tag": "div",
                "children": [
                    {
                        "tag": "div",
                        "children": [
                            {
                                "tag": "button",
                                "action_id": "10",
                                "text": "Nested Button",
                                "children": [],
                            }
                        ],
                    }
                ],
            },
        }
        snap = Snapshot(data)
        assert len(snap.elements) == 1
        assert snap.elements[0]["text"] == "Nested Button"

    def test_text_collection_from_children(self):
        data = {
            "url": "https://test.com",
            "title": "Test",
            "tree": {
                "tag": "a",
                "action_id": "1",
                "children": [
                    {"text": "Click"},
                    {"text": "Here"},
                ],
            },
        }
        snap = Snapshot(data)
        assert len(snap.elements) == 1
        assert "Click" in snap.elements[0]["text"]
        assert "Here" in snap.elements[0]["text"]
