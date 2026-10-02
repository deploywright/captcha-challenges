/** Controlled end-to-end check. This script can ONLY create the smoke cohort. */
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

const origin = new URL(process.argv[2] ?? "http://127.0.0.1:3001").origin;
const output = path.resolve(process.argv[3] ?? "../.tmp/human-production-smoke.json");
const localSecret = fs.existsSync(".dev.vars") ? fs.readFileSync(".dev.vars","utf8").match(/^HUMAN_BENCHMARK_ADMIN_KEY=(.+)$/m)?.[1].trim().replace(/^['"]|['"]$/g,"") : undefined;
const key = process.env.HUMAN_BENCHMARK_ADMIN_KEY ?? localSecret;
assert(key,"Configure the local admin secret without putting it in CLI arguments.");
const browser = await chromium.launch();
const context = await browser.newContext({viewport:{width:1440,height:1000}});
const api = context.request;
const secretHeaders = {Authorization:`Bearer ${key}`};
const mutationHeaders = {Origin:origin,"Content-Type":"application/json"};
const evidence = {origin,cohort:"smoke",trials:[],viewports:[],checks:[],startedAt:new Date().toISOString()};
async function getSession() {
  const response = await api.get(`${origin}/api/human-benchmark/session`);assert.equal(response.status(),200);return response.json();
}
function noFeedback(value) {
  assert(!/"(correct|incorrect|score|summary|correctSelection|session_token_hash)"\s*:/.test(JSON.stringify(value)),"Active participant response exposed an outcome.");
}
try {
  const before = await api.get(`${origin}/api/human-benchmark/admin/summary`,{headers:secretHeaders});assert.equal(before.status(),200);
  evidence.mainBefore = await before.json();
  const noAdmin = await api.get(`${origin}/api/human-benchmark/admin/summary`);assert.equal(noAdmin.status(),401);
  const deniedSmoke = await api.post(`${origin}/api/human-benchmark/session`,{headers:mutationHeaders,data:{consent:true,cohort:"smoke",deviceClass:"desktop",viewportBucket:"large"}});assert.equal(deniedSmoke.status(),401);
  const start = await api.post(`${origin}/api/human-benchmark/session`,{headers:{...mutationHeaders,...secretHeaders},data:{consent:true,cohort:"smoke",deviceClass:"desktop",viewportBucket:"large"}});
  assert.equal(start.status(),201);noFeedback(await start.json());
  const cookies = await context.cookies();assert(cookies.find(c => c.name === "hb_session_token")?.httpOnly);
  if (origin.startsWith("https:")) assert(cookies.find(c => c.name === "hb_session_token")?.secure);
  const page = await context.newPage();
  for(const [name,width,height] of [["desktop",1440,1000],["tablet",768,1024],["mobile",390,844]]) {
    await page.setViewportSize({width,height});await page.goto(`${origin}/human-benchmark/run`);
    await page.getByRole("heading",{name:"Question 1 of 40"}).waitFor();
    await page.waitForFunction(() => [...document.querySelectorAll(".hb-stimulus img")].every(img => img.complete && img.naturalWidth > 0));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),`${name} overflow`);
    await page.screenshot({path:path.join(path.dirname(output),`human-production-${name}.png`),fullPage:true});
    evidence.viewports.push({name,width,height,imagesLoaded:true,noOverflow:true});
  }
  // Close the visual player while the API driver finishes, avoiding double timing.
  await page.goto("about:blank");
  const quotas = {};
  let lastPayload;
  for(let index=0;index<40;index++) {
    const view = await getSession();assert.equal(view.status,"active");noFeedback(view);
    const {trial} = view;assert.equal(trial.position,index+1);quotas[trial.challenge.variant]=(quotas[trial.challenge.variant] ?? 0)+1;
    for(const asset of trial.challenge.assets) {
      const url = new URL(asset,origin);assert.equal(url.origin,origin);
      const image = await api.get(url.href);assert.equal(image.status(),200);assert((await image.body()).length > 0);
    }
    const ready = await api.post(`${origin}/api/human-benchmark/present`,{headers:mutationHeaders,data:{trialId:trial.trialId}});assert.equal(ready.status(),200);assert.equal((await ready.json()).ready,true);
    const payload = {trialId:trial.trialId,action:index === 1 ? "skip" : index === 2 ? "timeout" : "answer",solveTimeMs:index === 2 ? 120000 : 1000,interrupted:index === 2};
    if(payload.action === "answer") payload.answer = trial.challenge.type === "image-selection" ? [] : trial.challenge.ui.options[0];
    const submitted = await api.post(`${origin}/api/human-benchmark/trial`,{headers:mutationHeaders,data:payload});assert.equal(submitted.status(),200);
    const accepted = await submitted.json();noFeedback(accepted);assert.equal(accepted.accepted,true);assert.equal(accepted.progress.completed,index+1);
    if(index === 0 || index === 39) {
      const duplicate = await api.post(`${origin}/api/human-benchmark/trial`,{headers:mutationHeaders,data:payload});assert.equal(duplicate.status(),200);
      const different = await api.post(`${origin}/api/human-benchmark/trial`,{headers:mutationHeaders,data:{...payload,interrupted:!payload.interrupted}});assert.equal(different.status(),409);
    }
    evidence.trials.push({trialId:trial.trialId,position:trial.position,variant:trial.challenge.variant,assetCount:trial.challenge.assets.length,accepted:true});
    lastPayload = payload;
    console.log(`Smoke ${index+1}/40 accepted (${trial.challenge.variant})`);
  }
  for(const [variant,count] of Object.entries({"street-grid":6,"hard-street-grid":6,"checker-shadow":6,"routing-puzzle":18,"degraded-vision":4})) assert.equal(quotas[variant],count);
  const finished = await getSession();assert.equal(finished.status,"completed");assert.equal(finished.progress.completed,40);assert(finished.summary);assert(!finished.trial);
  const closed = await api.post(`${origin}/api/human-benchmark/present`,{headers:mutationHeaders,data:{trialId:lastPayload.trialId}});assert.equal(closed.status(),409);
  await page.goto(`${origin}/human-benchmark/run`);await page.getByRole("heading",{name:"Benchmark complete"}).waitFor();
  await page.screenshot({path:path.join(path.dirname(output),"human-production-completed.png"),fullPage:true});
  const after = await api.get(`${origin}/api/human-benchmark/admin/summary`,{headers:secretHeaders});evidence.mainAfter = await after.json();
  assert.equal(evidence.mainAfter.cohort,"main");assert.equal(evidence.mainAfter.completedSessions,evidence.mainBefore.completedSessions);
  const smokeSummary = await api.get(`${origin}/api/human-benchmark/admin/summary?cohort=smoke`,{headers:secretHeaders});assert.equal(smokeSummary.status(),200);evidence.smokeSummary = await smokeSummary.json();
  const raw = await api.get(`${origin}/api/human-benchmark/admin/export.json?cohort=smoke`,{headers:secretHeaders});assert.equal(raw.status(),200);
  const exported = await raw.json();assert(exported.rows.every(row => row.cohort === "smoke"));assert(!JSON.stringify(exported).includes("session_token_hash"));
  const matching = exported.rows.filter(row => evidence.trials.some(t => t.trialId === row.trial_id));assert.equal(matching.length,40);assert.equal(new Set(matching.map(row => row.session_id)).size,1);
  const csv = await api.get(`${origin}/api/human-benchmark/admin/export.csv?cohort=smoke`,{headers:secretHeaders});assert.equal(csv.status(),200);assert((await csv.text()).startsWith("session_id,participant_id,protocol_version,cohort"));
  evidence.personalAggregate = finished.summary;
  evidence.checks = ["admin authentication","smoke creation authorization","secure HttpOnly cookie","desktop/tablet/mobile visuals","40 persisted accepted trials","hidden active correctness","same-payload idempotency","changed replay rejection","completed writes locked","aggregate-only completion","main cohort unchanged","JSON and CSV exports"];
  evidence.finishedAt = new Date().toISOString();
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(evidence,null,2));
  console.log(`Smoke completed; main sessions unchanged. Evidence: ${output}`);
} finally {await browser.close();}
