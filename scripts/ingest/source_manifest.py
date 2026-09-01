"""Load the reviewed source manifest without enabling unverified candidates."""
import json
from pathlib import Path

try:
    from .data_model import validate_source
except ImportError:  # Supports direct execution from the collector script.
    from data_model import validate_source

MANIFEST = Path(__file__).with_name("source_manifest.json")


def load_manifest(path=MANIFEST):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("manifestVersion") != 1 or not isinstance(payload.get("sources"), list):
        raise ValueError("unsupported or malformed source manifest")
    for source in payload["sources"]:
        validate_source(source)
        if source.get("refreshIntervalMinutes") is not None:
            interval = source["refreshIntervalMinutes"]
            if isinstance(interval, bool) or not isinstance(interval, int) or interval < 60:
                raise ValueError("refreshIntervalMinutes must be an integer of at least 60")
    return payload


def enabled_feeds(path=MANIFEST):
    """Return the collector's legacy tuple shape for enabled feed sources."""
    return [
        (source["sourceName"], source["feedUrl"], source["sourceUrl"])
        for source in load_manifest(path)["sources"]
        if source.get("enabled") and source.get("feedUrl")
    ]
