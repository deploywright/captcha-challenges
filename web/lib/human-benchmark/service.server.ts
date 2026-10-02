import "server-only";
import { CATALOG, getChallengeById } from "../challenges/catalog";
import { toClientChallenge } from "../challenges/adapter";
import { gradeSubmission } from "../challenges/validation.server";
import { TOTAL_TRIALS, TRIAL_TIMEOUT_MS } from "./protocol";
import { BenchmarkError, exactFields, hashToken } from "./security.server";
import { HumanStore } from "./store.server";
import type { SessionRow } from "./store.server";
import type { AcceptedSubmission, SessionView, TrialSubmission } from "./types";

export { CATALOG };
export function progress(session: SessionRow) {
  return {completed:session.answered_count + session.skipped_count,total:TOTAL_TRIALS};
}
export function accepted(session: SessionRow): AcceptedSubmission {
  return {accepted:true,progress:progress(session),hasNext:session.status === "active"};
}
export function median(values: number[]) {
  if (!values.length) return null;
  values.sort((a,b) => a-b);
  const mid = Math.floor(values.length/2);
  return values.length % 2 ? values[mid] : (values[mid-1]+values[mid])/2;
}
export async function sessionView(store: HumanStore, session: SessionRow): Promise<SessionView> {
  if (session.status === "created") throw new BenchmarkError(503,"Session is still starting.");
  const view: SessionView = {status:session.status,cohort:session.cohort,progress:progress(session)};
  if (session.status === "completed") {
    const {results} = await store.db.prepare("SELECT correct,client_solve_time_ms,presented_at FROM human_trials WHERE session_id = ?").bind(session.session_id).all<{correct:number;client_solve_time_ms:number;presented_at:number|null}>();
    view.summary = {accuracy:results.reduce((sum,r) => sum+r.correct,0)/TOTAL_TRIALS,medianSolveTimeMs:median(results.filter(r => r.presented_at !== null).map(r => r.client_solve_time_ms)),skipped:session.skipped_count,timedOut:session.timeout_count,total:TOTAL_TRIALS};
  } else if (session.status === "active") {
    const trial = await store.current(session.session_id);
    if (!trial) throw new BenchmarkError(503,"Trial is unavailable.");
    const entry = getChallengeById(trial.challenge_id);
    if (!entry) throw new BenchmarkError(503,"Stimulus is unavailable.");
    const publicChallenge = toClientChallenge(entry);
    // Renderer contract uses an opaque trial identity; remove experimental metadata.
    view.trial = {trialId:trial.trial_id,position:trial.position,presented:trial.presented_at !== null,elapsedMs:trial.presented_at === null ? 0 : Math.max(0,store.now()-trial.presented_at),challenge:{...publicChallenge,id:trial.trial_id,level:0,levelKey:"",levelLabel:"",displayName:"",seed:0,subtype:undefined,difficulty:undefined,resolution:undefined,seriesId:undefined}};
  }
  return view;
}
export function validateSubmission(body: Record<string,unknown>): TrialSubmission {
  exactFields(body,["trialId","action","answer","solveTimeMs","interrupted"]);
  if (typeof body.trialId !== "string" || !/^[a-f0-9-]{36}$/.test(body.trialId)) throw new BenchmarkError(400,"Invalid trial token.");
  if (!["answer","skip","timeout"].includes(String(body.action))) throw new BenchmarkError(400,"Invalid trial action.");
  if (typeof body.solveTimeMs !== "number" || !Number.isFinite(body.solveTimeMs) || body.solveTimeMs < 0 || body.solveTimeMs > TRIAL_TIMEOUT_MS || !Number.isInteger(body.solveTimeMs)) throw new BenchmarkError(400,"Invalid solve time.");
  if (typeof body.interrupted !== "boolean") throw new BenchmarkError(400,"Invalid interruption flag.");
  if (body.action !== "answer" && body.answer !== undefined) throw new BenchmarkError(400,"A skipped trial cannot contain an answer.");
  return body as unknown as TrialSubmission;
}
export async function submitTrial(store: HumanStore, session: SessionRow, body: Record<string,unknown>) {
  const payload = validateSubmission(body);
  const trial = await store.trial(session.session_id,payload.trialId);
  if (!trial) throw new BenchmarkError(409,"This is not an assigned trial.");
  const entry = getChallengeById(trial.challenge_id);
  if (!entry) throw new BenchmarkError(503,"Stimulus is unavailable.");
  if (payload.action === "answer") {
    if (entry.type === "image-selection") {
      if (!Array.isArray(payload.answer) || payload.answer.some(i => !Number.isInteger(i) || typeof i !== "number" || i < 0 || i >= entry.assets.length) || new Set(payload.answer).size !== payload.answer.length) throw new BenchmarkError(400,"Select valid image tiles.");
      payload.answer = [...payload.answer].sort((a,b) => a-b);
    } else if (typeof payload.answer !== "string" || !entry.ui.options?.includes(payload.answer)) throw new BenchmarkError(400,"Choose a listed option.");
  }
  const fingerprint = await hashToken(JSON.stringify([payload.action,payload.answer ?? null,payload.solveTimeMs,payload.interrupted]));
  if (trial.submission_fingerprint) {
    if (trial.submission_fingerprint !== fingerprint) throw new BenchmarkError(409,"This trial is final. A different response cannot be accepted.");
    return accepted(await store.getSession(session.session_id));
  }
  if (session.status !== "active") throw new BenchmarkError(409,"This session is closed.");
  const current = await store.current(session.session_id);
  if (current?.trial_id !== trial.trial_id) throw new BenchmarkError(409,"This is not the current trial.");
  if (payload.action === "answer" && trial.presented_at === null) throw new BenchmarkError(409,"Wait until the visual stimulus is ready.");
  const serverElapsed = trial.presented_at === null ? 0 : Math.max(0,store.now()-trial.presented_at);
  const timedOut = payload.action === "timeout" || payload.solveTimeMs >= TRIAL_TIMEOUT_MS || serverElapsed >= TRIAL_TIMEOUT_MS;
  if (payload.action === "timeout" && payload.solveTimeMs < TRIAL_TIMEOUT_MS && serverElapsed < TRIAL_TIMEOUT_MS) throw new BenchmarkError(400,"The trial has not timed out.");
  const skipped = payload.action !== "answer" || timedOut;
  const grade = skipped ? null : gradeSubmission(trial.challenge_id,payload.answer);
  if (grade && !grade.valid) throw new BenchmarkError(503,"Grading is temporarily unavailable.");
  const updated = await store.finish(session,trial,fingerprint,payload.answer,grade?.correct === true && !skipped,skipped,timedOut,payload.solveTimeMs,payload.interrupted);
  return accepted(updated);
}
