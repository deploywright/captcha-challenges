import { beforeAll, afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import fs from "node:fs";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { NextRequest } from "next/server";
vi.mock("server-only",() => ({}));
vi.mock("../lib/challenges/validation.server",() => ({gradeSubmission:vi.fn(() => ({valid:true,correct:true}))}));
import { gradeSubmission } from "../lib/challenges/validation.server";
import { participantApi } from "../lib/human-benchmark/api.server";
import { adminApi } from "../lib/human-benchmark/admin.server";
import { HumanStore } from "../lib/human-benchmark/store.server";
import { CATALOG, sessionView, submitTrial } from "../lib/human-benchmark/service.server";
import { humanSummary, exportPage, csvValue } from "../lib/human-benchmark/analytics.server";
import type { Cohort } from "../lib/human-benchmark/protocol";
import { TRIAL_TIMEOUT_MS } from "../lib/human-benchmark/protocol";
import { checkOrigin, checkAdmin, readBody } from "../lib/human-benchmark/security.server";

let mf: Miniflare;
let store: HumanStore;
let now = 1_800_000_000_000;
function request(path: string, body?: unknown, cookie = "", headers: Record<string,string> = {}) {
  return new NextRequest(`https://benchmark.test/api/human-benchmark/${path}`,{method:body === undefined ? "GET" : "POST",headers:{origin:"https://benchmark.test","content-type":"application/json",cookie,...headers},body:body === undefined ? undefined : JSON.stringify(body)});
}
async function create(cohort: Cohort = "main", participant = crypto.randomUUID()) {
  return store.create(participant,cohort,"desktop","large",CATALOG);
}
async function complete(sessionId: string) {
  for(let i=0;i<40;i++) {
    const session = await store.getSession(sessionId); const trial = (await store.current(sessionId))!;
    await store.present(session,trial.trial_id);
    const entry = CATALOG.find(c => c.id === trial.challenge_id)!;
    await submitTrial(store,session,{trialId:trial.trial_id,action:"answer",answer:entry.type === "image-selection" ? [] : entry.ui.options![0],solveTimeMs:1000+i,interrupted:false});
    now += 2000;
  }
}
beforeAll(async () => {
  mf = new Miniflare(convertV4MiniflareOptions({modules:true,script:"export default {fetch(){return new Response('test')}}",d1Databases:["DB"],compatibilityDate:"2024-09-23"}));
  const db = await mf.getD1Database("DB");
  // Preserve complete trigger statements; apply the real committed migration to workerd D1.
  const statements: string[] = []; let current = ""; let trigger = false;
  for(const line of fs.readFileSync("migrations/0001_human_benchmark.sql","utf8").split(/\r?\n/)) {
    if (!line.trim() || line.trim().startsWith("--")) continue;
    current += `${line.trim()} `;
    if (/^CREATE TRIGGER/i.test(line)) trigger = true;
    if (trigger ? /^END;$/.test(line.trim()) : line.trim().endsWith(";")) {statements.push(current);current="";trigger=false;}
  }
  await db.batch(statements.map(sql => db.prepare(sql)));
  store = new HumanStore(db,() => now);
},30_000);
afterAll(async () => {await mf?.dispose();});
beforeEach(async () => {
  now = 1_800_000_000_000; vi.mocked(gradeSubmission).mockClear();
  await store.db.batch(["human_trials","human_sessions","human_participants","human_challenge_exposure","human_protocol_state","human_rate_limits"].map(table => store.db.prepare(`DELETE FROM ${table}`)));
});
describe("persistent participant API and private grading", () => {
  it("requires consent and authenticates token hashes rather than session/participant IDs", async () => {
    await expect(participantApi(request("session",{consent:false}),"start",store)).rejects.toMatchObject({status:400});
    const response = await participantApi(request("session",{consent:true,deviceClass:"mobile",viewportBucket:"small"}),"start",store);
    expect(response.status).toBe(201);
    const cookies = response.cookies.getAll();
    expect(cookies).toHaveLength(2);
    const token = cookies.find(c => c.name === "hb_session_token")!;
    expect(token.httpOnly).toBe(true);expect(token.secure).toBe(true);expect(token.sameSite).toBe("lax");
    const session = await store.authenticate(token.value);
    const row = await store.db.prepare("SELECT session_token_hash FROM human_sessions WHERE session_id = ?").bind(session.session_id).first<{session_token_hash:string}>();
    expect(row!.session_token_hash).not.toBe(token.value);
    await expect(store.authenticate(session.session_id)).rejects.toMatchObject({status:401});
    await expect(store.authenticate(session.participant_id)).rejects.toMatchObject({status:401});
    const view = await response.json(); expect(JSON.stringify(view)).not.toMatch(/"(correct|score|summary|session_token_hash|assignment_seed)"/);
  });
  it("resumes the frozen assignment, starts presentation once, and never leaks active correctness", async () => {
    const {session,token} = await create();
    const initial = await sessionView(store,session); const trial = initial.trial!;
    const cookie = `hb_session_token=${token}`;
    const presented = await participantApi(request("present",{trialId:trial.trialId},cookie),"present",store);
    expect(await presented.json()).toMatchObject({ready:true});
    now += 500;
    await participantApi(request("present",{trialId:trial.trialId},cookie),"present",store);
    expect((await store.trial(session.session_id,trial.trialId))!.presented_at).toBe(now-500);
    const currentTrial = (await store.current(session.session_id))!;
    const entry = CATALOG.find(c => c.id === currentTrial.challenge_id)!;
    const payload = {trialId:trial.trialId,action:"answer",answer:entry.type === "image-selection" ? [] : entry.ui.options![0],solveTimeMs:500,interrupted:true};
    const result = await participantApi(request("trial",payload,cookie),"trial",store);
    expect(await result.json()).toEqual({accepted:true,progress:{completed:1,total:40},hasNext:true});
    expect(gradeSubmission).toHaveBeenCalledWith(entry.id,payload.answer);
    const resumed = await participantApi(request("session",undefined,cookie),"session",store);
    const next = await resumed.json() as {trial:{position:number;trialId:string}};
    expect(next.trial.position).toBe(2); expect(next.trial.trialId).not.toBe(trial.trialId);
    expect(JSON.stringify(next)).not.toMatch(/"(correct|score|summary)"/);
  });
  it("idempotently accepts duplicate delivery and rejects a changed payload, including concurrent delivery", async () => {
    const {session} = await create(); const trial = (await store.current(session.session_id))!;
    const payload = {trialId:trial.trial_id,action:"skip",solveTimeMs:0,interrupted:false};
    const responses = await Promise.all([submitTrial(store,session,payload),submitTrial(store,session,payload)]);
    expect(responses.every(r => r.accepted)).toBe(true);
    expect((await store.getSession(session.session_id)).skipped_count).toBe(1);
    await expect(submitTrial(store,session,{...payload,interrupted:true})).rejects.toMatchObject({status:409});
    const exposure = await store.db.prepare("SELECT completed_count FROM human_challenge_exposure WHERE challenge_id = ?").bind(trial.challenge_id).first<{completed_count:number}>();
    expect(exposure!.completed_count).toBe(1);
  });
  it("rejects arbitrary IDs, future trials, invalid indices, missing readiness, and oversized input", async () => {
    const {session} = await create();const trial = (await store.current(session.session_id))!;
    await expect(submitTrial(store,session,{trialId:trial.trial_id,action:"skip",solveTimeMs:0,interrupted:false,challengeId:"anything"})).rejects.toMatchObject({status:400});
    const future = await store.db.prepare("SELECT trial_id FROM human_trials WHERE session_id = ? AND position = 2").bind(session.session_id).first<{trial_id:string}>();
    await expect(submitTrial(store,session,{trialId:future!.trial_id,action:"skip",solveTimeMs:0,interrupted:false})).rejects.toMatchObject({status:409});
    await expect(submitTrial(store,session,{trialId:crypto.randomUUID(),action:"skip",solveTimeMs:0,interrupted:false})).rejects.toMatchObject({status:409});
    const entry = CATALOG.find(c => c.id === trial.challenge_id)!;
    const valid = entry.type === "image-selection" ? [] : entry.ui.options![0];
    await expect(submitTrial(store,session,{trialId:trial.trial_id,action:"answer",answer:valid,solveTimeMs:5,interrupted:false})).rejects.toMatchObject({status:409});
    await store.present(session,trial.trial_id);
    for(const answer of [[true],[100],[0,0],{},123]) await expect(submitTrial(store,session,{trialId:trial.trial_id,action:"answer",answer,solveTimeMs:5,interrupted:false})).rejects.toMatchObject({status:400});
    await expect(readBody(request("trial",{padding:"x".repeat(5000)}))).rejects.toMatchObject({status:413});
  });
  it("records skip and timeout as primary failures and only releases an aggregate after completion", async () => {
    const {session} = await create();
    let trial = (await store.current(session.session_id))!;
    await submitTrial(store,session,{trialId:trial.trial_id,action:"skip",solveTimeMs:0,interrupted:false});
    trial = (await store.current(session.session_id))!;
    const current = await store.getSession(session.session_id);await store.present(current,trial.trial_id);
    await expect(submitTrial(store,current,{trialId:trial.trial_id,action:"timeout",solveTimeMs:10,interrupted:false})).rejects.toMatchObject({status:400});
    now += TRIAL_TIMEOUT_MS;
    await submitTrial(store,current,{trialId:trial.trial_id,action:"timeout",solveTimeMs:TRIAL_TIMEOUT_MS,interrupted:false});
    for(let i=0;i<38;i++) {
      const s = await store.getSession(session.session_id); const t = (await store.current(s.session_id))!;
      await store.present(s,t.trial_id); const entry = CATALOG.find(c => c.id === t.challenge_id)!;
      await submitTrial(store,s,{trialId:t.trial_id,action:"answer",answer:entry.type === "image-selection" ? [] : entry.ui.options![0],solveTimeMs:1000,interrupted:false});
    }
    const finished = await store.getSession(session.session_id);
    expect(finished.status).toBe("completed");
    const view = await sessionView(store,finished); expect(view.summary).toMatchObject({accuracy:.95,skipped:2,timedOut:1,total:40});expect(view.trial).toBeUndefined();
    const summary = await humanSummary(store.db);
    expect(summary.overall).toMatchObject({assignedTrials:40,primaryExactAccuracy:.95,secondaryAnsweredOnlyAccuracy:1,timedOutTrials:1,skippedTrials:2});
    expect(summary.by.stage["Level 2A"]).toBeDefined();expect(summary.by.stage["Level 2B"]).toBeDefined();
    await expect(store.present(finished,trial.trial_id)).rejects.toMatchObject({status:409});
    await expect(create("main",session.participant_id)).rejects.toMatchObject({status:409});
  },20_000);
  it("uses server elapsed time to turn a late answer into a timeout without grading", async () => {
    const {session} = await create();const trial = (await store.current(session.session_id))!;await store.present(session,trial.trial_id);
    now += TRIAL_TIMEOUT_MS+1;const entry = CATALOG.find(c => c.id === trial.challenge_id)!;
    await submitTrial(store,session,{trialId:trial.trial_id,action:"answer",answer:entry.type === "image-selection" ? [] : entry.ui.options![0],solveTimeMs:3,interrupted:false});
    expect(gradeSubmission).not.toHaveBeenCalled();expect(await store.trial(session.session_id,trial.trial_id)).toMatchObject({timed_out:1,skipped:1,correct:0});
  });
  it("makes concurrent session reservations atomic and keeps exposure counts consistent", async () => {
    const sessions = await Promise.all(Array.from({length:4},() => create()));
    expect(sessions).toHaveLength(4);
    const counts = await store.db.prepare("SELECT SUM(assigned_count) count FROM human_challenge_exposure").first<{count:number}>();expect(counts!.count).toBe(160);
    for(const {session} of sessions) expect((await store.db.prepare("SELECT COUNT(*) count FROM human_trials WHERE session_id = ?").bind(session.session_id).first<{count:number}>())!.count).toBe(40);
  });
  it("excludes pilot and smoke from main summaries/exports and protects administration", async () => {
    for(const cohort of ["pilot","smoke"] as const) {const {session} = await create(cohort);await complete(session.session_id);}
    expect((await humanSummary(store.db)).completedParticipants).toBe(0);
    expect((await exportPage(store.db,"main")).rows).toHaveLength(0);
    expect((await humanSummary(store.db,"all")).completedParticipants).toBe(2);
    await expect(adminApi(request("admin/summary"),"summary",store.db,"admin-test-key")).rejects.toMatchObject({status:401});
    await expect(checkAdmin(request("admin/summary",undefined,"",{authorization:"Bearer wrong"}),"admin-test-key")).rejects.toMatchObject({status:401});
    const response = await adminApi(request("admin/export.json?cohort=all",undefined,"",{authorization:"Bearer admin-test-key"}),"json",store.db,"admin-test-key");
    expect((await response.json() as {rows:unknown[]}).rows).toHaveLength(80);
    const csv = await adminApi(request("admin/export.csv?cohort=all",undefined,"",{authorization:"Bearer admin-test-key"}),"csv",store.db,"admin-test-key");
    expect((await csv.text()).split("\r\n")).toHaveLength(82);
    expect(csvValue('=danger,"text"')).toBe('"\'=danger,""text"""');
  },20_000);
  it("rejects cross-origin mutation, restricts smoke creation, and stops sessions", async () => {
    expect(() => checkOrigin(request("session",{},"",{origin:"https://other.test"}))).toThrow();
    await expect(participantApi(request("session",{consent:true,cohort:"smoke",deviceClass:"desktop",viewportBucket:"large"}),"start",store,"key")).rejects.toMatchObject({status:401});
    const {session,token} = await create();await participantApi(request("stop",{},`hb_session_token=${token}`),"stop",store);
    expect((await store.getSession(session.session_id)).status).toBe("abandoned");
  });
  it("checks the HTTP host when Next reconstructs a local URL with localhost", () => {
    expect(() => checkOrigin(new NextRequest("http://localhost:3001/api/human-benchmark/session",{method:"POST",headers:{host:"127.0.0.1:3001",origin:"http://127.0.0.1:3001"}}))).not.toThrow();
    expect(() => checkOrigin(new NextRequest("http://localhost:3001/api/human-benchmark/session",{method:"POST",headers:{host:"127.0.0.1:3001",origin:"http://evil.test"}}))).toThrow();
  });
});
