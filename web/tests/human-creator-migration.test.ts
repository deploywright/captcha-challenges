import { describe, expect, it, vi } from "vitest";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
vi.mock("server-only",() => ({}));
import { HumanStore } from "../lib/human-benchmark/store.server";
import { CATALOG } from "../lib/challenges/catalog";
import { applyHumanMigration } from "./helpers/human-migrations";

describe("creator schema upgrade", () => {
  it("preserves populated 0001 data, indexes, triggers and foreign keys before allowing creator", async () => {
    const mf = new Miniflare(convertV4MiniflareOptions({modules:true,script:"export default {fetch(){return new Response('test')}}",d1Databases:["DB"],compatibilityDate:"2024-09-23"}));
    try {
      const db = await mf.getD1Database("DB");await applyHumanMigration(db,"0001_human_benchmark.sql");
      const store = new HumanStore(db);
      for(const cohort of ["main","pilot","smoke"] as const) {
        const {session} = await store.create(crypto.randomUUID(),cohort,"desktop","large",CATALOG);
        const trial = (await store.current(session.session_id))!;
        await store.finish(session,trial,"test-fingerprint",undefined,false,true,false,0,false);
      }
      const tables = ["human_participants","human_sessions","human_trials","human_protocol_state","human_challenge_exposure","human_rate_limits"];
      const before = await Promise.all(tables.map(table => db.prepare(`SELECT * FROM ${table} ORDER BY 1,2`).all()));
      const schemaBefore = (await db.prepare("SELECT type,name,sql FROM sqlite_schema WHERE type IN ('index','trigger') AND sql IS NOT NULL ORDER BY name").all<{type:string;name:string;sql:string}>()).results;
      await applyHumanMigration(db,"0002_creator_cohort.sql");
      const after = await Promise.all(tables.map(table => db.prepare(`SELECT * FROM ${table} ORDER BY 1,2`).all()));
      after.forEach((value,index) => expect(value.results,tables[index]).toEqual(before[index].results));
      const schemaAfter = (await db.prepare("SELECT type,name,sql FROM sqlite_schema WHERE type IN ('index','trigger') AND sql IS NOT NULL ORDER BY name").all<{type:string;name:string;sql:string}>()).results;
      for(const original of schemaBefore) {
        const retained = schemaAfter.find(row => row.name === original.name)!;
        expect(retained.type).toBe(original.type);expect(retained.sql.replace(/\s+/g," ")).toBe(original.sql.replace(/\s+/g," "));
      }
      expect((await db.prepare("PRAGMA foreign_key_check").all()).results).toEqual([]);
      const {session} = await store.create(crypto.randomUUID(),"creator","desktop","large",CATALOG);
      expect(session.cohort).toBe("creator");
      const trial = (await store.current(session.session_id))!;
      await store.finish(session,trial,"creator-fingerprint",undefined,false,true,false,0,false);
      expect((await store.getSession(session.session_id)).skipped_count).toBe(1);
      expect(await db.prepare("SELECT assigned_count,completed_count FROM human_challenge_exposure WHERE cohort = 'creator' AND challenge_id = ?").bind(trial.challenge_id).first()).toEqual({assigned_count:1,completed_count:1});
      await expect(db.prepare("UPDATE human_trials SET correct = 1 WHERE trial_id = ?").bind(trial.trial_id).run()).rejects.toThrow("HB_TRIAL_FINAL");
      // Bypass the application guard to prove the partial unique index itself.
      await db.prepare("UPDATE human_sessions SET assignment_revision = (SELECT revision FROM human_protocol_state WHERE cohort = 'creator' AND protocol_version = 'human-v1') WHERE session_id = ?").bind(session.session_id).run();
      await expect(db.prepare("INSERT INTO human_sessions SELECT ?,participant_id,?,protocol_version,cohort,assignment_seed,assignment_revision,status,consented_at,created_at,started_at,completed_at,device_class,viewport_bucket,assigned_count,answered_count,skipped_count,timeout_count FROM human_sessions WHERE session_id = ?").bind(crypto.randomUUID(),"different-hash",session.session_id).run()).rejects.toThrow("UNIQUE constraint failed");
      expect((await db.prepare("PRAGMA foreign_key_check").all()).results).toEqual([]);
    } finally {await mf.dispose();}
  },30_000);
});
