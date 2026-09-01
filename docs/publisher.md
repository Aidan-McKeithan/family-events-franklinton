# Validated catalog publisher

`scripts/ingest/publish.py` converts a validated collector envelope into one
deterministic D1 transaction. It is deliberately offline: it reads a payload
and source registry, but does not fetch feeds, call an AI model, or require
Cloudflare credentials.

The transaction upserts events and source health, then updates
`catalog_metadata` as its final catalog operation. Validation happens before
the transaction is emitted. Existing event rows are not deleted, so a failed
or partial source refresh preserves last-known-good records. A future Worker
or scheduled job can execute this SQL only after authentication and complete
batch validation.

The transaction begins with a uniqueness-based snapshot guard. An older batch
fails before any event, source, or reconciliation mutation. Reconciliation
uses both an event's primary source and its `additionalSources` attribution, so
a fresh source cannot accidentally delete an event also published by it when a
different source is stale.

Callers that already know the database snapshot should pass its timestamp as
`current_generated_at`; older payloads are rejected. Equal timestamps remain
idempotent, while a later complete batch can advance the catalog snapshot.

The manifest in `scripts/ingest/source_manifest.json` is the sole authoritative
allowlist for official iCal feeds. Adding a feed requires its HTTPS source URL,
retrieval method, and a corresponding collector adapter review.
