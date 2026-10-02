import "server-only";
import { COHORTS, PROTOCOL_VERSION, STAGES } from "./protocol";
import type { BenchmarkVariant, Cohort } from "./protocol";
import { BenchmarkError } from "./security.server";
import { metricResult } from "./metrics";
import type { MetricCounts } from "./metrics";
import creatorAttribution from "../../../reports/creator-vs-gemini/creator-attribution.json";

const ANALYSIS_ANNOTATIONS = [creatorAttribution] as const;
const ANALYSIS_ANNOTATIONS_JSON = JSON.stringify(ANALYSIS_ANNOTATIONS);

export function analysisRole(sessionId: string, storedCohort: Cohort): string {
  return ANALYSIS_ANNOTATIONS.find(annotation => annotation.session_id === sessionId)?.analysis_role ?? storedCohort;
}

const ANALYSIS_POPULATION_FILTER = `AND (s.cohort = 'creator' OR NOT EXISTS (
  SELECT 1 FROM json_each(?) annotation
  WHERE json_extract(annotation.value,'$.session_id') = s.session_id
    AND json_extract(annotation.value,'$.analysis_role') = 'creator'))`;

export function analysisCohort(url: URL): Cohort | "all" {
  const value = url.searchParams.get("cohort") ?? "main";
  if (value !== "all" && !COHORTS.includes(value as Cohort)) throw new BenchmarkError(400,"Invalid analysis cohort.");
  return value as Cohort | "all";
}
const RELEVANT = `SELECT t.* FROM human_trials t JOIN human_sessions s ON t.session_id = s.session_id
  WHERE s.status = 'completed' AND s.protocol_version = ? AND (? = 'all' OR s.cohort = ?) ${ANALYSIS_POPULATION_FILTER}`;
const EXPANDED = `SELECT dimensions.value kind, CASE dimensions.value
    WHEN 'overall' THEN 'overall' WHEN 'variant' THEN variant WHEN 'subtype' THEN subtype
    WHEN 'routingDifficulty' THEN CASE WHEN variant = 'routing-puzzle' THEN difficulty END
    WHEN 'degradedResolution' THEN CASE WHEN variant = 'degraded-vision' THEN CAST(resolution AS TEXT) END
    WHEN 'series' THEN series_id END bucket, r.* FROM relevant r
  CROSS JOIN json_each('["overall","variant","subtype","routingDifficulty","degradedResolution","series"]') dimensions
  WHERE bucket IS NOT NULL`;

export async function humanSummary(db: D1Database, cohort: Cohort | "all" = "main") {
  // Aggregate and quantile work stays in D1; no answers or unbounded raw rows enter memory.
  const query = `WITH relevant AS (${RELEVANT}), expanded AS (${EXPANDED}),
    timed AS (SELECT kind,bucket,client_solve_time_ms,
      ROW_NUMBER() OVER (PARTITION BY kind,bucket ORDER BY client_solve_time_ms) rn,
      COUNT(*) OVER (PARTITION BY kind,bucket) n FROM expanded WHERE presented_at IS NOT NULL),
    latencies AS (SELECT kind,bucket,COUNT(*) timed_samples,
      AVG(CASE WHEN rn IN ((n+1)/2,(n+2)/2) THEN client_solve_time_ms END) median_ms,
      MAX(CASE WHEN rn = (n*95+99)/100 THEN client_solve_time_ms END) p95_ms FROM timed GROUP BY kind,bucket),
    counts AS (SELECT kind,bucket,COUNT(*) assigned,SUM(status = 'answered') answered,
      SUM(skipped) skipped,SUM(timed_out) timed_out,SUM(correct) correct,SUM(interrupted) interrupted
      FROM expanded GROUP BY kind,bucket)
    SELECT c.*,l.median_ms,l.p95_ms,COALESCE(l.timed_samples,0) timed_samples FROM counts c
      LEFT JOIN latencies l USING(kind,bucket)`;
  const {results} = await db.prepare(query).bind(PROTOCOL_VERSION,cohort,cohort,ANALYSIS_ANNOTATIONS_JSON).all<MetricCounts & {kind:string;bucket:string}>();
  const completed = await db.prepare(`SELECT COUNT(DISTINCT participant_id) participants, COUNT(*) sessions
    FROM human_sessions s WHERE status = 'completed' AND protocol_version = ? AND (? = 'all' OR cohort = ?) ${ANALYSIS_POPULATION_FILTER}`)
    .bind(PROTOCOL_VERSION,cohort,cohort,ANALYSIS_ANNOTATIONS_JSON).first<{participants:number;sessions:number}>();
  const excluded = await db.prepare(`SELECT COUNT(*) sessions FROM human_sessions s WHERE status = 'completed' AND protocol_version = ?
    AND (? = 'all' OR cohort = ?) AND cohort != 'creator' AND EXISTS (
      SELECT 1 FROM json_each(?) annotation WHERE json_extract(annotation.value,'$.session_id') = s.session_id
        AND json_extract(annotation.value,'$.analysis_role') = 'creator')`)
    .bind(PROTOCOL_VERSION,cohort,cohort,ANALYSIS_ANNOTATIONS_JSON).first<{sessions:number}>();
  const groups: Record<string,Record<string,ReturnType<typeof metricResult>>> = {stage:{},variant:{},subtype:{},routingDifficulty:{},degradedResolution:{},series:{}};
  const empty = metricResult({assigned:0,answered:0,skipped:0,timed_out:0,correct:0,interrupted:0,median_ms:null,p95_ms:null,timed_samples:0});
  let overall = empty;
  for (const row of results) {
    const metric = metricResult(row);
    if (row.kind === "overall") overall = metric;
    else {
      groups[row.kind][row.bucket] = metric;
      if (row.kind === "variant") groups.stage[STAGES[row.bucket as BenchmarkVariant]] = metric;
    }
  }
  const analysisExcludedSessions = excluded?.sessions ?? 0;
  return {protocolVersion:PROTOCOL_VERSION,cohort,completedParticipants:completed?.participants ?? 0,completedSessions:completed?.sessions ?? 0,analysisExcludedSessions,overall,by:groups,
    population:cohort === "creator" ? "Single-participant creator baseline; not representative of humans in general." : `Completed sessions in this anonymous convenience sample.${analysisExcludedSessions ? ` Excludes ${analysisExcludedSessions} creator-attributed session${analysisExcludedSessions === 1 ? "" : "s"} stored in another cohort.` : ""}`,
    intervalMethod:"95% Wilson interval over trials; descriptive, not adjusted for participant/scene clustering.",
    timingPopulation:"Finalized trials with a presented stimulus, including skips and timeouts; p95 nearest rank."};
}

export const EXPORT_FIELDS = ["session_id","participant_id","protocol_version","cohort","analysis_role","session_status","position","challenge_id","variant","subtype","difficulty","resolution","series_id","trial_status","answer","correct","skipped","timed_out","client_solve_time_ms","server_elapsed_ms","interrupted","assigned_at","presented_at","answered_at"] as const;
export type ExportRow = Record<typeof EXPORT_FIELDS[number], string | number | null> & {trial_id:string};
export async function exportPage(db: D1Database, cohort: Cohort | "all", cursor = "", limit = 500) {
  if (cursor && !/^[a-f0-9-]{36}$/.test(cursor)) throw new BenchmarkError(400,"Invalid export cursor.");
  const {results} = await db.prepare(`SELECT t.trial_id,s.session_id,s.participant_id,s.protocol_version,s.cohort,
    COALESCE(json_extract(annotation.value,'$.analysis_role'),s.cohort) analysis_role,s.status session_status,
    t.position,t.challenge_id,t.variant,t.subtype,t.difficulty,t.resolution,t.series_id,t.status trial_status,
    t.submitted_answer_json answer,t.correct,t.skipped,t.timed_out,t.client_solve_time_ms,t.server_elapsed_ms,t.interrupted,
    t.assigned_at,t.presented_at,t.answered_at
    FROM human_trials t JOIN human_sessions s ON s.session_id = t.session_id
    LEFT JOIN json_each(?) annotation ON json_extract(annotation.value,'$.session_id') = s.session_id
    WHERE s.protocol_version = ? AND (? = 'all' OR s.cohort = ?) AND t.trial_id > ? ORDER BY t.trial_id LIMIT ?`)
    .bind(ANALYSIS_ANNOTATIONS_JSON,PROTOCOL_VERSION,cohort,cohort,cursor,limit).all<ExportRow>();
  return {rows:results,nextCursor:results.length === limit ? results.at(-1)!.trial_id : null};
}
export function csvValue(value: string | number | null) {
  let text = value === null ? "" : String(value);
  // Neutralize spreadsheet formulas in exported text; retain the exact JSON export.
  if (typeof value === "string" && /^[=+@\-\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"','""')}"`;
}
export function csvExport(db: D1Database, cohort: Cohort | "all") {
  let cursor = "";
  let first = true;
  let done = false;
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      if (done) { controller.close(); return; }
      const page = await exportPage(db,cohort,cursor);
      const header = first ? EXPORT_FIELDS.join(",") + "\r\n" : "";
      first = false;
      controller.enqueue(new TextEncoder().encode(header + page.rows.map(row => EXPORT_FIELDS.map(field => csvValue(row[field])).join(",")).join("\r\n") + (page.rows.length ? "\r\n" : "")));
      if (!page.nextCursor) done = true;
      else cursor = page.nextCursor;
    },
  });
}
