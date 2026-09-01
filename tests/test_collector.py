import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.ingest.collect import EASTERN, expand_occurrences, normalize, parse_ics


class CollectorTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).parent / "fixtures" / "sample.ics"
        self.events = parse_ics(fixture.read_text(encoding="utf-8"))
        self.raw = self.events[0]

    def test_parses_folded_calendar_event(self):
        self.assertEqual(self.raw["SUMMARY"], "Franklinton Family Storytime")

    def test_normalizes_age_location_and_timezone(self):
        event = normalize(self.raw, "Official Library", "https://example.gov/calendar", "2026-09-01T00:00:00Z")
        self.assertEqual((event["ageMin"], event["ageMax"]), (0.0, 5.0))
        self.assertEqual(event["town"], "Franklinton, NC")
        self.assertEqual(event["start"], "2026-09-16T10:30:00-04:00")

    def test_recurring_events_expand_to_distinct_occurrences(self):
        end = datetime(2026, 10, 1, tzinfo=EASTERN)
        occurrences = expand_occurrences(self.events[1], end)
        self.assertEqual(len(occurrences), 3)
        normalized = [normalize(item, "Official Library", "https://example.gov/calendar", "2026-09-01T00:00:00Z") for item in occurrences]
        self.assertEqual(len({event["id"] for event in normalized}), 3)


if __name__ == "__main__":
    unittest.main()
