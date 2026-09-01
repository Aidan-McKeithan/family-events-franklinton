# Product requirements

## Purpose

Help a caregiver quickly find trustworthy, nearby activities suitable for a child without searching several community calendars.

## Primary user

A caregiver using a phone who wants a useful answer to: "What can we do today?"

## MVP defaults

- Search origin: Franklinton, NC 27525
- Radius: 20 miles
- Date: today in America/New_York
- Child age: 2.5 years

The date, child age, and radius defaults must be adjustable. The MVP search origin is fixed at Franklinton, NC 27525 so that distance calculations remain local, predictable, and private. Adjustable origins may be considered after the MVP.

## Required filters

- Date or date range
- Child age
- Distance
- Free, paid, or cost unknown
- Indoor, outdoor, or unknown
- Category
- Registration required, not required, or unknown

Unknown information must remain visible as unknown and must never be guessed.

For an age selection, a definite match satisfies `ageMin <= selectedAge <= ageMax`; a missing minimum or maximum is an open bound. Events with no published age information appear by default in a separate "Age not specified - verify suitability" group. The caregiver can exclude that group.

Selecting a definite value such as "Free," "Indoor," or "Registration not required" returns definite matches only. An "Include unknown" control can add clearly labeled unknown results.

## Event cards

Each card should show, when available:

- Title
- Date and time
- Venue and town
- Distance from the selected origin
- Suitable age range
- Cost
- Indoor or outdoor status
- Category
- Registration requirement
- Official source link
- Registration link when different from the source
- Active, postponed, or cancelled status
- Time the listing was last checked

The interface must remind users to verify details and cancellations with the organizer.

## Privacy and safety

- Do not create child profiles or collect a child's name.
- Do not transmit the selected age or location to an analytics service.
- Preferences may be stored only in the user's browser.
- No secret or API credential may be shipped to the browser.
- Official source links must remain available for verification.

## MVP acceptance criteria

1. The mobile landing page defaults to today, age 2.5, and 20 miles from 27525.
2. A caregiver can adjust or clear every filter.
3. Filtering behaves deterministically at age, date, and distance boundaries.
4. Events with unknown age or cost are labeled rather than silently discarded.
5. Duplicate events collapse while retaining every source attribution; recurring occurrences remain distinct events.
6. Collection failure preserves the last known good dataset and exposes freshness for the dataset and each source.
7. The interface is keyboard usable, has visible focus, and has readable contrast.
8. Automated schema, unit, ingestion-fixture, timezone/DST, link, accessibility-smoke, security, and build checks pass.
9. An independent reviewer resolves all blocking findings before merge.

## Out of scope for the MVP

- User accounts
- Advertising
- Payments or ticket sales
- Tracking a child's identity or precise live location
- Guaranteeing that an organizer has not changed or cancelled an event
