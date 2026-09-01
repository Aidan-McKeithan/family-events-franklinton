-- Permanent CAS guard used as the first statement in each D1 batch.
CREATE TABLE IF NOT EXISTS catalog_publish_guard (
  id INTEGER PRIMARY KEY CHECK (id = 1), generated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO catalog_publish_guard (id, generated_at) VALUES (1, '1970-01-01T00:00:00Z');
