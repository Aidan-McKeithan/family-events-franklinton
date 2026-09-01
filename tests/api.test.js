const test = require("node:test");
const assert = require("node:assert/strict");
const { loadCatalog } = require("../api.js");

const event = (id) => ({ id, title: "Storytime", start: "2026-09-01T12:00:00Z", end: null, latitude: 36, longitude: -78, sourceName: "Library", sourceUrl: "https://example.org/event", additionalSources: [] });
const page = (events, extra = {}) => ({ schemaVersion: 1, generatedAt: "2026-09-01T12:00:00Z", origin: { label: "Franklinton, NC 27525", latitude: 36.101, longitude: -78.458 }, events, sources: [{ sourceName: "Library", status: "fresh", lastSuccessfulRefresh: "2026-09-01T12:00:00Z" }], sourceFailures: [], hasMore: false, nextCursor: null, ...extra });
const response = (body, ok = true, status = 200) => ({ ok, status, json: async () => body });

test("follows opaque cursors without age or location query parameters", async () => {
  const urls = [];
  const fetchImpl = async (url) => { urls.push(url); return response(url.includes("cursor=") ? page([event("2")]) : page([event("1")], { hasMore: true, nextCursor: "opaque" })); };
  const result = await loadCatalog({ apiBase: "https://api.example", fetchImpl });
  assert.deepEqual(result.data.events.map((item) => item.id), ["1", "2"]);
  assert.ok(urls.every((url) => !/[?&](age|lat|lon|location|radius)=/i.test(url)));
});

test("falls back to static data on 503, malformed data, repeated cursor, and timeout", async () => {
  const staticData = page([event("static")]);
  for (const mode of ["503", "malformed", "repeat", "timeout"]) {
    const fetchImpl = async (url, options = {}) => {
      if (url === "public/data/events.json") return response(staticData);
      if (mode === "timeout") return new Promise((resolve, reject) => options.signal?.addEventListener("abort", () => reject(new Error("aborted")), { once: true }));
      if (mode === "repeat") return response(page([event("1")], { hasMore: true, nextCursor: "same" }));
      if (mode === "503") return response({}, false, 503);
      return response({ bad: true });
    };
    const result = await loadCatalog({ apiBase: "https://api.example", fetchImpl, staticUrl: "public/data/events.json", timeoutMs: 1 });
    assert.equal(result.usingFallback, true);
    assert.equal(result.data.events[0].id, "static");
  }
});

test("rejects an event with invalid attribution", async () => {
  const bad = page([{ ...event("bad"), sourceUrl: "http://not-https.example" }]);
  const fetchImpl = async (url) => url === "public/data/events.json" ? response(page([event("static")])) : response(bad);
  const result = await loadCatalog({ apiBase: "https://api.example", fetchImpl });
  assert.equal(result.usingFallback, true);
});

test("falls back when pages repeat an ID or change snapshot metadata", async () => {
  const staticData = page([event("static")]);
  for (const second of [page([event("1")]), page([event("2")], { generatedAt: "2026-09-02T12:00:00Z" })]) {
    let count = 0;
    const fetchImpl = async (url) => {
      if (url === "public/data/events.json") return response(staticData);
      count += 1;
      return count === 1 ? response(page([event("1")], { hasMore: true, nextCursor: "next" })) : response(second);
    };
    const result = await loadCatalog({ apiBase: "https://api.example", fetchImpl });
    assert.equal(result.usingFallback, true);
  }
});
