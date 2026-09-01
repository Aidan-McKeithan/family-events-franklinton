# Backend event catalog

The static `public/data/events.json` remains the GitHub Pages fallback while the
server-side catalog is introduced. The Cloudflare Worker in `worker.js` exposes
read-only `GET /api/events` and `GET /api/health` endpoints backed by D1. It
accepts optional `from`, `to`, and bounded `limit` query parameters. Radius and
age filtering remain in the browser so changing the slider is instantaneous and
does not disclose a caregiver's location to the service.

## Local/Cloudflare setup

1. Copy `wrangler.toml.example` to `wrangler.toml` and fill in a D1 database ID.
2. Apply all migrations in `db/migrations/` with Wrangler (currently `0001_initial.sql` and `0002_catalog_hardening.sql`).
3. Load only validated catalog rows from the existing collector; do not expose
   write endpoints publicly.
4. Deploy the Worker and configure the website's API base URL in a later slice.

The Worker returns the static dataset's event fields plus an intentional API
superset: origin coordinates, source health, and opaque cursor pagination.
Until a deployment is configured, the browser must continue using
`public/data/events.json`. Dates and timestamps are UTC; cursors are opaque and
must only be replayed with the same query filters.
An unavailable database returns `503`, allowing the client to retain its static
fallback. No API keys or business credentials belong in browser code.
