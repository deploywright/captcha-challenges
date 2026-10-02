import "server-only";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import { COHORTS } from "./protocol";
import type { Cohort } from "./protocol";
import { HumanStore } from "./store.server";
import { CATALOG, sessionView, submitTrial } from "./service.server";
import { BenchmarkError, checkAdmin, checkOrigin, exactFields, noStore, PARTICIPANT_COOKIE, readBody, SESSION_COOKIE, setCookies } from "./security.server";

export type ParticipantOperation = "start" | "session" | "present" | "trial" | "stop";
export async function participantApi(request: NextRequest, operation: ParticipantOperation, store: HumanStore, adminKey?: string) {
  if (operation !== "session") checkOrigin(request);
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (operation === "start") {
    const body = await readBody(request);
    exactFields(body,["consent","cohort","deviceClass","viewportBucket"]);
    if (body.consent !== true) throw new BenchmarkError(400,"Consent is required before starting.");
    const cohort = (body.cohort ?? "main") as Cohort;
    if (!COHORTS.includes(cohort)) throw new BenchmarkError(400,"Invalid cohort.");
    if (cohort === "smoke") await checkAdmin(request,adminKey);
    if (!["desktop","tablet","mobile"].includes(String(body.deviceClass)) || !["small","medium","large"].includes(String(body.viewportBucket))) throw new BenchmarkError(400,"Invalid coarse device context.");
    if (token) {
      let current;
      try { current = await store.authenticate(token); } catch(error) { if (!(error instanceof BenchmarkError) || error.status !== 401) throw error; }
      if (current?.cohort === cohort) return noStore(await sessionView(store,current));
      if (current?.status === "active") throw new BenchmarkError(409,"Finish or stop your active session before starting another cohort.");
    }
    const cookieId = request.cookies.get(PARTICIPANT_COOKIE)?.value;
    const participantId = cookieId && /^[a-f0-9-]{36}$/.test(cookieId) ? cookieId : crypto.randomUUID();
    const created = await store.create(participantId,cohort,String(body.deviceClass),String(body.viewportBucket),CATALOG);
    const response = noStore(await sessionView(store,created.session),201);
    setCookies(response,participantId,created.token,new URL(request.headers.get("origin")!).protocol === "https:");
    return response;
  }
  const session = await store.authenticate(token);
  if (operation === "session") return noStore(await sessionView(store,session));
  await store.limit(`session:${session.session_id}`,90);
  const body = await readBody(request);
  if (operation === "present") {
    exactFields(body,["trialId"]);
    if (typeof body.trialId !== "string") throw new BenchmarkError(400,"Trial token is required.");
    const trial = await store.present(session,body.trialId);
    return noStore({ready:true,elapsedMs:Math.max(0,store.now()-(trial.presented_at ?? store.now()))});
  }
  if (operation === "stop") {
    exactFields(body,[]);
    await store.abandon(session);
    return noStore({stopped:true});
  }
  return noStore(await submitTrial(store,session,body));
}

export async function handleParticipant(request: NextRequest, operation: ParticipantOperation) {
  try {
    const {env} = await getCloudflareContext({async:true});
    if (!env.HUMAN_BENCHMARK_DB) throw new BenchmarkError(503,"Benchmark storage is unavailable.");
    return await participantApi(request,operation,new HumanStore(env.HUMAN_BENCHMARK_DB),env.HUMAN_BENCHMARK_ADMIN_KEY);
  } catch(error) {
    if (error instanceof BenchmarkError) return noStore({error:error.message},error.status);
    // No request bodies, tokens, headers, or database exception details in logs.
    return noStore({error:"The benchmark is temporarily unavailable. Your accepted responses remain saved."},503);
  }
}
