import json
import sqlite3
import unittest
from pathlib import Path

from scripts.ingest.publish import build_publish_sql

ROOT = Path(__file__).parents[1]


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "public" / "data" / "events.json").read_text(encoding="utf-8"))
        self.registry = json.loads((ROOT / "scripts" / "ingest" / "source_manifest.json").read_text(encoding="utf-8"))

    def test_output_is_deterministic_and_transactional(self):
        first = build_publish_sql(self.payload, self.registry)
        second = build_publish_sql(self.payload, self.registry)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("BEGIN TRANSACTION;"))
        self.assertTrue(first.endswith("COMMIT;\n"))
        self.assertIn("catalog_metadata", first)
        self.assertNotIn("created_at=excluded.created_at", first)
        self.assertIn("WHERE excluded.generated_at >= catalog_metadata.generated_at", first)

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
        self.assertNotIn("DELETE FROM events WHERE source_name='Franklin County Library'", sql)

    def test_successful_source_reconciles_removed_events(self):
        sql = build_publish_sql(self.payload, self.registry)
        self.assertIn("DELETE FROM events WHERE source_name='Franklin County Library'", sql)

    def test_top_level_failure_controls_source_lkg_status(self):
        payload = json.loads(json.dumps(self.payload))
        payload["sources"][1]["status"] = "fresh"
        payload["sourceFailures"] = [{"sourceName": "Franklin County Kids & Teens", "usingLastKnownGood": True}]
        sql = build_publish_sql(payload, self.registry)
        self.assertIn("'stale'", sql)
        self.assertIn(",1,", sql)

    def test_sql_runs_on_fresh_schema_and_replay_is_idempotent(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
        sql = build_publish_sql(self.payload, self.registry)
        connection.executescript(sql)
        count = connection.execute("SELECT count(*) FROM events").fetchone()[0]
        connection.execute("UPDATE events SET created_at='2000-01-01T00:00:00Z' WHERE id=(SELECT id FROM events LIMIT 1)")
        connection.commit()
        connection.executescript(sql)
        self.assertEqual(connection.execute("SELECT count(*) FROM events").fetchone()[0], count)
        self.assertEqual(connection.execute("SELECT count(*) FROM events WHERE created_at='2000-01-01T00:00:00Z'").fetchone()[0], 1)

    def test_sql_failure_rolls_back_batch(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
        sql = build_publish_sql(self.payload, self.registry).replace("COMMIT;", "INSERT INTO no_such_table VALUES (1);\nCOMMIT;")
        with self.assertRaises(sqlite3.OperationalError):
            connection.executescript(sql)
        connection.rollback()
        self.assertEqual(connection.execute("SELECT count(*) FROM events").fetchone()[0], 0)

    def test_stale_source_does_not_reconcile_existing_rows(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
        connection.executescript(build_publish_sql(self.payload, self.registry))
        before = connection.execute("SELECT count(*) FROM events WHERE source_name='Franklin County Kids & Teens'").fetchone()[0]
        changed = json.loads(json.dumps(self.payload))
        changed["sources"][1]["status"] = "stale"
        changed["events"] = [event for event in changed["events"] if event["sourceName"] != "Franklin County Kids & Teens"]
        connection.executescript(build_publish_sql(changed, self.registry))
        self.assertEqual(connection.execute("SELECT count(*) FROM events WHERE source_name='Franklin County Kids & Teens'").fetchone()[0], before)

    def test_older_snapshot_aborts_before_mutation(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
        connection.executescript(build_publish_sql(self.payload, self.registry, published_at="2026-09-02T00:00:00Z"))
        before = connection.execute("SELECT count(*) FROM events").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            connection.executescript(build_publish_sql(self.payload, self.registry, published_at="2026-09-01T00:00:00Z"))
        connection.rollback()
        self.assertEqual(connection.execute("SELECT count(*) FROM events").fetchone()[0], before)

    def test_older_snapshot_is_rejected(self):
        with self.assertRaises(ValueError):
            build_publish_sql(self.payload, self.registry, current_generated_at="2999-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
