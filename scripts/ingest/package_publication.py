#!/usr/bin/env python3
"""Package validated D1 statements for the authenticated publication Worker."""
import argparse, json
from pathlib import Path
from scripts.ingest.publish import build_publish_sql

def split_sql(sql):
    statements, start, quoted, index = [], 0, False, 0
    while index < len(sql):
        if sql[index] == "'":
            if quoted and index + 1 < len(sql) and sql[index + 1] == "'": index += 1
            else: quoted = not quoted
        elif sql[index] == ";" and not quoted:
            value = sql[start:index].strip()
            if value: statements.append(value + ";")
            start = index + 1
        index += 1
    if sql[start:].strip(): statements.append(sql[start:].strip())
    return statements

def package(payload, expected_generated_at=None):
    sql = build_publish_sql(payload, published_at=payload["generatedAt"], current_generated_at=expected_generated_at)
    return {"schemaVersion": 1, "expectedGeneratedAt": expected_generated_at, "nextGeneratedAt": payload["generatedAt"], "statements": split_sql(sql)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("payload", type=Path); parser.add_argument("output", type=Path); parser.add_argument("--expected-generated-at")
    args = parser.parse_args(); payload = json.loads(args.payload.read_text(encoding="utf-8")); args.output.write_text(json.dumps(package(payload, args.expected_generated_at), indent=2) + "\n", encoding="utf-8")
