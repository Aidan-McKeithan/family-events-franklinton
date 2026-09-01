#!/usr/bin/env python3
"""Collect family events from official CivicPlus iCalendar feeds."""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

try:
    from .source_manifest import enabled_feeds
except ImportError:  # Supports the existing GitHub job's `python scripts/...py` form.
    from source_manifest import enabled_feeds

ROOT = Path(__file__).parents[2]
OUTPUT = ROOT / "public" / "data" / "events.json"
EASTERN = ZoneInfo("America/New_York")
USER_AGENT = "LittleDayOut/1.0 (+https://github.com/Aidan-McKeithan/family-events-franklinton)"

FEEDS = enabled_feeds()

PLACES = {
    "franklinton": ("Franklinton, NC", 36.1018, -78.4581),
    "youngsville": ("Youngsville, NC", 36.0243, -78.4744),
    "bunn": ("Bunn, NC", 35.9613, -78.2536),
    "louisburg": ("Louisburg, NC", 36.0990, -78.3011),
    "creedmoor": ("Creedmoor, NC", 36.1224, -78.6861),
    "oxford": ("Oxford, NC", 36.3107, -78.5908),
    "south branch": ("Creedmoor, NC", 36.1224, -78.6861),
    "thornton": ("Oxford, NC", 36.3107, -78.5908),
}

FAMILY_WORDS = re.compile(r"baby|babies|toddler|preschool|child|children|kid|kids|teen|family|families|storytime|story time|craft|steam|play|puppet|youth", re.I)
ADULT_ONLY_WORDS = re.compile(r"\bfor adults?\b|\badults? only\b|\bseniors?\b|\b55\s*\+|\bages?\s+18\s*\+", re.I)
AGE_RANGE = re.compile(r"ages?\s*(\d+(?:\.5)?)\s*(?:-|–|to)\s*(\d+(?:\.5)?)", re.I)
AGE_UP_TO = re.compile(r"(?:up to|through)\s+age\s+(\d+(?:\.5)?)", re.I)


def unescape(value):
    return value.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\").strip()


def parse_ics(text):
    unfolded = re.sub(r"\r?\n[ \t]", "", text)
    events, current = [], None
    for line in unfolded.splitlines():
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
        elif current is not None and ":" in line:
            raw_key, value = line.split(":", 1)
            key = raw_key.split(";", 1)[0]
            current[key] = unescape(value)
    return events


def parse_ical_time(value):
    if re.fullmatch(r"\d{8}", value):
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=EASTERN)
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(EASTERN)
    return datetime.strptime(value[:15], "%Y%m%dT%H%M%S").replace(tzinfo=EASTERN)


def locate(location):
    lower = location.lower()
    for name, place in PLACES.items():
        if name in lower:
            return place
    return None


def ages(text):
    match = AGE_RANGE.search(text)
    if match:
        return float(match.group(1)), float(match.group(2))
    match = AGE_UP_TO.search(text)
    if match:
        return 0, float(match.group(1))
    return None, None


def category_for(text):
    if re.search(r"story|book|read", text, re.I): return "stories"
    if re.search(r"art|craft|paint|music", text, re.I): return "arts"
    if re.search(r"park|nature|garden|outdoor|hike", text, re.I): return "nature"
    if re.search(r"play|sensory|baby|toddler", text, re.I): return "play"
    return "community"


def audience_group(text):
    if re.search(r"\bteens?\b|teen leadership", text, re.I): return "teen"
    if re.search(r"school[- ]age|\bK\s*[-–]\s*5|\bgrades?\b", text, re.I): return "school-age"
    if re.search(r"newborn|cruiser|bab(?:y|ies)|toddler|preschool", text, re.I): return "early-childhood"
    return "general"


def clean_text(value):
    return re.sub(r"<[^>]+>", " ", value or "").replace("&nbsp;", " ").strip()


def normalize(raw, source_name, source_url, checked):
    title = raw.get("SUMMARY", "Untitled event")
    description = raw.get("DESCRIPTION", "")
    combined = f"{title} {description}"
    if re.search(r"\badults?\b", title, re.I) or ADULT_ONLY_WORDS.search(combined) or not FAMILY_WORDS.search(combined) or "DTSTART" not in raw:
        return None
    place = locate(raw.get("LOCATION", ""))
    if place is None:
        return None
    town, lat, lon = place
    start = parse_ical_time(raw["DTSTART"])
    end = parse_ical_time(raw["DTEND"]) if raw.get("DTEND") else None
    age_min, age_max = ages(combined)
    occurrence_id = f"{title.lower().strip()}-{town.lower()}-{start.isoformat()}"
    detail_url = raw.get("URL", source_url)
    location = clean_text(raw.get("LOCATION", "Location listed by organizer").split(",")[0])
    status_text = raw.get("STATUS", "").upper()
    status = "cancelled" if status_text == "CANCELLED" or re.search(r"\bcancelled\b|\bcanceled\b", combined, re.I) else "postponed" if re.search(r"\bpostponed\b", combined, re.I) else "active"
    registration = "false" if re.search(r"\b(?:no|not)\s+registration\s+(?:is\s+)?required\b|\bregistration\s+(?:is\s+)?not\s+required\b", combined, re.I) else "true" if re.search(r"\bregistration\s+(?:is\s+)?required\b|\bregister\s+(?:at|by|online|now)\b", combined, re.I) else "unknown"
    registration_url = raw.get("X-REGISTRATION-URL")
    if not registration_url or not registration_url.startswith("https://"):
        registration_url = None
    return {
        "id": re.sub(r"[^a-zA-Z0-9._-]", "-", occurrence_id), "title": title, "description": description,
        "start": start.isoformat(), "end": end.isoformat() if end else None,
        "venue": location, "town": town, "latitude": lat, "longitude": lon, "coordinatePrecision": "town",
        "ageMin": age_min, "ageMax": age_max, "audienceGroup": audience_group(combined), "category": category_for(combined),
        "costStatus": "free" if re.search(r"\bfree\b", combined, re.I) else "unknown",
        "setting": "outdoor" if re.search(r"outdoor|park|outside", combined, re.I) else "unknown",
        "registrationRequired": registration, "status": status,
        "accessibility": None, "registrationUrl": registration_url,
        "sourceName": source_name, "sourceUrl": detail_url if detail_url.startswith("https://") else source_url,
        "lastChecked": checked,
    }


def fetch(url):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/calendar,text/plain;q=0.9,*/*;q=0.1"})
    with urlopen(request, timeout=25) as response:
        text = response.read().decode("utf-8", errors="replace")
        if "BEGIN:VCALENDAR" not in text or "END:VCALENDAR" not in text:
            raise ValueError("Official feed did not return iCalendar data")
        return text


def add_event(collected, event):
    """Keep the first feed's fields and retain attribution from exact duplicate occurrences."""
    if event["id"] in collected:
        existing = collected[event["id"]]
        existing_pairs = {(existing["sourceName"], existing["sourceUrl"])}
        existing_pairs.update((source["sourceName"], source["sourceUrl"]) for source in existing.get("additionalSources", []))
        if (event["sourceName"], event["sourceUrl"]) not in existing_pairs:
            existing.setdefault("additionalSources", []).append({"sourceName": event["sourceName"], "sourceUrl": event["sourceUrl"]})
    else:
        collected[event["id"]] = event


def expand_occurrences(raw, window_end):
    """Expand the daily/weekly recurrence forms used by CivicPlus feeds."""
    rule = raw.get("RRULE")
    if not rule:
        return [raw]
    if any(key in raw for key in ("EXDATE", "RDATE", "RECURRENCE-ID")):
        raise ValueError("Unsupported recurrence exception")
    parts = dict(item.split("=", 1) for item in rule.split(";") if "=" in item)
    unsupported = set(parts) - {"FREQ", "COUNT", "UNTIL", "INTERVAL"}
    if unsupported:
        raise ValueError(f"Unsupported recurrence fields: {sorted(unsupported)}")
    frequency = parts.get("FREQ")
    if frequency not in {"DAILY", "WEEKLY"}:
        raise ValueError(f"Unsupported recurrence frequency: {frequency}")
    interval = int(parts.get("INTERVAL", "1"))
    if interval < 1:
        raise ValueError("Recurrence interval must be positive")
    step = timedelta(days=(1 if frequency == "DAILY" else 7) * interval)
    start = parse_ical_time(raw["DTSTART"])
    original_end = parse_ical_time(raw["DTEND"]) if raw.get("DTEND") else None
    duration = original_end - start if original_end else None
    until = parse_ical_time(parts["UNTIL"]) if parts.get("UNTIL") else window_end
    limit = min(int(parts.get("COUNT", "200")), 200)
    occurrences = []
    current = start
    while current <= min(until, window_end) and len(occurrences) < limit:
        occurrence = dict(raw)
        occurrence["DTSTART"] = current.strftime("%Y%m%dT%H%M%S")
        if duration:
            occurrence["DTEND"] = (current + duration).strftime("%Y%m%dT%H%M%S")
        occurrences.append(occurrence)
        current += step
    return occurrences


def collect(now=None):
    now = now or datetime.now(timezone.utc)
    checked = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    cutoff = now.astimezone(EASTERN) + timedelta(days=45)
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"events": [], "sources": []}
    previous_by_source = {}
    for event in previous.get("events", []):
        previous_by_source.setdefault(event["sourceName"], []).append(event)
        for source in event.get("additionalSources", []):
            attributed = dict(event)
            attributed["sourceName"] = source["sourceName"]
            attributed["sourceUrl"] = source["sourceUrl"]
            attributed.pop("additionalSources", None)
            previous_by_source.setdefault(source["sourceName"], []).append(attributed)
    previous_status = {item["sourceName"]: item for item in previous.get("sources", [])}
    collected, failures, sources = {}, [], []
    for source_name, feed_url, source_url in FEEDS:
        try:
            source_events = []
            raw_events = parse_ics(fetch(feed_url))
            if not raw_events:
                raise ValueError("Official feed returned zero calendar events")
            for raw in raw_events:
                for occurrence in expand_occurrences(raw, cutoff):
                    event = normalize(occurrence, source_name, source_url, checked)
                    if event and now.astimezone(EASTERN) - timedelta(days=1) <= parse_ical_time(occurrence["DTSTART"]) <= cutoff:
                        source_events.append(event)
            if not source_events:
                raise ValueError("Official feed produced zero supported upcoming family events")
            for event in source_events:
                add_event(collected, event)
            sources.append({"sourceName": source_name, "lastSuccessfulRefresh": checked, "status": "fresh"})
        except Exception as error:  # Keep other official sources usable.
            prior = previous_by_source.get(source_name, [])
            for event in prior:
                add_event(collected, event)
            prior_checked = previous_status.get(source_name, {}).get("lastSuccessfulRefresh")
            print(f"{source_name} refresh failed: {error}", file=sys.stderr)
            failures.append({"sourceName": source_name, "message": "refresh failed", "usingLastKnownGood": bool(prior)})
            sources.append({"sourceName": source_name, "lastSuccessfulRefresh": prior_checked, "status": "stale" if prior else "unavailable"})
    if not collected:
        raise RuntimeError("No source produced valid events; preserving last known good dataset. " + "; ".join(item["sourceName"] for item in failures))
    return {
        "schemaVersion": 1, "generatedAt": checked,
        "origin": {"label": "Franklinton, NC 27525", "latitude": 36.101, "longitude": -78.458},
        "sourceFailures": failures, "sources": sources, "events": sorted(collected.values(), key=lambda event: event["start"]),
    }


if __name__ == "__main__":
    try:
        payload = collect()
        OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Collected {len(payload['events'])} events; {len(payload['sourceFailures'])} source failures")
    except Exception as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
