-- Freshness fields and stable catalog snapshot timestamp.
ALTER TABLE sources ADD COLUMN last_attempt TEXT;
ALTER TABLE sources ADD COLUMN last_success TEXT;
ALTER TABLE sources ADD COLUMN using_last_known_good INTEGER NOT NULL DEFAULT 0 CHECK (using_last_known_good IN (0, 1));
CREATE TABLE IF NOT EXISTS catalog_metadata (
  id INTEGER PRIMARY KEY CHECK (id = 1), generated_at TEXT NOT NULL,
  origin_label TEXT NOT NULL, origin_latitude REAL NOT NULL,
  origin_longitude REAL NOT NULL, updated_at TEXT NOT NULL
);
