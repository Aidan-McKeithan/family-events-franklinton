-- Initial D1 catalog migration. Apply with: wrangler d1 migrations apply EVENTS_DB
-- This file intentionally mirrors db/schema.sql for local review and reproducibility.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY, source_name TEXT NOT NULL, source_url TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('fresh', 'stale', 'unavailable')),
  last_successful_refresh TEXT, last_error TEXT, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT, start TEXT NOT NULL, end TEXT,
  venue TEXT NOT NULL, address TEXT, town TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL,
  coordinate_precision TEXT NOT NULL CHECK (coordinate_precision IN ('venue', 'town')),
  age_min REAL, age_max REAL,
  audience_group TEXT NOT NULL CHECK (audience_group IN ('general', 'early-childhood', 'school-age', 'teen')),
  category TEXT NOT NULL CHECK (category IN ('stories', 'play', 'arts', 'nature', 'community')),
  cost_status TEXT NOT NULL CHECK (cost_status IN ('free', 'paid', 'unknown')), cost_label TEXT,
  setting TEXT NOT NULL CHECK (setting IN ('indoor', 'outdoor', 'both', 'unknown')),
  registration_required TEXT NOT NULL CHECK (registration_required IN ('true', 'false', 'unknown')),
  registration_url TEXT, status TEXT NOT NULL CHECK (status IN ('active', 'postponed', 'cancelled')) DEFAULT 'active',
  accessibility TEXT, source_name TEXT NOT NULL, source_url TEXT NOT NULL,
  additional_sources_json TEXT NOT NULL DEFAULT '[]', last_checked TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_start_idx ON events (start);
CREATE INDEX IF NOT EXISTS events_status_start_idx ON events (status, start);
CREATE INDEX IF NOT EXISTS events_source_idx ON events (source_name);
