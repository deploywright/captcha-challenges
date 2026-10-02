/** Read-only production diagnosis; all participant API replies are mocked. */
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const folder = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(folder, '../..');
const web = path.join(root, 'web');
const require = createRequire(path.join(web, 'package.json'));
const {chromium} = require('@playwright/test');
const account = '2f240b7f39bbbf616321d3ba86ef7d7e';
const origin = 'https://captcha-challenges-web.deploywright.workers.dev';
const mainId = '73fac77a-7985-4755-a26d-16ea9046541f';
function wrangler(args) {
  const run = spawnSync(process.execPath, ['node_modules/wrangler/bin/wrangler.js', ...args], {
    cwd: web, env: {...process.env, CLOUDFLARE_ACCOUNT_ID: account},
    encoding: 'utf8', maxBuffer: 4e6,
  });
  assert.equal(run.status, 0, run.stderr);
  return JSON.parse(run.stdout);
}
const sql = [
  "SELECT cohort,status,COUNT(*) sessions FROM human_sessions WHERE protocol_version='human-v1' GROUP BY cohort,status ORDER BY cohort,status",
  "SELECT COUNT(*) count FROM human_sessions WHERE protocol_version='human-v1' AND cohort='creator' AND status='completed'",
  "SELECT COUNT(*) count FROM human_sessions WHERE cohort='creator'",
  "SELECT cohort,COUNT(*) exposure_rows,SUM(assigned_count) assigned_count FROM human_challenge_exposure GROUP BY cohort ORDER BY cohort",
  "SELECT protocol_version,cohort,revision FROM human_protocol_state ORDER BY cohort",
  `SELECT session_id,protocol_version,cohort,status,created_at,started_at,completed_at,assigned_count,answered_count,skipped_count,timeout_count FROM human_sessions WHERE session_id='${mainId}'`,
  `SELECT position,challenge_id,variant,subtype,difficulty,resolution,series_id,status,assigned_at,presented_at,answered_at,correct,skipped,timed_out,client_solve_time_ms,server_elapsed_ms,interrupted FROM human_trials WHERE session_id='${mainId}' ORDER BY position`,
  "SELECT name,sql FROM sqlite_schema WHERE name IN ('human_sessions','human_one_creator','human_trial_completed') ORDER BY name",
  "SELECT name,applied_at FROM d1_migrations ORDER BY id",
];
assert(sql.every(query => query.startsWith('SELECT ')));
const queries = wrangler(['d1','execute','HUMAN_BENCHMARK_DB','--remote','--command', sql.join('; '), '--json']);
assert.equal(queries.length, sql.length);
assert(queries.every(query => query.success && query.meta.rows_written === 0 && !query.meta.changed_db));
const deployments = wrangler(['deployments','list','--name','captcha-challenges-web','--json']);
const creatorDeployment = deployments.find(d => d.versions.some(v => v.version_id === 'ed26276e-ee49-486d-815c-917423858a43'));
assert(creatorDeployment);
const activeDeployment = [...deployments].sort((a,b)=>a.created_on.localeCompare(b.created_on)).at(-1);
const sourcePaths = ['web/app/human-benchmark/page.tsx','web/components/human-benchmark/HumanBenchmarkLanding.tsx','web/components/human-benchmark/HumanBenchmarkPlayer.tsx','web/lib/human-benchmark/api.server.ts','web/lib/human-benchmark/store.server.ts','web/migrations/0002_creator_cohort.sql'];
const sources = sourcePaths.map(p => ({path:p,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')}));
const historical = spawnSync('git',['show','0725f1d^:web/app/human-benchmark/page.tsx'],{cwd:root,encoding:'utf8'});
assert.equal(historical.status,0);
assert(historical.stdout.includes('cohort === "pilot" ? "pilot" : "main"'));

const browser = await chromium.launch({headless:true});
const browserChecks = [];
try {
  for (const existingMain of [false,true]) {
    const context = await browser.newContext();
    let gets = 0;
    const posts = [];
    const completion = cohort => ({status:'completed',cohort,progress:{completed:40,total:40},summary:{accuracy:.75,medianSolveTimeMs:7683,skipped:3,timedOut:1,total:40}});
    // No real session cookie, creation, presentation or submission is allowed.
    await context.route('**/api/**', async route => {
      const request = route.request();
      assert.equal(new URL(request.url()).pathname, '/api/human-benchmark/session');
      if (request.method() === 'POST') {
        assert(!existingMain);
        const body = request.postDataJSON(); posts.push(body);
        assert.equal(body.cohort,'creator');
        await route.fulfill({status:201,contentType:'application/json',body:JSON.stringify(completion('creator'))});
      } else {
        assert.equal(request.method(),'GET'); gets++;
        const view = existingMain && gets === 1 ? {status:'active',cohort:'main',progress:{completed:0,total:40}} : completion(existingMain ? 'main' : 'creator');
        await route.fulfill({status: !existingMain && gets===1 ? 401 : 200,contentType:'application/json',body:JSON.stringify(view)});
      }
    });
    const page = await context.newPage();
    await page.goto(`${origin}/human-benchmark?cohort=creator`);
    await page.getByText('Creator Baseline',{exact:true}).waitFor();
    let startVisible;
    if (existingMain) {
      await page.getByRole('link',{name:'Resume benchmark',exact:true}).waitFor();
      startVisible = await page.getByRole('button',{name:'Start Human Benchmark',exact:true}).count() > 0;
      await page.screenshot({path:path.join(folder,'creator-url-main-resume.png'),fullPage:true});
      await page.getByRole('link',{name:'Resume benchmark',exact:true}).click();
      await page.getByRole('heading',{name:'Benchmark complete',exact:true}).waitFor();
      assert.equal(posts.length,0);
    } else {
      const button=page.getByRole('button',{name:'Start Human Benchmark',exact:true});
      await button.waitFor(); assert(await button.isDisabled()); startVisible=true;
      await page.getByRole('checkbox').check(); await button.click();
      await page.getByRole('heading',{name:'Creator baseline complete',exact:true}).waitFor();
      assert.equal(posts.length,1);
    }
    assert.equal(new URL(page.url()).pathname,'/human-benchmark/run');
    assert.equal(new URL(page.url()).search,'');
    assert(await page.getByText('75.0%',{exact:true}).isVisible());
    browserChecks.push({case:existingMain?'Creator URL with mocked active main session':'Creator URL with mocked unauthenticated browser',session_replies_mocked:true,real_participant_api_requests:0,creator_notice_visible:true,start_button_visible:startVisible,captured_mock_start_cohort:posts[0]?.cohort ?? null,mocked_start_requests:posts.length,resumed_cohort:existingMain?'main':null,run_url:'/human-benchmark/run',completion_heading:existingMain?'Benchmark complete':'Creator baseline complete',completion_values_are_synthetic:true});
    await context.close();
  }
} finally { await browser.close(); }

const main=queries[5].results[0], trials=queries[6].results;
assert.equal(trials.length,40);
const correct=trials.reduce((n,r)=>n+r.correct,0);
const sorted=trials.map(r=>r.client_solve_time_ms).sort((a,b)=>a-b);
const diagnostic={cohort:main.cohort,session_id:main.session_id,attributed_to_creator:false,assigned:trials.length,correct,skipped:trials.reduce((n,r)=>n+r.skipped,0),timed_out:trials.reduce((n,r)=>n+r.timed_out,0),answered:trials.filter(r=>r.status==='answered').length,median_solve_time_ms:(sorted[19]+sorted[20])/2,unique_positions:new Set(trials.map(r=>r.position)).size,unique_challenge_ids:new Set(trials.map(r=>r.challenge_id)).size,finalized:trials.filter(r=>['answered','skipped','timed_out'].includes(r.status)).length,created_at:new Date(main.created_at).toISOString(),completed_at:new Date(main.completed_at).toISOString(),session_counters_match_trials:main.assigned_count===trials.length && main.answered_count===trials.filter(r=>r.status==='answered').length && main.skipped_count===trials.reduce((n,r)=>n+r.skipped,0) && main.timeout_count===trials.reduce((n,r)=>n+r.timed_out,0)};
const evidence={checked_at:new Date().toISOString(),production_origin:origin,account_id:account,database:'captcha-human-benchmark',database_id:'a88c2d6f-d809-4de4-beeb-ebf11347dc26',completed_creator_sessions:queries[1].results[0].count,creator_sessions_all_statuses:queries[2].results[0].count,cohorts:queries[0].results,exposure:queries[3].results,protocol_state:queries[4].results,schema:queries[7].results,migrations:queries[8].results,creator_deployment:{created_at:creatorDeployment.created_on,version_id:creatorDeployment.versions[0].version_id},active_deployment:{created_at:activeDeployment.created_on,versions:activeDeployment.versions},unattributed_main_diagnostic:diagnostic,browser_checks:browserChecks,source_hashes:sources,historical_route:{git_reference:'0725f1d^:web/app/human-benchmark/page.tsx',unsupported_creator_query_falls_back_to_main:true},production_rows_written:0,real_participant_api_requests:0,main_attribution_prohibited:true,historical_browser_path_verified:false};
fs.writeFileSync(path.join(folder,'creator-session-investigation.json'),JSON.stringify(evidence,null,2)+'\n');
// All reported counts and timestamps come from the serialized evidence.
const saved = JSON.parse(fs.readFileSync(path.join(folder,'creator-session-investigation.json'),'utf8'));
const diag = saved.unattributed_main_diagnostic;
const migration = saved.migrations.find(row=>row.name==='0002_creator_cohort.sql');
const markdown = [
  '# Creator session storage investigation', '',
  `Production D1 checked at ${saved.checked_at}. Database: \`${saved.database}\` (\`${saved.database_id}\`).`, '',
  `**No completed creator session exists:** completed human-v1 creator records = ${saved.completed_creator_sessions}; creator records across all statuses = ${saved.creator_sessions_all_statuses}. The main record is not attributed to the user and must not be used as the Creator Baseline.`, '',
  '## Production records', '',
  '| Cohort | Status | Sessions |', '| --- | --- | ---: |',
  ...saved.cohorts.map(row=>`| ${row.cohort} | ${row.status} | ${row.sessions} |`), '',
  'No creator assignment revision or challenge-exposure rows are present. The deployed schema permits creator and has the creator-specific unique index. The missing session is not explained by an unapplied creator schema migration.', '',
  '## Timeline of the unattributed main record', '',
  'This timeline describes an anonymous production record, not the creator\'s identity.', '',
  '| Event | UTC |', '| --- | --- |',
  `| Main record created | ${diag.created_at} |`,
  `| Creator schema migration applied | ${migration.applied_at} UTC |`,
  `| Creator-support Worker deployed | ${saved.creator_deployment.created_at} |`,
  `| Main record completed | ${diag.completed_at} |`, '',
  `Creator-support version: \`${saved.creator_deployment.version_id}\`. Current deployment versions: ${saved.active_deployment.versions.map(v=>`\`${v.version_id}\` (${v.percentage}%)`).join(', ')}.`, '',
  'The main record was created before creator support existed. Its first trial was interrupted and finalized much later; those timing fields do not identify a participant or prove which URL was visited.', '',
  '## Confirmed mechanisms', '',
  '1. **Before creator deployment:** the old landing route accepted only pilot as an alternative to main. A creator query therefore fell back to main. This is verified in the pre-extension Git source, not by reproducing a historical deployment.',
  '2. **Current landing recovery:** the URL selects the Creator Baseline notice, but the landing page fetches the cookie-bound session without a requested-cohort check. Its active-session branch offers Resume for any active cohort. The completed-session branch checks the cohort; the active-session branch does not.',
  '3. **Resume navigation:** Resume opens `/human-benchmark/run`, which loads the cookie-bound session. It does not create, convert, or transfer a session to creator.',
  '4. **Current fresh start:** Start sends the requested creator cohort, and server creation stores that value. A creator-start request with an active main cookie is rejected with HTTP 409; the server does not silently create a new main session.', '',
  'The interface can therefore promise Creator Baseline storage while actually resuming an existing main session. This is a confirmed UI mismatch. It explains how visiting the Creator URL can end with main data without any database relabeling, but the historical path taken by the user remains unverified.', '',
  '## Controlled production browser reproduction', '',
  'The deployed HTML and JavaScript were loaded, but every participant API request was intercepted and fulfilled locally. No real session cookie was supplied. Completion values in these checks were synthetic, not a newly completed benchmark.', '',
  '| Mocked initial state | Creator notice | Start visible | Mocked creator-start requests | Result |',
  '| --- | --- | --- | ---: | --- |',
  ...saved.browser_checks.map(check=>`| ${check.resumed_cohort ? 'Active main session' : 'Unauthenticated browser'} | ${check.creator_notice_visible} | ${check.start_button_visible} | ${check.mocked_start_requests} | ${check.completion_heading} |`), '',
  '[Screenshot: Creator notice with main-session Resume](creator-url-main-resume.png).', '',
  '## Raw-row diagnostic validation', '',
  `The excluded main record \`${diag.session_id}\` has ${diag.assigned} assigned and ${diag.finalized} finalized trials, ${diag.unique_positions} unique positions and ${diag.unique_challenge_ids} unique challenge IDs. Raw outcomes: ${diag.correct}/${diag.assigned}, median ${(diag.median_solve_time_ms/1000).toFixed(3)} seconds, ${diag.skipped} skips including ${diag.timed_out} timeout; ${diag.answered} answered. Session counters agree with raw rows: ${diag.session_counters_match_trials}.`, '',
  'These checks establish record consistency only. They do not establish creator identity, and the matching completion-screen values do not authorize attribution. There are no creator trial rows to validate.', '',
  '## Limits and next action', '',
  'D1 does not store the requested landing URL, browser navigation history, or an authenticated creator identity. The current evidence cannot determine whether the user first opened an unsupported creator query before deployment or later resumed another cohort through the misleading landing page.', '',
  'No valid creator-cohort result can be generated from these records under the instruction to exclude main. The comparison remains an anonymous diagnostic draft. The generator\'s former main-session confirmation override has been removed, so it cannot publish that record as a Creator Baseline.', '',
  'A future UI repair should check the existing cohort before offering Resume, state any cohort conflict clearly, and preserve the existing server rule and immutable assignments. Such a repair would prevent future confusion; it would not recover or change a missing historical creator record. No application code or deployment was changed during this investigation.', '',
  `Production rows written: ${saved.production_rows_written}. Real participant API requests: ${saved.real_participant_api_requests}. No migration, relabeling, model inference, or benchmark rerun was performed.`, '',
  '## Evidence and reproduction', '',
  '[Structured investigation](creator-session-investigation.json) contains query results, deployment identity, browser checks, and source hashes. Submitted responses, provider predictions, cookies, token values, participant IDs, and private ground truth are omitted.', '',
  'The relevant source files are `web/app/human-benchmark/page.tsx`, `web/components/human-benchmark/HumanBenchmarkLanding.tsx`, `web/components/human-benchmark/HumanBenchmarkPlayer.tsx`, and `web/lib/human-benchmark/api.server.ts`.', '',
  'Run `node reports/creator-vs-gemini/investigate_creator_session.mjs` from the repository root after verifying the intended Wrangler account. The script runs SELECT queries only and blocks all real participant API traffic. Browser dependencies come from the existing web package. It writes investigation artifacts only.', '',
].join('\n');
fs.writeFileSync(path.join(folder,'creator-session-investigation.md'),markdown);
console.log(JSON.stringify({completed_creator_sessions:evidence.completed_creator_sessions,creator_sessions_all_statuses:evidence.creator_sessions_all_statuses,browser_checks:browserChecks,production_rows_written:0,report:path.join(folder,'creator-session-investigation.json')}));
