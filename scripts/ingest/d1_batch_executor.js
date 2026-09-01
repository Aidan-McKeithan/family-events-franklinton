/** D1-compatible publication helper. D1 batch execution is atomic. */
export async function publishCatalog(db, statements, expectedGeneratedAt, nextGeneratedAt) {
  if (!db || !Array.isArray(statements) || !nextGeneratedAt) throw new Error("invalid publication arguments");
  const current = await db.prepare("SELECT generated_at FROM catalog_metadata WHERE id = 1").first();
  if (current?.generated_at && !expectedGeneratedAt) throw new Error("expected catalog snapshot is required");
  if (current?.generated_at && expectedGeneratedAt && current.generated_at !== expectedGeneratedAt) throw new Error("catalog changed; regenerate before publishing");
  if (current?.generated_at && current.generated_at > nextGeneratedAt) throw new Error("refusing to publish an older catalog snapshot");
  // A duplicate primary key deliberately aborts the batch if the snapshot
  // changed between the read above and this CAS statement. D1 rolls back the
  // complete batch, including all event/source mutations.
  const guard = db.prepare("INSERT INTO catalog_publish_guard (id, generated_at) SELECT 1, ? WHERE EXISTS (SELECT 1 FROM catalog_metadata WHERE id=1 AND generated_at != ?)").bind(nextGeneratedAt, expectedGeneratedAt || "");
  const advance = db.prepare("INSERT INTO catalog_publish_guard (id, generated_at) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET generated_at=excluded.generated_at").bind(nextGeneratedAt);
  return db.batch([guard, ...statements.map((sql) => db.prepare(sql)), advance]);
}
