/** Read-only public API for the event catalog. Writes belong behind auth. */
const corsHeaders = () => ({ "access-control-allow-origin": "https://aidan-mckeithan.github.io", "vary": "Origin", "x-content-type-options": "nosniff", "referrer-policy": "no-referrer", "content-security-policy": "default-src 'none'; frame-ancestors 'none'" });
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": status >= 400 ? "no-store" : "public, max-age=300, stale-while-revalidate=60", ...corsHeaders() } });
const eventColumns = `id,title,description,start,end,venue,address,town,latitude,longitude,coordinate_precision,age_min,age_max,audience_group,category,cost_status,cost_label,setting,registration_required,registration_url,status,accessibility,source_name,source_url,additional_sources_json,last_checked`;
function eventRow(row) {
  let additionalSources;
  try { additionalSources = JSON.parse(row.additional_sources_json || "[]"); } catch { throw new Error("invalid attribution metadata"); }
  if (!Array.isArray(additionalSources) || additionalSources.some((source) => !source || typeof source !== "object" || typeof source.sourceName !== "string" || !source.sourceName.trim() || typeof source.sourceUrl !== "string" || !/^https:\/\/[^\s]+$/i.test(source.sourceUrl))) throw new Error("invalid attribution metadata");
  return { id: row.id, title: row.title, description: row.description || "", start: row.start, end: row.end, venue: row.venue, address: row.address || "", town: row.town, latitude: row.latitude, longitude: row.longitude, coordinatePrecision: row.coordinate_precision, ageMin: row.age_min, ageMax: row.age_max, audienceGroup: row.audience_group, category: row.category, costStatus: row.cost_status, costLabel: row.cost_label || "", setting: row.setting, registrationRequired: row.registration_required, registrationUrl: row.registration_url, status: row.status, accessibility: row.accessibility || "", sourceName: row.source_name, sourceUrl: row.source_url, additionalSources, lastChecked: row.last_checked };
}
function parseDateOnly(value) { if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null; const date = new Date(`${value}T00:00:00.000Z`); return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value ? null : date; }
function cursorDecode(value) { try { const parsed = JSON.parse(atob(value.replace(/-/g, "+").replace(/_/g, "/"))); return parsed && typeof parsed.start === "string" && typeof parsed.id === "string" ? parsed : null; } catch { return null; } }
function cursorEncode(row) { return btoa(JSON.stringify({ start: row.start, id: row.id })).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
async function eventsResponse(request, env) {
  if (!env.EVENTS_DB) return json({ error: "Event service is not configured" }, 503);
  const url = new URL(request.url), params = [], conditions = ["status != 'cancelled'"];
  const fromValue = url.searchParams.get("from"), toValue = url.searchParams.get("to"), from = fromValue ? parseDateOnly(fromValue) : null, to = toValue ? parseDateOnly(toValue) : null;
  if ((fromValue && !from) || (toValue && !to)) return json({ error: "from and to must be valid dates in YYYY-MM-DD format" }, 400);
  if (from && to && from > to) return json({ error: "from must not be after to" }, 400);
  if (from) { conditions.push("start >= ?"); params.push(`${fromValue}T00:00:00.000Z`); }
  if (to) { conditions.push("start < ?"); params.push(new Date(to.getTime() + 86400000).toISOString()); }
  const cursorValue = url.searchParams.get("cursor"), cursor = cursorValue ? cursorDecode(cursorValue) : null;
  if (cursorValue && !cursor) return json({ error: "cursor is invalid" }, 400);
  if (cursor) { conditions.push("(start > ? OR (start = ? AND id > ?))"); params.push(cursor.start, cursor.start, cursor.id); }
  const requestedLimit = Number(url.searchParams.get("limit") || 500), limit = Number.isInteger(requestedLimit) ? Math.min(Math.max(requestedLimit, 1), 1000) : 500;
  const result = await env.EVENTS_DB.prepare(`SELECT ${eventColumns} FROM events WHERE ${conditions.join(" AND ")} ORDER BY start ASC, id ASC LIMIT ${limit + 1}`).bind(...params).all();
  const hasMore = result.results.length > limit, rows = hasMore ? result.results.slice(0, limit) : result.results;
  const sources = await env.EVENTS_DB.prepare("SELECT source_name, status, last_attempt, last_success, last_successful_refresh, using_last_known_good FROM sources ORDER BY source_name ASC").all();
  const metadata = await env.EVENTS_DB.prepare("SELECT generated_at, origin_label, origin_latitude, origin_longitude FROM catalog_metadata WHERE id = 1").first();
  const generatedAt = metadata?.generated_at || (rows.length ? rows.map((row) => row.last_checked).sort().at(-1) : new Date(0).toISOString());
  return json({ schemaVersion: 1, generatedAt, origin: { label: metadata?.origin_label || "Franklinton, NC 27525", latitude: metadata?.origin_latitude ?? 36.101, longitude: metadata?.origin_longitude ?? -78.458 }, events: rows.map(eventRow), hasMore, nextCursor: hasMore ? cursorEncode(rows[rows.length - 1]) : null, sources: sources.results.map((source) => ({ sourceName: source.source_name, status: source.status, lastAttempt: source.last_attempt, lastSuccessfulRefresh: source.last_success || source.last_successful_refresh, usingLastKnownGood: Boolean(source.using_last_known_good) })), sourceFailures: sources.results.filter((source) => ["stale", "unavailable"].includes(source.status)).map((source) => ({ sourceName: source.source_name, status: source.status, usingLastKnownGood: Boolean(source.using_last_known_good) })) });
}
export default { async fetch(request, env) { const url = new URL(request.url); if (request.method !== "GET") return json({ error: "Method not allowed" }, 405); if (url.pathname === "/api/health") return json({ ok: Boolean(env.EVENTS_DB), service: "little-day-out-api" }, env.EVENTS_DB ? 200 : 503); if (url.pathname === "/api/events") { try { return await eventsResponse(request, env); } catch { return json({ error: "Event catalog temporarily unavailable" }, 503); } } return json({ error: "Not found" }, 404); } };
