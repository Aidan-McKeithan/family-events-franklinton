# Validated catalog publisher

`scripts/ingest/publish.py` converts a validated collector envelope into a
deterministic list of D1 statements. It is deliberately offline: it reads a payload
and source manifest, but does not fetch feeds, call an AI model, or require
Cloudflare credentials.

The generated batch upserts events and source health, then updates
`catalog_metadata` as its final catalog operation. Validation happens before
the transaction is emitted. Failed or partial source refreshes preserve
last-known-good records; successful sources reconcile their owned events and
attributions, including tombstoning records removed from the source. A future Worker
or scheduled job can execute this SQL only after authentication and complete
batch validation.

Cloudflare D1 imports do not accept explicit `BEGIN`/`COMMIT` or temporary
tables. `scripts/ingest/d1_batch_executor.js` checks the current snapshot before
calling D1's atomic `batch()` API, so an older or concurrently superseded batch
fails before any event, source, or reconciliation mutation. Reconciliation
uses both an event's primary source and its `additionalSources` attribution, so
a fresh source cannot accidentally delete an event also published by it when a
different source is stale.
The permanent `catalog_publish_guard` row is seeded by migration; a changed
snapshot causes a deliberate duplicate-key failure in the first batch statement.

Callers that already know the database snapshot should pass its timestamp as
`current_generated_at`; older payloads are rejected. Equal timestamps remain
idempotent, while a later complete batch can advance the catalog snapshot.

The manifest in `scripts/ingest/source_manifest.json` is the sole authoritative
allowlist for official iCal feeds. Adding a feed requires its HTTPS source URL,
retrieval method, and a corresponding collector adapter review.

The authenticated execution path is `scripts/ingest/publish_admin_worker.js`.
It accepts bearer-authenticated publication requests and invokes the D1 batch
helper. Store `CATALOG_PUBLISH_TOKEN` as a Worker secret; never commit it.
The scheduled GitHub workflow only validates and generates statements until
this endpoint is deliberately deployed.

`package_publication.py` creates the exact request envelope: `statements`,
`expectedGeneratedAt`, and `nextGeneratedAt`. The migration seeds guard row
`id=1` at `1970-01-01T00:00:00Z`; the first batch CAS statement collides with
that permanent row when the catalog snapshot changed, so D1 atomically rolls
back before any mutation.
