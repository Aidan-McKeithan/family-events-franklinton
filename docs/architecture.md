# System architecture

## Overview

The system separates event collection from the website shown to caregivers.

```text
approved public calendars
          |
          v
scheduled GitHub Actions collector
  fetch -> normalize -> deduplicate -> validate
          |
          v
public/data/events.json
          |
          v
static mobile-first website on GitHub Pages
```

The browser will not scrape third-party sites. A scheduled workflow will build a small, validated dataset from approved sources. GitHub Pages will serve both the static interface and the dataset for free.

## Planned repository boundaries

```text
docs/                    Requirements and architecture decisions
src/                     Browser interface, filtering, and rendering
public/data/             Validated event data consumed by the browser
scripts/ingest/          Source adapters and normalization pipeline
tests/unit/              Deterministic application and data tests
tests/fixtures/          Saved source examples for repeatable tests
.github/workflows/       Verification, refresh, and deployment jobs
```

## Canonical event model

An event will contain:

- Stable identifier
- Title and description
- Start and end timestamps with timezone
- Venue and address
- Latitude and longitude used to calculate distance locally from fixed origin 27525
- Minimum and maximum suitable age, each nullable
- Categories
- Cost status and optional price
- Indoor/outdoor status
- Registration requirement
- Optional registration URL
- Active, postponed, or cancelled status
- Accessibility information when published
- One or more official source names and URLs
- Last successful check time

Missing information is represented explicitly. Collectors must not infer facts that a source does not provide.

The MVP origin is fixed at Franklinton, NC 27525. The browser calculates distance from bundled coordinates, so changing the radius does not disclose location to another service. Supporting arbitrary origins later will require a separate privacy and geocoding design decision.

Age matching uses inclusive bounds. A null minimum or maximum is open-ended. Events with no published age information are not treated as definite matches; they are displayed in a separate, optional group that asks the caregiver to verify suitability.

Each occurrence in a recurring series has its own stable identifier. When multiple sources describe the same occurrence, normalization keeps all source URLs and resolves conflicting fields using a documented official-source priority.

## Initial source policy

Prefer official municipal, county, library, parks, museum, and organizer calendars. An automated adapter may be added only after confirming that a public feed, API, or permitted retrieval method is available. Broad commercial event APIs are supplemental because they often miss free library and toddler programs.

Initial candidates include:

- Franklin County official calendar and library listings
- Town of Franklinton Parks and Recreation
- Town of Youngsville public events
- Granville County and library public events within the radius
- Arts Council of Franklin County

The first automated adapters use the official Franklin County and Granville County iCalendar subscription feeds. Calendars without an official structured feed remain manual candidates until their retrieval policy and reliability are established.

Before automating a source, its adapter documentation must record the approved feed/API/retrieval method, supporting terms or robots decision, and the date checked.

## Failure behavior

- Validate new data before publication.
- Never replace valid data with an invalid or empty refresh.
- Retain the last known good dataset when collection fails.
- Display dataset freshness in the interface.
- Track freshness independently for each source so one successful adapter cannot conceal another stale source.
- Label postponed events and exclude cancelled events from ordinary active results.
- Log which source adapter failed without leaking credentials.

## GitHub delivery flow

1. The architect defines a bounded requirement and acceptance criteria.
2. The builder works on a feature branch and pushes small checkpoints.
3. Continuous integration runs tests and validation on the pull request.
4. A separate verifier reviews the diff and test evidence.
5. Findings return to the builder until blocking issues are resolved.
6. The architect makes the final merge decision.

Agents operating through the same GitHub identity cannot provide organizationally independent GitHub approvals. Their review remains useful, while automated checks and the human architect provide the merge gate.
