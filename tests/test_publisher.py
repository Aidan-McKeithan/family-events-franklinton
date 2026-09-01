import json
import unittest
from pathlib import Path

from scripts.ingest.publish import build_publish_sql

ROOT = Path(__file__).parents[1]


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "public" / "data" / "events.json").read_text(encoding="utf-8"))
        self.registry = json.loads((ROOT / "scripts" / "ingest" / "source_registry.json").read_text(encoding="utf-8"))

    def test_output_is_deterministic_and_transactional(self):
        first = build_publish_sql(self.payload, self.registry)
        second = build_publish_sql(self.payload, self.registry)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("BEGIN TRANSACTION;"))
        self.assertTrue(first.endswith("COMMIT;\n"))
        self.assertIn("catalog_metadata", first)

    def test_incomplete_source_batch_is_rejected_before_sql(self):
        incomplete = dict(self.payload, sources=self.payload["sources"][:-1])
        with self.assertRaises(ValueError):
            build_publish_sql(incomplete, self.registry)

    def test_failed_source_retains_last_known_good(self):
        payload = json.loads(json.dumps(self.payload))
        payload["sources"][0]["status"] = "stale"
        sql = build_publish_sql(payload, self.registry)
        self.assertIn("using_last_known_good", sql)
        self.assertIn(",1,", sql)

    def test_older_snapshot_is_rejected(self):
        with self.assertRaises(ValueError):
            build_publish_sql(self.payload, self.registry, current_generated_at="2999-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
