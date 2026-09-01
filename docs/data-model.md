# Event platform data model

This is the migration contract for replacing the static event list with a
server-side event and places service. The current `public/data/events.json`
remains the read-only fallback until API parity and failure tests pass.

## Trust boundary

```text
source registry / submissions
             |
             v
candidate fetch -> extraction (AI may assist) -> deterministic validation
             |                                      |
             +---------- rejected/quarantined <-----+
                                                    v
                                             approved records
                                                    |
                                           API and app filters
```

An AI model may extract fields from a source page, classify a category, or
suggest a duplicate. It may not invent missing details, publish directly, or
replace the official URL. Missing age, cost, location, and registration facts
remain `null`/`unknown`.

## Source registry

Each monitored source has a stable `sourceId`, retrieval method (`ical`,
`rss`, `api`, `web`, or `submission`), canonical HTTPS URL, enabled flag,
refresh timestamps, status, failure count, and optional terms/robots review
note. Source health is tracked independently so a failed source cannot erase
good data from another source.

Validator limits are intentional API guardrails: IDs are 1–120 characters
using URL-safe ASCII characters, names are at most 200 characters, URLs are at
most 2,048 characters, timestamps must include a timezone, coordinates and
ages are finite numbers in their documented ranges, and a submission payload
is at most 64 KiB. Python booleans are not accepted where numbers are required.

## Places

Places use the same provenance and freshness conventions as events: stable ID,
official URL, coordinates (with precision), optional ages, setting, cost,
amenities, phone, and `lastChecked`. A place is a fallback recommendation when
no matching event exists; it is not silently presented as an event.

## Submissions and promotions

Anyone may submit an event or place for free. A submission remains `pending`,
`needs-review`, `approved`, or `rejected` until validation and moderation
complete. A promotion references an approved event/place and has a bounded
time window. It affects ranking only and must display the literal `Sponsored`
label. It must not alter the event's source, facts, ratings, or safety filters.

Analytics store aggregate action counts (view, website, call, directions,
registration, coupon). Do not store child names, precise location trails,
browsing histories, or sell personal data.

## Refresh contract

The API should return `generatedAt`, per-source health, and the last successful
refresh. A failed refresh keeps the last-known-good record. Radius changes are
local database/API filters over a broad regional dataset; they do not require a
new model call or expose a family's location to a third party.
