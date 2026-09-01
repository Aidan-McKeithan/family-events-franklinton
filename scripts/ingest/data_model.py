"""Shared, deterministic checks for the event-platform migration.

This module deliberately does not call an AI model or a live service.  Model
output and user/business submissions are untrusted candidates until they pass
these checks and a publishing workflow approves them.
"""
from datetime import datetime
import json
import math
import re
from urllib.parse import urlparse


ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
MAX_NAME = 200
MAX_TEXT = 5000
MAX_PAYLOAD_BYTES = 65536


def _string(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be a non-empty string of at most {limit} characters")
    return value


def _id(value, field):
    _string(value, field, 120)
    if not ID_RE.fullmatch(value):
        raise ValueError(f"{field} contains invalid characters")


def _number(value, field, low=None, high=None):
    # bool is an int subclass in Python and must never pass coordinate/age checks.
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{field} is out of range")


def _timestamp(value, field="timestamp"):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError(f"{field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an ISO timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")


def _https_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_source(source):
    """Validate one source-registry row and return it unchanged."""
    required = {"sourceId", "sourceName", "kind", "sourceUrl", "enabled", "status"}
    missing = required - source.keys()
    if missing:
        raise ValueError(f"source missing {sorted(missing)}")
    _id(source["sourceId"], "sourceId")
    _string(source["sourceName"], "sourceName", MAX_NAME)
    if not _https_url(source["sourceUrl"]):
        raise ValueError("sourceUrl must be an HTTPS URL")
    if source.get("feedUrl") and not _https_url(source["feedUrl"]):
        raise ValueError("feedUrl must be an HTTPS URL")
    if source["kind"] not in {"ical", "rss", "api", "web", "submission"}:
        raise ValueError("unsupported source kind")
    if source["status"] not in {"fresh", "stale", "unavailable", "disabled"}:
        raise ValueError("unsupported source status")
    if not isinstance(source["enabled"], bool):
        raise ValueError("enabled must be boolean")
    for key in ("lastAttemptAt", "lastSuccessfulRefresh"):
        if source.get(key):
            _timestamp(source[key], key)
    return source


def validate_place(place):
    """Validate a family place record before it is made public."""
    required = {"id", "name", "latitude", "longitude", "officialUrl", "lastChecked"}
    missing = required - place.keys()
    if missing:
        raise ValueError(f"place missing {sorted(missing)}")
    _id(place["id"], "place id")
    _string(place["name"], "place name", MAX_NAME)
    if not _https_url(place["officialUrl"]):
        raise ValueError("officialUrl must be an HTTPS URL")
    _number(place["latitude"], "latitude", -90, 90)
    _number(place["longitude"], "longitude", -180, 180)
    for field in ("ageMin", "ageMax"):
        if place.get(field) is not None:
            _number(place[field], field, 0, 18)
    if place.get("ageMin") is not None and place.get("ageMax") is not None and place["ageMin"] > place["ageMax"]:
        raise ValueError("place age range is reversed")
    _timestamp(place["lastChecked"], "lastChecked")
    return place


def validate_submission(submission):
    """Validate an untrusted event/place submission envelope."""
    required = {"id", "kind", "status", "officialUrl", "submittedAt", "payload"}
    missing = required - submission.keys()
    if missing:
        raise ValueError(f"submission missing {sorted(missing)}")
    _id(submission["id"], "submission id")
    if submission["kind"] not in {"event", "place"}:
        raise ValueError("submission kind must be event or place")
    if submission["status"] not in {"pending", "approved", "rejected", "needs-review"}:
        raise ValueError("unsupported submission status")
    if not _https_url(submission["officialUrl"]):
        raise ValueError("submission requires an HTTPS officialUrl")
    _timestamp(submission["submittedAt"], "submittedAt")
    if not isinstance(submission["payload"], dict):
        raise ValueError("submission payload must be an object")
    try:
        payload_size = len(json.dumps(submission["payload"], ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError) as error:
        raise ValueError("submission payload must be JSON-serializable") from error
    if payload_size > MAX_PAYLOAD_BYTES:
        raise ValueError("submission payload is too large")
    return submission


def validate_promotion(promotion):
    """Validate a sponsored-placement record; sponsorship never replaces source data."""
    required = {"id", "targetType", "targetId", "sponsorName", "startsAt", "endsAt", "status", "label"}
    missing = required - promotion.keys()
    if missing:
        raise ValueError(f"promotion missing {sorted(missing)}")
    _id(promotion["id"], "promotion id")
    _id(promotion["targetId"], "promotion targetId")
    _string(promotion["sponsorName"], "sponsorName", MAX_NAME)
    if promotion["targetType"] not in {"event", "place"}:
        raise ValueError("promotion targetType must be event or place")
    if promotion["status"] not in {"scheduled", "active", "expired", "paused"}:
        raise ValueError("unsupported promotion status")
    if promotion["label"] != "Sponsored":
        raise ValueError("promotions must use the Sponsored label")
    _timestamp(promotion["startsAt"], "startsAt")
    _timestamp(promotion["endsAt"], "endsAt")
    if datetime.fromisoformat(promotion["endsAt"].replace("Z", "+00:00")) < datetime.fromisoformat(promotion["startsAt"].replace("Z", "+00:00")):
        raise ValueError("promotion ends before it starts")
    if not promotion["sponsorName"].strip():
        raise ValueError("sponsorName is required")
    return promotion
