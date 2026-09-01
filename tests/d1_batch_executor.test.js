import test from "node:test";
import assert from "node:assert/strict";
import { publishCatalog } from "../scripts/ingest/d1_batch_executor.js";

function mockDb(snapshot, failBatch = false) {
  const calls = [];
  return { calls, prepare(sql) { const item = { sql, bind(...values) { item.values = values; return item; } }; calls.push(item); return item; }, async batch(items) { if (failBatch) throw new Error("batch failed"); return items; }, async _snapshot() { return snapshot; } };
}

for (const [name, snapshot, expected, next, shouldReject] of [
  ["stale", "2026-09-02T00:00:00Z", "2026-09-01T00:00:00Z", "2026-09-03T00:00:00Z", true],
  ["equal", "2026-09-01T00:00:00Z", "2026-09-01T00:00:00Z", "2026-09-02T00:00:00Z", false],
  ["newer", "2026-09-01T00:00:00Z", "2026-09-01T00:00:00Z", "2026-09-02T00:00:00Z", false]
]) test(`CAS ${name} snapshot`, async () => {
  const db = mockDb(snapshot);
  db.prepare = (sql) => { if (sql.startsWith("SELECT")) return { first: async () => ({ generated_at: snapshot }) }; const item = { sql, bind(...values) { item.values = values; return item; } }; db.calls.push(item); return item; };
  if (shouldReject) await assert.rejects(() => publishCatalog(db, ["UPDATE events SET title='x'"], expected, next));
  else { await publishCatalog(db, ["UPDATE events SET title='x'"], expected, next); assert.match(db.calls[0].sql, /catalog_publish_guard/); }
});

test("batch failure is surfaced for atomic rollback", async () => {
  const db = mockDb(null, true);
  db.prepare = (sql) => { if (sql.startsWith("SELECT")) return { first: async () => null }; const item = { sql, bind(...values) { item.values = values; return item; } }; return item; };
  await assert.rejects(() => publishCatalog(db, [], undefined, "2026-09-01T00:00:00Z"), /batch failed/);
});

test("interleaving CAS failure occurs inside batch", async () => {
  const db = mockDb("2026-09-01T00:00:00Z");
  db.prepare = (sql) => { if (sql.startsWith("SELECT")) return { first: async () => ({ generated_at: "2026-09-01T00:00:00Z" }) }; const item = { sql, bind(...values) { item.values = values; return item; } }; return item; };
  db.batch = async (items) => { assert.match(items[0].sql, /catalog_publish_guard/); throw new Error("CAS guard conflict"); };
  await assert.rejects(() => publishCatalog(db, ["UPDATE events SET title='x'"], "2026-09-01T00:00:00Z", "2026-09-02T00:00:00Z"), /CAS guard conflict/);
});
