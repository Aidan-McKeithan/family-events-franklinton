import json
import unittest
from pathlib import Path

from scripts.validate_events import validate


ROOT = Path(__file__).parents[1]


class EventDataTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "public" / "data" / "events.json").read_text(encoding="utf-8"))

    def test_dataset_is_valid(self):
        validate(self.data)

    def test_seed_data_has_toddler_match(self):
        matches = [event for event in self.data["events"] if not (event["ageMin"] is None and event["ageMax"] is None) and (event["ageMin"] is None or event["ageMin"] <= 2.5) and (event["ageMax"] is None or 2.5 <= event["ageMax"])]
        self.assertTrue(matches)

    def test_every_event_has_official_https_source(self):
        self.assertTrue(all(event["sourceUrl"].startswith("https://") for event in self.data["events"]))


if __name__ == "__main__":
    unittest.main()
