import fs from "node:fs";

/** D1 batch keeps the real migration atomic, including complete trigger bodies. */
export async function applyHumanMigration(db: D1Database, filename: string) {
  const statements: string[] = []; let current = ""; let trigger = false;
  for(const line of fs.readFileSync(`migrations/${filename}`,"utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("--")) continue;
    current += `${trimmed} `;
    if (/^CREATE TRIGGER/i.test(trimmed)) trigger = true;
    if (trigger ? /^(?:END;|BEGIN\b.*\bEND;)$/.test(trimmed) : trimmed.endsWith(";")) {
      statements.push(current);current="";trigger=false;
    }
  }
  if (current) throw new Error(`Incomplete migration statement in ${filename}`);
  await db.batch(statements.map(sql => db.prepare(sql)));
}

export async function applyHumanMigrations(db: D1Database) {
  for(const filename of fs.readdirSync("migrations").filter(name => name.endsWith(".sql")).sort()) await applyHumanMigration(db,filename);
}
