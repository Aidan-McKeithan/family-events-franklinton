#!/usr/bin/env python3
"""Validate the public event dataset using only the Python standard library."""
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).parents[1] / "public" / "data" / "events.json"
REQUIRED = {"id", "title", "start", "venue", "town", "latitude", "longitude", "coordinatePrecision", "ageMin", "ageMax", "category", "costStatus", "setting", "registrationRequired", "status", "sourceName", "sourceUrl", "lastChecked"}


def parse_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None, f"Timestamp lacks timezone: {value}"
    return parsed


def validate(data):
    assert data["schemaVersion"] == 1
    parse_timestamp(data["generatedAt"])
    assert data["origin"]["label"] and isinstance(data.get("sources"), list) and isinstance(data.get("sourceFailures"), list)
    for source in data["sources"]:
        assert source["sourceName"] and source["status"] in {"fresh", "stale", "unavailable"}
        if source.get("lastSuccessfulRefresh"):
            parse_timestamp(source["lastSuccessfulRefresh"])
    for failure in data["sourceFailures"]:
        assert failure["sourceName"] and isinstance(failure["usingLastKnownGood"], bool)
    assert isinstance(data["events"], list)
    ids = set()
    for event in data["events"]:
        missing = REQUIRED - event.keys()
        assert not missing, f"{event.get('id', '<unknown>')} missing {sorted(missing)}"
        assert all(isinstance(event[key], str) and event[key].strip() for key in ("id", "title", "venue", "town", "sourceName", "sourceUrl"))
        assert event["id"] not in ids, f"Duplicate id: {event['id']}"
        ids.add(event["id"])
        start = parse_timestamp(event["start"])
        if event.get("end"):
            assert parse_timestamp(event["end"]) >= start
        assert type(event["latitude"]) in {int, float} and -90 <= event["latitude"] <= 90
        assert type(event["longitude"]) in {int, float} and -180 <= event["longitude"] <= 180
        assert event["coordinatePrecision"] in {"venue", "town"}
        assert event["category"] in {"stories", "play", "arts", "nature", "community"}
        for age in (event["ageMin"], event["ageMax"]):
            assert age is None or (type(age) in {int, float} and 0 <= age <= 18)
        if event["ageMin"] is not None and event["ageMax"] is not None:
            assert event["ageMin"] <= event["ageMax"]
        assert event["costStatus"] in {"free", "paid", "unknown"}
        assert event["setting"] in {"indoor", "outdoor", "both", "unknown"}
        assert event["registrationRequired"] in {"true", "false", "unknown"}
        assert event["status"] in {"active", "postponed", "cancelled"}
        parsed_url = urlparse(event["sourceUrl"])
        assert parsed_url.scheme == "https" and parsed_url.netloc
        if event.get("registrationUrl"):
            registration_url = urlparse(event["registrationUrl"])
            assert registration_url.scheme == "https" and registration_url.netloc
        parse_timestamp(event["lastChecked"])


if __name__ == "__main__":
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    validate(payload)
    print(f"Validated {len(payload['events'])} events")
