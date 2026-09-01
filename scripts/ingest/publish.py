#!/usr/bin/env python3
"""Turn a completely validated collector payload into deterministic D1 SQL.

This module never fetches a network resource and never writes to D1 itself.
The generated transaction can be reviewed, passed to Wrangler, or used by a
future authenticated publisher. Existing rows are only upserted: a partial or
failed refresh cannot erase the last-known-good catalog.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from scripts.validate_events import validate
from scripts.ingest.source_manifest import load_manifest

ROOT = Path(__file__).parents[2]
REGISTRY = ROOT / "scripts" / "ingest" / "source_manifest.json"


def sql_string(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def sql_number(value):
    return "NULL" if value is None else str(value)


def source_rows(payload, registry):
    by_name = {item["sourceName"]: item for item in payload.get("sources", [])}
    rows = []
    for configured in registry["sources"] if isinstance(registry, dict) else registry:
        if not configured.get("enabled"):
            continue
        current = by_name.get(configured["sourceName"])
        if current is None:
            raise ValueError(f"enabled source missing from complete payload: {configured['sourceName']}")
        status = current.get("status")
        if status not in {"fresh", "stale", "unavailable"}:
            raise ValueError(f"invalid source status: {status}")
        rows.append((configured, current))
    configured_sources = registry["sources"] if isinstance(registry, dict) else registry
    unknown = set(by_name) - {item["sourceName"] for item in configured_sources}
    if unknown:
        raise ValueError(f"payload contains unregistered sources: {sorted(unknown)}")
    return rows


def build_publish_sql(payload, registry=None, published_at=None, current_generated_at=None):
    """Return one all-or-nothing SQL transaction for a valid complete batch."""
    validate(payload)
    registry = registry if registry is not None else load_manifest()
    rows = source_rows(payload, registry)
    published_at = published_at or payload["generatedAt"]
    if current_generated_at and datetime.fromisoformat(published_at.replace("Z", "+00:00")) < datetime.fromisoformat(current_generated_at.replace("Z", "+00:00")):
        raise ValueError("refusing to publish an older catalog snapshot")
    statements = ["BEGIN TRANSACTION;"]
    for event in sorted(payload["events"], key=lambda item: item["id"]):
        columns = ["id","title","description","start","end","venue","address","town","latitude","longitude","coordinate_precision","age_min","age_max","audience_group","category","cost_status","cost_label","setting","registration_required","registration_url","status","accessibility","source_name","source_url","additional_sources_json","last_checked","created_at","updated_at"]
        values = [sql_string(event.get("id")), sql_string(event.get("title")), sql_string(event.get("description", "")), sql_string(event["start"]), sql_string(event.get("end")), sql_string(event["venue"]), sql_string(event.get("address", "")), sql_string(event["town"]), sql_number(event["latitude"]), sql_number(event["longitude"]), sql_string(event["coordinatePrecision"]), sql_number(event.get("ageMin")), sql_number(event.get("ageMax")), sql_string(event["audienceGroup"]), sql_string(event["category"]), sql_string(event["costStatus"]), sql_string(event.get("costLabel", "")), sql_string(event["setting"]), sql_string(event["registrationRequired"]), sql_string(event.get("registrationUrl")), sql_string(event["status"]), sql_string(event.get("accessibility")), sql_string(event["sourceName"]), sql_string(event["sourceUrl"]), sql_string(json.dumps(event.get("additionalSources", []), separators=(",", ":"))), sql_string(event["lastChecked"]), sql_string(published_at), sql_string(published_at)]
        updates = ", ".join(f"{column}=excluded.{column}" for column in columns[1:] if column != "created_at")
        statements.append(f"INSERT INTO events ({','.join(columns)}) VALUES ({','.join(values)}) ON CONFLICT(id) DO UPDATE SET {updates};")
    # Reconcile only sources whose feed completed successfully. Failed feeds
    # retain their existing rows as last-known-good data.
    for configured, current in rows:
        if current["status"] == "fresh":
            ids = sorted(event["id"] for event in payload["events"] if event["sourceName"] == configured["sourceName"])
            if ids:
                quoted = ",".join(sql_string(item) for item in ids)
                statements.append(f"DELETE FROM events WHERE source_name={sql_string(configured['sourceName'])} AND id NOT IN ({quoted});")
            else:
                statements.append(f"DELETE FROM events WHERE source_name={sql_string(configured['sourceName'])};")
    for configured, current in rows:
        values = [sql_string(configured["sourceId"]), sql_string(configured["sourceName"]), sql_string(configured["sourceUrl"]), sql_string(current["status"]), sql_string(current.get("lastSuccessfulRefresh")), sql_string(current.get("lastAttemptAt") or published_at), sql_string(current.get("lastSuccessfulRefresh")), "1" if current.get("status") == "stale" else "0", sql_string(current.get("message")), sql_string(published_at)]
        statements.append("INSERT INTO sources (id,source_name,source_url,status,last_successful_refresh,last_attempt,last_success,using_last_known_good,last_error,updated_at) VALUES (" + ",".join(values) + ") ON CONFLICT(id) DO UPDATE SET source_name=excluded.source_name,source_url=excluded.source_url,status=excluded.status,last_successful_refresh=excluded.last_successful_refresh,last_attempt=excluded.last_attempt,last_success=excluded.last_success,using_last_known_good=excluded.using_last_known_good,last_error=excluded.last_error,updated_at=excluded.updated_at;")
    origin = payload.get("origin", {})
    statements.append("INSERT INTO catalog_metadata (id,generated_at,origin_label,origin_latitude,origin_longitude,updated_at) VALUES (1," + ",".join([sql_string(published_at), sql_string(origin.get("label", "Franklinton, NC 27525")), sql_number(origin.get("latitude", 36.101)), sql_number(origin.get("longitude", -78.458)), sql_string(published_at)]) + ") ON CONFLICT(id) DO UPDATE SET generated_at=excluded.generated_at,origin_label=excluded.origin_label,origin_latitude=excluded.origin_latitude,origin_longitude=excluded.origin_longitude,updated_at=excluded.updated_at WHERE excluded.generated_at >= catalog_metadata.generated_at;")
    statements.append("COMMIT;")
    return "\n".join(statements) + "\n"


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "public" / "data" / "events.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    sys.stdout.write(build_publish_sql(payload))
