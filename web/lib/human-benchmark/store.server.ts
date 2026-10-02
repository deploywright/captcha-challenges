import "server-only";
import { assignChallenges } from "./assignment";
import { PROTOCOL_VERSION, TOTAL_TRIALS } from "./protocol";
import type { Cohort } from "./protocol";
import type { ChallengeCatalogEntry } from "../challenges/types";
import { BenchmarkError, hashToken, opaqueToken } from "./security.server";

export interface SessionRow {
  session_id: string; participant_id: string; protocol_version: string; cohort: Cohort;
  status: "created" | "active" | "completed" | "abandoned";
  assigned_count: number; answered_count: number; skipped_count: number; timeout_count: number;
}
export interface TrialRow {
  trial_id: string; session_id: string; position: number; challenge_id: string;
  variant: string; subtype: string | null; difficulty: string | null;
  resolution: number | null; series_id: string | null;
  status: "assigned" | "presented" | "answered" | "skipped" | "timed_out";
  presented_at: number | null; answered_at: number | null; submission_fingerprint: string | null;
  correct: number | null; skipped: number; timed_out: number;
  client_solve_time_ms: number | null; interrupted: number;
}

export class HumanStore {
  constructor(public db: D1Database, public now = () => Date.now()) {}

  async authenticate(token: string | undefined) {
    if (!token || !/^[a-f0-9]{64}$/.test(token)) throw new BenchmarkError(401,"Please start or resume your benchmark.");
    const session = await this.db.prepare("SELECT * FROM human_sessions WHERE session_token_hash = ? AND protocol_version = ?").bind(await hashToken(token),PROTOCOL_VERSION).first<SessionRow>();
    if (!session) throw new BenchmarkError(401,"Please start or resume your benchmark.");
    return session;
  }
  async getSession(id: string) {
    const session = await this.db.prepare("SELECT * FROM human_sessions WHERE session_id = ?").bind(id).first<SessionRow>();
    if (!session) throw new BenchmarkError(404,"Session is unavailable.");
    return session;
  }
  async current(sessionId: string) {
    return this.db.prepare("SELECT * FROM human_trials WHERE session_id = ? AND status IN ('assigned','presented') ORDER BY position LIMIT 1").bind(sessionId).first<TrialRow>();
  }
  async trial(sessionId: string, trialId: string) {
    return this.db.prepare("SELECT * FROM human_trials WHERE session_id = ? AND trial_id = ?").bind(sessionId,trialId).first<TrialRow>();
  }
  async limit(bucket: string, maximum: number) {
    const now = this.now();
    const row = await this.db.prepare(`INSERT INTO human_rate_limits(bucket,window_start,request_count) VALUES (?, ?, 1)
      ON CONFLICT(bucket) DO UPDATE SET request_count = CASE WHEN window_start <= ? THEN 1 ELSE request_count + 1 END,
      window_start = CASE WHEN window_start <= ? THEN excluded.window_start ELSE window_start END
      RETURNING request_count`).bind(bucket,now,now-60_000,now-60_000).first<{request_count:number}>();
    if (!row || row.request_count > maximum) throw new BenchmarkError(429,"Please wait a moment before trying again.");
    await this.db.prepare("DELETE FROM human_rate_limits WHERE window_start < ?").bind(now-86_400_000).run();
  }
  async create(participantId: string, cohort: Cohort, deviceClass: string, viewportBucket: string, catalog: readonly ChallengeCatalogEntry[]) {
    await this.limit(`start:${participantId}`,3);
    const existing = (cohort === "main" || cohort === "creator") && await this.db.prepare("SELECT status FROM human_sessions WHERE participant_id = ? AND protocol_version = ? AND cohort = ?").bind(participantId,PROTOCOL_VERSION,cohort).first<{status:string}>();
    if (existing) throw new BenchmarkError(409,existing.status === "completed" ? "You already completed this benchmark." : `This browser already has a ${cohort} session. Use its original session cookie to resume.`);
    const sessionId = crypto.randomUUID();
    const token = opaqueToken();
    const tokenHash = await hashToken(token);
    const seed = opaqueToken();
    const now = this.now();
    await this.db.prepare("INSERT OR IGNORE INTO human_protocol_state(protocol_version,cohort,revision) VALUES (?,?,0)").bind(PROTOCOL_VERSION,cohort).run();
    for (let attempt = 0; attempt < 6; attempt++) {
      const snapshot = await this.db.batch([
        this.db.prepare("SELECT revision FROM human_protocol_state WHERE protocol_version = ? AND cohort = ?").bind(PROTOCOL_VERSION,cohort),
        this.db.prepare("SELECT challenge_id,assigned_count FROM human_challenge_exposure WHERE protocol_version = ? AND cohort = ?").bind(PROTOCOL_VERSION,cohort),
      ]);
      const revision = (snapshot[0].results[0] as {revision:number}).revision;
      const countRows = snapshot[1].results as {challenge_id:string;assigned_count:number}[];
      const counts = Object.fromEntries(countRows.map(row => [row.challenge_id,row.assigned_count]));
      const assignment = assignChallenges(catalog,counts,seed);
      const statements = [
        this.db.prepare("INSERT OR IGNORE INTO human_participants(participant_id,created_at) VALUES (?,?)").bind(participantId,now),
        this.db.prepare(`INSERT INTO human_sessions(session_id,participant_id,session_token_hash,protocol_version,cohort,assignment_seed,assignment_revision,status,consented_at,created_at,started_at,device_class,viewport_bucket,assigned_count)
          VALUES (?,?,?,?,?,?,?,'created',?,?,?,?,?,?)`).bind(sessionId,participantId,tokenHash,PROTOCOL_VERSION,cohort,seed,revision,now,now,now,deviceClass,viewportBucket,TOTAL_TRIALS),
        ...assignment.map((c,index) => this.db.prepare(`INSERT INTO human_trials(trial_id,session_id,position,challenge_id,variant,subtype,difficulty,resolution,series_id,assigned_at)
          VALUES (?,?,?,?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),sessionId,index+1,c.id,c.variant,c.subtype ?? null,c.difficulty ?? null,c.resolution ?? null,c.seriesId ?? null,now)),
        this.db.prepare("UPDATE human_sessions SET status = 'active' WHERE session_id = ?").bind(sessionId),
      ];
      try {
        await this.db.batch(statements);
        return {session:await this.getSession(sessionId),token};
      } catch(error) {
        const message = error instanceof Error ? error.message : "";
        if (message.includes("HB_ASSIGNMENT_CONFLICT")) continue;
        if (message.includes("human_sessions.participant_id")) throw new BenchmarkError(409,`This browser already has a ${cohort} session.`);
        throw error;
      }
    }
    throw new BenchmarkError(503,"The benchmark is busy. Please try starting again shortly.");
  }
  async present(session: SessionRow, trialId: string) {
    if (session.status !== "active") throw new BenchmarkError(409,"This session is closed.");
    const trial = await this.current(session.session_id);
    if (!trial || trial.trial_id !== trialId) throw new BenchmarkError(409,"This is not the current trial. Resume the session.");
    await this.db.prepare("UPDATE human_trials SET presented_at = ?, status = 'presented' WHERE trial_id = ? AND status = 'assigned'").bind(this.now(),trialId).run();
    return (await this.trial(session.session_id,trialId))!;
  }
  async finish(session: SessionRow, trial: TrialRow, fingerprint: string, answer: unknown, correct: boolean, skipped: boolean, timedOut: boolean, clientTime: number, interrupted: boolean) {
    const now = this.now();
    const elapsed = trial.presented_at === null ? 0 : Math.max(0,now-trial.presented_at);
    await this.db.prepare(`UPDATE human_trials SET status = ?, answered_at = ?, submitted_answer_json = ?, submission_fingerprint = ?, correct = ?, skipped = ?, timed_out = ?, client_solve_time_ms = ?, server_elapsed_ms = ?, interrupted = ?
      WHERE trial_id = ? AND session_id = ? AND status IN ('assigned','presented')
      AND EXISTS (SELECT 1 FROM human_sessions WHERE session_id = ? AND status = 'active')
      AND position = (SELECT MIN(position) FROM human_trials WHERE session_id = ? AND status IN ('assigned','presented'))`)
      .bind(timedOut ? "timed_out" : skipped ? "skipped" : "answered",now,answer === undefined ? null : JSON.stringify(answer),fingerprint,correct ? 1 : 0,skipped ? 1 : 0,timedOut ? 1 : 0,clientTime,elapsed,interrupted ? 1 : 0,trial.trial_id,session.session_id,session.session_id,session.session_id).run();
    const accepted = await this.trial(session.session_id,trial.trial_id);
    if (accepted?.submission_fingerprint !== fingerprint) throw new BenchmarkError(409,"This trial is final. A different response cannot be accepted.");
    return this.getSession(session.session_id);
  }
  async abandon(session: SessionRow) {
    if (session.status !== "active") throw new BenchmarkError(409,"This session is closed.");
    await this.db.prepare("UPDATE human_sessions SET status = 'abandoned' WHERE session_id = ? AND status = 'active'").bind(session.session_id).run();
  }
}
