import unittest
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parents[1]


class BackendFoundationTests(unittest.TestCase):
    def test_d1_schema_has_event_and_source_tables(self):
        schema = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS events", schema)
        self.assertIn("CREATE TABLE IF NOT EXISTS sources", schema)
        self.assertIn("events_status_start_idx", schema)
        self.assertIn("catalog_metadata", schema)
        self.assertIn("using_last_known_good", schema)
        migration = (ROOT / "db" / "migrations" / "0002_catalog_hardening.sql").read_text(encoding="utf-8")
        self.assertIn("origin_latitude", migration)
        self.assertIn("CHECK (using_last_known_good IN (0, 1))", migration)

    def test_worker_is_read_only_and_bounded(self):
        worker = (ROOT / "worker.js").read_text(encoding="utf-8")
        self.assertIn('request.method !== "GET"', worker)
        self.assertIn("Math.min(Math.max(requestedLimit, 1), 1000)", worker)
        self.assertIn('url.pathname === "/api/events"', worker)
        self.assertIn('url.pathname === "/api/health"', worker)
        self.assertIn("hasMore", worker)
        self.assertIn("nextCursor", worker)
        self.assertIn("parseDateOnly", worker)
        self.assertIn('start < ?', worker)
        self.assertIn("last_attempt", worker)
        self.assertIn("cache-control", worker)
        self.assertIn("x-content-type-options", worker)
        self.assertIn('"stale", "unavailable"', worker)
        self.assertIn("origin_latitude", worker)
        self.assertIn("invalid attribution metadata", worker)

    def test_runtime_config_does_not_contain_credentials(self):
        config = (ROOT / "wrangler.toml.example").read_text(encoding="utf-8")
        self.assertIn("database_id =", config)
        self.assertNotIn("api_token", config.lower())

    def test_fresh_database_applies_all_migrations(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript((ROOT / "db" / "migrations" / "0001_initial.sql").read_text(encoding="utf-8"))
        connection.executescript((ROOT / "db" / "migrations" / "0002_catalog_hardening.sql").read_text(encoding="utf-8"))
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"events", "sources", "catalog_metadata"}.issubset(tables))
        source_columns = {row[1] for row in connection.execute("PRAGMA table_info(sources)")}
        self.assertTrue({"last_attempt", "last_success", "using_last_known_good"}.issubset(source_columns))
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO sources (id, source_name, source_url, status, updated_at, using_last_known_good) VALUES ('x', 'X', 'https://x.example', 'fresh', '2026-09-01T12:00:00Z', 2)")
        connection.execute("INSERT INTO catalog_metadata VALUES (1, '2026-09-01T12:00:00Z', 'Franklinton, NC 27525', 36.101, -78.458, '2026-09-01T12:00:00Z')")
        self.assertEqual(connection.execute("SELECT origin_label FROM catalog_metadata WHERE id=1").fetchone()[0], "Franklinton, NC 27525")


if __name__ == "__main__":
    unittest.main()
