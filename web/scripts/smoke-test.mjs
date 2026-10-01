async function runSmokeTests() {
  const routes = [
    { url: "http://127.0.0.1:8787/", expect: "CAPTCHA BENCHMARK" },
    { url: "http://127.0.0.1:8787/challenges", expect: "Benchmark Level Select" },
    { url: "http://127.0.0.1:8787/challenges/catalog.json", expect: "lvl1_05ema8" },
    { url: "http://127.0.0.1:8787/challenge/lvl1_05ema8", expect: "Select all images containing a motorcycle" },
    { url: "http://127.0.0.1:8787/challenge/lvl2a_21c33m", expect: "Level 2A" },
    { url: "http://127.0.0.1:8787/challenge/lvl2b_hm0jcq", expect: "Visual Perception Illusion" },
    { url: "http://127.0.0.1:8787/challenge/lvl3a_1w91r2", expect: "Visual Path Tracing" },
    { url: "http://127.0.0.1:8787/challenge/lvl3b_0dhc19", expect: "Resolution:" }
  ];

  console.log("=== Testing GET Routes on Cloudflare Worker ===");
  let allGetPassed = true;
  for (const r of routes) {
    const res = await fetch(r.url);
    const text = await res.text();
    const passed = res.status === 200 && text.includes(r.expect);
    console.log(`[GET ${res.status}] ${r.url}: ${passed ? "PASS" : "FAIL"}`);
    if (!passed) {
      allGetPassed = false;
      console.error("Response snippet:", text.slice(0, 300));
    }
  }

  console.log("\n=== Testing API Submissions on Cloudflare Worker ===");
  // Test 1: Level 1 correct submission
  const sub1 = await fetch("http://127.0.0.1:8787/api/challenges/lvl1_05ema8/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer: [0, 1, 7], solveTimeMs: 3200 })
  });
  const data1 = await sub1.json();
  console.log("Sub 1 (Lvl 1 Correct):", data1.correct === true ? "PASS" : "FAIL", data1);

  // Test 2: Level 1 incorrect submission
  const sub2 = await fetch("http://127.0.0.1:8787/api/challenges/lvl1_05ema8/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer: [0, 2], solveTimeMs: 2500 })
  });
  const data2 = await sub2.json();
  console.log("Sub 2 (Lvl 1 Incorrect):", data2.correct === false ? "PASS" : "FAIL", data2);

  // Test 3: Level 2B Checker Shadow correct submission
  const sub3 = await fetch("http://127.0.0.1:8787/api/challenges/lvl2b_hm0jcq/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer: "Yes", solveTimeMs: 1800 })
  });
  const data3 = await sub3.json();
  console.log("Sub 3 (Lvl 2B Correct):", data3.correct === true ? "PASS" : "FAIL", data3);

  // Test 4: Level 3A Tangled Cables correct submission
  const sub4 = await fetch("http://127.0.0.1:8787/api/challenges/lvl3a_1w91r2/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer: "server_24", solveTimeMs: 4600 })
  });
  const data4 = await sub4.json();
  console.log("Sub 4 (Lvl 3A Correct):", data4.correct === true ? "PASS" : "FAIL", data4);

  // Test 5: Verify static asset image
  const imgRes = await fetch("http://127.0.0.1:8787/challenges/lvl1_05ema8/assets/a.webp");
  console.log(`[STATIC ASSET] lvl1_05ema8/assets/a.webp: status ${imgRes.status}, type ${imgRes.headers.get("content-type")}`);

  if (allGetPassed && data1.correct && !data2.correct && data3.correct && data4.correct && imgRes.status === 200) {
    console.log("\nALL SMOKE TESTS PASSED ON OPENNEXT CLOUDFLARE WORKER!");
  } else {
    console.error("\nSOME SMOKE TESTS FAILED.");
    process.exit(1);
  }
}

runSmokeTests().catch((err) => {
  console.error("Smoke test error:", err);
  process.exit(1);
});
