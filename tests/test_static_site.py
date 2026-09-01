import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.buttons = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "button":
            self.buttons.append(values)
        if tag == "a":
            self.links.append(values)


class StaticSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.parser = PageParser()
        cls.parser.feed(cls.html)

    def test_required_controls_exist(self):
        required = {"ageRange", "distanceRange", "startDate", "endDate", "costFilter", "settingFilter", "registrationFilter", "includeUnknownAge", "sourceFreshness", "customDateError"}
        self.assertFalse(required - self.parser.ids)

    def test_toggle_buttons_expose_pressed_state(self):
        toggles = [button for button in self.parser.buttons if "data-date" in button or "data-category" in button]
        self.assertTrue(toggles)
        self.assertTrue(all("aria-pressed" in button for button in toggles))

    def test_external_links_are_protected(self):
        blank_links = [link for link in self.parser.links if link.get("target") == "_blank"]
        self.assertTrue(all("noopener" in link.get("rel", "") and "noreferrer" in link.get("rel", "") for link in blank_links))

    def test_dynamic_event_text_is_escaped(self):
        self.assertIn("escapeHtml(event.title)", self.js)
        self.assertIn("safeUrl(event.sourceUrl)", self.js)
        self.assertIn("source.lastSuccessfulRefresh", self.js)
        self.assertIn("controlsBound", self.js)


if __name__ == "__main__":
    unittest.main()
