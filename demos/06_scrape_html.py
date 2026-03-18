"""
Demo 06: Scrape HTML — fetch a page and extract data.

Uses Nyx for the HTTP request (stealth), standard html.parser for extraction.
"""

from html.parser import HTMLParser
from nyx import Nyx


class LinkExtractor(HTMLParser):
    """Simple link extractor — no external deps needed."""
    def __init__(self):
        super().__init__()
        self.links = []
        self._in_a = False
        self._href = ""
        self._text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_a = True
            self._text = ""
            for name, val in attrs:
                if name == "href":
                    self._href = val or ""

    def handle_data(self, data):
        if self._in_a:
            self._text += data

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            self._in_a = False
            if self._href and self._text.strip():
                self.links.append((self._text.strip(), self._href))


client = Nyx()
resp = client.get("https://news.ycombinator.com")

print(f"Status: {resp.status_code}")
print(f"Page size: {len(resp.body)} bytes\n")

parser = LinkExtractor()
parser.feed(resp.text)

print(f"Found {len(parser.links)} links:\n")
for text, href in parser.links[:20]:
    print(f"  {text[:60]:<60s} {href}")
