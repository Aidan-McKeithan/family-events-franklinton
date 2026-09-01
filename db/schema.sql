-- D1 schema for the server-side event catalog.  Timestamps are ISO-8601 UTC.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('fresh', 'stale', 'unavailable')),
  last_successful_refresh TEXT,
  last_attempt TEXT,
  last_success TEXT,
  using_last_known_good INTEGER NOT NULL DEFAULT 0 CHECK (using_last_known_good IN (0, 1)),
  last_error TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalog_metadata (
  id INTEGER PRIMARY KEY CHECK (id = 1), generated_at TEXT NOT NULL,
  origin_label TEXT NOT NULL, origin_latitude REAL NOT NULL,
  origin_longitude REAL NOT NULL, updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalog_publish_guard (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  generated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO catalog_publish_guard (id, generated_at) VALUES (1, '1970-01-01T00:00:00Z');

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  start TEXT NOT NULL,
  end TEXT,
  venue TEXT NOT NULL,
  address TEXT,
  town TEXT NOT NULL,
  latitude REAL NOT NULL,
  longitude REAL NOT NULL,
  coordinate_precision TEXT NOT NULL CHECK (coordinate_precision IN ('venue', 'town')),
  age_min REAL,
  age_max REAL,
  audience_group TEXT NOT NULL CHECK (audience_group IN ('general', 'early-childhood', 'school-age', 'teen')),
  category TEXT NOT NULL CHECK (category IN ('stories', 'play', 'arts', 'nature', 'community')),
  cost_status TEXT NOT NULL CHECK (cost_status IN ('free', 'paid', 'unknown')),
  cost_label TEXT,
  setting TEXT NOT NULL CHECK (setting IN ('indoor', 'outdoor', 'both', 'unknown')),
  registration_required TEXT NOT NULL CHECK (registration_required IN ('true', 'false', 'unknown')),
  registration_url TEXT,
  status TEXT NOT NULL CHECK (status IN ('active', 'postponed', 'cancelled')) DEFAULT 'active',
  accessibility TEXT,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  additional_sources_json TEXT NOT NULL DEFAULT '[]',
  last_checked TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS events_start_idx ON events (start);
CREATE INDEX IF NOT EXISTS events_status_start_idx ON events (status, start);
CREATE INDEX IF NOT EXISTS events_source_idx ON events (source_name);
