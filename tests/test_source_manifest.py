import json
import tempfile
import unittest
from pathlib import Path

from scripts.ingest.source_manifest import enabled_feeds, load_manifest


class SourceManifestTests(unittest.TestCase):
    def test_only_reviewed_enabled_sources_become_feeds(self):
        feeds = enabled_feeds()
        self.assertEqual(len(feeds), 4)
        self.assertTrue(all(item[1].startswith("https://") for item in feeds))
        self.assertNotIn("City of Raleigh Parks", {item[0] for item in feeds})

    def test_manifest_rejects_short_refresh_interval(self):
        payload = load_manifest()
        payload["sources"][0]["refreshIntervalMinutes"] = 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_manifest_contains_disabled_candidates_without_enabling_them(self):
        sources = load_manifest()["sources"]
        candidates = [item for item in sources if not item["enabled"]]
        self.assertTrue(candidates)
        self.assertTrue(all(item["status"] == "disabled" for item in candidates))

    def test_manifest_ids_are_stable_and_unique(self):
        ids = [item["sourceId"] for item in load_manifest()["sources"]]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
