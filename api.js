(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.LittleDayOutApi = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const MAX_PAGES = 20;
  const TIMEOUT_MS = 8000;
  const https = (value) => typeof value === "string" && value.length <= 2048 && /^https:\/\/[^\s]+$/i.test(value);
  const timestamp = (value) => typeof value === "string" && value.length <= 40 && !Number.isNaN(Date.parse(value)) && /(?:Z|[+-]\d\d:\d\d)$/.test(value);
  const eventValid = (event) => event && typeof event === "object" && typeof event.id === "string" && event.id.length <= 120 && typeof event.title === "string" && event.title.length <= 500 && timestamp(event.start) && (event.end == null || timestamp(event.end)) && Number.isFinite(event.latitude) && Number.isFinite(event.longitude) && event.latitude >= -90 && event.latitude <= 90 && event.longitude >= -180 && event.longitude <= 180 && https(event.sourceUrl) && typeof event.sourceName === "string" && event.sourceName.trim().length > 0 && (!event.additionalSources || Array.isArray(event.additionalSources) && event.additionalSources.every((source) => source && typeof source.sourceName === "string" && source.sourceName.trim() && https(source.sourceUrl)));
  const sourceValid = (source) => source && typeof source.sourceName === "string" && source.sourceName.trim() && ["fresh", "stale", "unavailable", "disabled"].includes(source.status) && (!source.lastSuccessfulRefresh || timestamp(source.lastSuccessfulRefresh));
  const envelopeValid = (data) => data && data.schemaVersion === 1 && timestamp(data.generatedAt) && Array.isArray(data.events) && data.events.every(eventValid) && Array.isArray(data.sources) && data.sources.every(sourceValid) && Array.isArray(data.sourceFailures);
  const fetchWithTimeout = async (fetchImpl, url, options = {}, timeoutMs = TIMEOUT_MS) => {
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    const timer = setTimeout(() => controller && controller.abort(), timeoutMs);
    try { return await fetchImpl(url, { ...options, ...(controller ? { signal: controller.signal } : {}) }); }
    finally { clearTimeout(timer); }
  };
  async function fetchApi(fetchImpl, apiBase, timeoutMs = TIMEOUT_MS) {
    let cursor = null; const events = []; let first = null;
    for (let page = 0; page < MAX_PAGES; page += 1) {
      const url = `${apiBase.replace(/\/$/, "")}/api/events${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`;
      const response = await fetchWithTimeout(fetchImpl, url, { cache: "no-store" }, timeoutMs);
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      if (!envelopeValid(data) || (data.nextCursor !== null && typeof data.nextCursor !== "string")) throw new Error("API envelope failed validation");
      if (!first) first = data; events.push(...data.events);
      if (!data.hasMore) return { ...first, events, hasMore: false, nextCursor: null };
      if (!data.nextCursor || data.nextCursor === cursor) throw new Error("API pagination cursor repeated or missing");
      cursor = data.nextCursor;
    }
    throw new Error("API pagination exceeded safety cap");
  }
  async function loadCatalog({ fetchImpl = fetch, apiBase = "", staticUrl = "public/data/events.json", timeoutMs = TIMEOUT_MS } = {}) {
    try {
      if (!apiBase) throw new Error("API not configured");
      return { data: await fetchApi(fetchImpl, apiBase, timeoutMs), usingFallback: false, statusText: "Live catalog" };
    } catch (apiError) {
      const response = await fetchWithTimeout(fetchImpl, staticUrl, { cache: "no-store" }, timeoutMs);
      if (!response.ok) throw new Error("Static catalog unavailable");
      const data = await response.json();
      if (!envelopeValid(data)) throw new Error("Static catalog failed validation");
      return { data, usingFallback: true, statusText: "Offline/static catalog (last approved data)" };
    }
  }
  return { loadCatalog, envelopeValid, eventValid, sourceValid, fetchWithTimeout };
});
