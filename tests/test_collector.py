import unittest
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import scripts.ingest.collect as collector
from scripts.ingest.collect import EASTERN, add_event, expand_occurrences, normalize, parse_ics


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

    def test_cancelled_status_is_preserved(self):
        raw = dict(self.raw, STATUS="CANCELLED")
        event = normalize(raw, "Official Library", "https://example.gov/calendar", "2026-09-01T00:00:00Z")
        self.assertEqual(event["status"], "cancelled")

    def test_registration_tri_state_prefers_negative_wording(self):
        not_required = dict(self.raw, DESCRIPTION="No registration required for this family event.")
        required = dict(self.raw, DESCRIPTION="Registration is required for this family event.")
        unknown = dict(self.raw, DESCRIPTION="A family event.")
        normalize_event = lambda item: normalize(item, "Official Library", "https://example.gov/calendar", "2026-09-01T00:00:00Z")
        self.assertEqual(normalize_event(not_required)["registrationRequired"], "false")
        self.assertEqual(normalize_event(required)["registrationRequired"], "true")
        self.assertEqual(normalize_event(unknown)["registrationRequired"], "unknown")

    def test_adult_only_event_is_rejected(self):
        raw = dict(self.raw, SUMMARY="Adult Crafternoon", DESCRIPTION="A craft program for adults.")
        self.assertIsNone(normalize(raw, "Official Library", "https://example.gov/calendar", "2026-09-01T00:00:00Z"))

    def test_explicit_teen_event_is_classified(self):
        raw = dict(self.raw, SUMMARY="Teen Time", DESCRIPTION="A program for teens.")
        event = normalize(raw, "Official Library", "https://example.gov/calendar", "2026-09-01T00:00:00Z")
        self.assertEqual(event["audienceGroup"], "teen")

    def test_unsupported_recurrence_is_rejected(self):
        raw = dict(self.events[1], RRULE="FREQ=WEEKLY;BYDAY=MO,WE")
        with self.assertRaises(ValueError):
            expand_occurrences(raw, datetime(2026, 10, 1, tzinfo=EASTERN))

    def test_unsupported_monthly_recurrence_is_rejected(self):
        raw = dict(self.events[1], RRULE="FREQ=MONTHLY;COUNT=3")
        with self.assertRaises(ValueError):
            expand_occurrences(raw, datetime(2026, 12, 1, tzinfo=EASTERN))

    def test_exact_cross_source_duplicate_retains_attribution(self):
        first = normalize(self.raw, "County Library", "https://one.example.gov/calendar", "2026-09-01T00:00:00Z")
        second = normalize(self.raw, "Town Calendar", "https://two.example.gov/calendar", "2026-09-01T00:00:00Z")
        collected = {}
        add_event(collected, first)
        add_event(collected, second)
        add_event(collected, second)
        self.assertEqual(len(collected), 1)
        self.assertEqual(len(collected[first["id"]]["additionalSources"]), 1)
        self.assertEqual(collected[first["id"]]["additionalSources"][0]["sourceName"], "Town Calendar")

    def test_same_url_with_different_source_name_is_retained_once(self):
        first = normalize(self.raw, "County Library", "https://example.gov/calendar", "2026-09-01T00:00:00Z")
        second = dict(first, sourceName="Town Calendar")
        collected = {}
        add_event(collected, first)
        add_event(collected, second)
        add_event(collected, second)
        self.assertEqual(collected[first["id"]]["additionalSources"], [{"sourceName": "Town Calendar", "sourceUrl": first["sourceUrl"]}])

    def test_failed_source_retains_last_known_good_events_and_freshness(self):
        prior_event = normalize(self.raw, "Official Library", "https://example.gov/calendar", "2026-09-01T00:00:00Z")
        prior = {"events": [prior_event], "sources": [{"sourceName": "Official Library", "lastSuccessfulRefresh": "2026-09-01T00:00:00Z", "status": "fresh"}]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "events.json"
            output.write_text(json.dumps(prior), encoding="utf-8")
            with patch.object(collector, "OUTPUT", output), patch.object(collector, "FEEDS", [("Official Library", "https://example.gov/feed", "https://example.gov/calendar")]), patch.object(collector, "fetch", return_value="not a calendar"):
                result = collector.collect(datetime(2026, 9, 1, tzinfo=timezone.utc))
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["sources"][0]["status"], "stale")
        self.assertTrue(result["sourceFailures"][0]["usingLastKnownGood"])

    def test_failed_secondary_source_keeps_its_attribution(self):
        prior_event = normalize(self.raw, "Primary Calendar", "https://primary.example.gov/calendar", "2026-09-01T00:00:00Z")
        prior_event["additionalSources"] = [{"sourceName": "Secondary Calendar", "sourceUrl": "https://secondary.example.gov/calendar"}]
        prior = {"events": [prior_event], "sources": [
            {"sourceName": "Primary Calendar", "lastSuccessfulRefresh": "2026-09-01T00:00:00Z", "status": "fresh"},
            {"sourceName": "Secondary Calendar", "lastSuccessfulRefresh": "2026-09-01T00:00:00Z", "status": "fresh"},
        ]}
        fixture_text = (Path(__file__).parent / "fixtures" / "sample.ics").read_text(encoding="utf-8")
        feeds = [
            ("Primary Calendar", "https://primary.example.gov/feed", "https://primary.example.gov/calendar"),
            ("Secondary Calendar", "https://secondary.example.gov/feed", "https://secondary.example.gov/calendar"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "events.json"
            output.write_text(json.dumps(prior), encoding="utf-8")
            with patch.object(collector, "OUTPUT", output), patch.object(collector, "FEEDS", feeds), patch.object(collector, "fetch", side_effect=[fixture_text, "not a calendar"]):
                result = collector.collect(datetime(2026, 9, 1, tzinfo=timezone.utc))
        matching = next(event for event in result["events"] if event["id"] == prior_event["id"])
        self.assertEqual(len(matching["additionalSources"]), 1)
        self.assertEqual(matching["additionalSources"][0]["sourceName"], "Secondary Calendar")


if __name__ == "__main__":
    unittest.main()
