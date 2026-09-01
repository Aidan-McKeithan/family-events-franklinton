import unittest

from scripts.ingest.data_model import validate_place, validate_promotion, validate_source, validate_submission


class MigrationModelTests(unittest.TestCase):
    def test_source_health_requires_https_and_timezone(self):
        source = {"sourceId": "library", "sourceName": "Library", "kind": "ical", "sourceUrl": "https://example.org", "enabled": True, "status": "fresh", "lastSuccessfulRefresh": "2026-09-01T12:00:00Z"}
        self.assertIs(validate_source(source), source)
        with self.assertRaises(ValueError):
            validate_source(dict(source, sourceUrl="http://example.org"))
        with self.assertRaises(ValueError):
            validate_source(dict(source, enabled=1))
        with self.assertRaises(ValueError):
            validate_source(dict(source, sourceName="x" * 201))

    def test_place_has_provenance_and_valid_age_range(self):
        place = {"id": "park-1", "name": "Family Park", "latitude": 36.1, "longitude": -78.4, "officialUrl": "https://example.org/park", "ageMin": 0, "ageMax": 8, "lastChecked": "2026-09-01T12:00:00Z"}
        self.assertIs(validate_place(place), place)
        with self.assertRaises(ValueError):
            validate_place(dict(place, ageMin=9))
        with self.assertRaises(ValueError):
            validate_place(dict(place, latitude=True))
        with self.assertRaises(ValueError):
            validate_place(dict(place, longitude=float("inf")))

    def test_free_submission_requires_official_link(self):
        submission = {"id": "sub-1", "kind": "event", "status": "pending", "officialUrl": "https://example.org/event", "submittedAt": "2026-09-01T12:00:00Z", "payload": {"title": "Storytime"}}
        self.assertIs(validate_submission(submission), submission)
        with self.assertRaises(ValueError):
            validate_submission(dict(submission, officialUrl="https://"))
        with self.assertRaises(ValueError):
            validate_submission(dict(submission, id="bad id"))
        with self.assertRaises(ValueError):
            validate_submission(dict(submission, payload={"notes": "x" * 70000}))

    def test_promotion_is_bounded_and_cannot_be_unlabeled_by_contract(self):
        promotion = {"id": "promo-1", "targetType": "place", "targetId": "park-1", "sponsorName": "Family Park", "startsAt": "2026-09-01T00:00:00Z", "endsAt": "2026-09-08T00:00:00Z", "status": "active", "label": "Sponsored"}
        self.assertIs(validate_promotion(promotion), promotion)
        with self.assertRaises(ValueError):
            validate_promotion(dict(promotion, endsAt="2026-08-01T00:00:00Z"))
        with self.assertRaises(ValueError):
            validate_promotion(dict(promotion, label="Featured"))
        with self.assertRaises(ValueError):
            validate_promotion(dict(promotion, sponsorName=""))


if __name__ == "__main__":
    unittest.main()
