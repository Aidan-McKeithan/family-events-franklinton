import { publishCatalog } from "./d1_batch_executor.js";

// Deploy separately or behind an access rule. The token is a Worker secret.
export default { async fetch(request, env) {
  if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });
  const token = request.headers.get("Authorization")?.replace(/^Bearer\s+/i, "");
  if (!env.CATALOG_PUBLISH_TOKEN || token !== env.CATALOG_PUBLISH_TOKEN) return new Response("Unauthorized", { status: 401 });
  let input; try { input = await request.json(); } catch { return new Response("Invalid JSON", { status: 400 }); }
  if (!Array.isArray(input.statements) || input.statements.some((sql) => typeof sql !== "string" || !/^\s*(INSERT|UPDATE|DELETE)\b/i.test(sql))) return new Response("Invalid publication statements", { status: 400 });
  try { await publishCatalog(env.EVENTS_DB, input.statements, input.expectedGeneratedAt, input.nextGeneratedAt); return Response.json({ ok: true, statementCount: input.statements.length }); }
  catch (error) { return Response.json({ ok: false, error: error.message }, { status: 409 }); }
} };
