import { test, expect } from "@playwright/test";
import type { SessionView } from "../lib/human-benchmark/types";
import { CATALOG } from "../lib/challenges/catalog";

test.beforeEach(async ({baseURL}) => {
  if (!baseURL || !["127.0.0.1","localhost"].includes(new URL(baseURL).hostname)) throw new Error("These browser tests may only write to local D1.");
});
test("consent, readiness, same-payload retry, refresh, skip and timeout", async ({page}) => {
  await page.clock.install();
  await page.goto("/human-benchmark?cohort=pilot");
  const start = page.getByRole("button",{name:"Start Human Benchmark"});await expect(start).toBeDisabled();
  await page.getByRole("checkbox").check();await expect(start).toBeEnabled();
  await page.route("**/challenges/*/assets/*",async route => {await new Promise(resolve => setTimeout(resolve,500));await route.continue();});
  const presented = page.waitForResponse(r => r.url().endsWith("/human-benchmark/present") && r.request().method() === "POST");
  await start.click(); await expect(page.getByRole("heading",{name:"Question 1 of 40"})).toBeVisible();
  await expect(page.getByText("Loading visual stimulus…")).toBeVisible();
  const ready = await presented;expect(ready.status()).toBe(200);
  const before = await page.request.get("/api/human-benchmark/session");
  const view = await before.json() as SessionView; expect(view.summary).toBeUndefined();
  const sent: string[] = [];
  await page.route("**/api/human-benchmark/trial",async route => {
    sent.push(route.request().postData()!);
    if (sent.length === 1) await route.abort("connectionfailed");else await route.continue();
  });
  await page.getByRole("button",{name:"Skip question"}).click();
  await expect(page.getByRole("button",{name:"Send saved response"})).toBeVisible();
  await page.reload();await expect(page.getByRole("heading",{name:"Question 1 of 40"})).toBeVisible();
  await expect(page.getByRole("button",{name:"Send saved response"})).toBeVisible();
  await page.getByRole("button",{name:"Send saved response"}).click();
  await expect(page.getByRole("heading",{name:"Question 2 of 40"})).toBeVisible();
  expect(sent[0]).toBe(sent[1]);
  await page.reload();await expect(page.getByRole("heading",{name:"Question 2 of 40"})).toBeVisible();
  const cookies = await page.context().cookies();expect(cookies.find(c => c.name === "hb_session_token")?.httpOnly).toBe(true);
  await page.unroute("**/api/human-benchmark/trial");
  await expect(page.getByText(/seconds remaining/)).toBeVisible();
  await page.clock.fastForward(120_200);
  await expect(page.getByRole("heading",{name:"Question 3 of 40"})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("all renderer families, degraded magnification, mobile layout and keyboard inspection", async ({page},testInfo) => {
  await page.goto("/human-benchmark?cohort=pilot");await page.getByRole("checkbox").check();await page.getByRole("button",{name:"Start Human Benchmark"}).click();
  const seen = new Set<string>();
  for(let i=0;i<40 && seen.size<5;i++) {
    await expect(page.getByRole("heading",{name:`Question ${i+1} of 40`})).toBeVisible();
    const response = await page.request.get("/api/human-benchmark/session");const view = await response.json() as SessionView;
    const variant = view.trial!.challenge.variant;
    await page.waitForFunction(() => [...document.querySelectorAll<HTMLImageElement>(".hb-stimulus img")].every(img => img.complete && img.naturalWidth > 0));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.getByText(/difficulty|series-0|lvl[123]|Gemini/)).toHaveCount(0);
    if (!seen.has(variant)) {
      await page.screenshot({path:testInfo.outputPath(`${variant}.png`),fullPage:true});
      if (["street-grid","hard-street-grid","degraded-vision"].includes(variant)) {
        const urls = await page.locator(".hb-stimulus img").evaluateAll(images => images.map(img => (img as HTMLImageElement).src));
        await page.getByRole("button",{name:"Inspect tile 1 enlarged"}).click();
        await expect(page.getByRole("dialog")).toBeVisible();
        expect(await page.getByRole("dialog").locator("img").getAttribute("src")).toBe(new URL(urls[0]).pathname);
        await page.keyboard.press("Escape");await expect(page.getByRole("dialog")).toHaveCount(0);
      }
      if (variant === "routing-puzzle") {
        await page.getByRole("button",{name:"Zoom in",exact:true}).click();await page.getByRole("button",{name:"Expand",exact:true}).click();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      }
      seen.add(variant);
    }
    await page.getByRole("button",{name:"Skip question"}).click();
  }
  expect(seen.size).toBe(5);
});

test("completes forty real local trials, releases aggregate only, and prevents a second main session", async ({page},testInfo) => {
  test.skip(testInfo.project.name !== "desktop","Complete session is covered once; layouts run in every project.");
  const submissions: unknown[] = [];
  await page.goto("/human-benchmark");await page.getByRole("checkbox").check();await page.getByRole("button",{name:"Start Human Benchmark"}).click();
  for(let i=1;i<=40;i++) {
    await expect(page.getByRole("heading",{name:`Question ${i} of 40`})).toBeVisible();
    await page.waitForFunction(() => [...document.querySelectorAll<HTMLImageElement>(".hb-stimulus img")].every(img => img.complete && img.naturalWidth > 0));
    const view = await (await page.request.get("/api/human-benchmark/session")).json() as SessionView;
    if (view.trial!.challenge.type === "single-choice") await page.getByRole("button",{name:view.trial!.challenge.ui.options![0],exact:true}).click();
    await expect(page.getByRole("button",{name:/Submit (response|\(None Match\))/})).toBeEnabled();
    const accepted = page.waitForResponse(response => response.url().endsWith("/human-benchmark/trial") && response.status() === 200);
    await page.getByRole("button",{name:/Submit (response|\(None Match\))/}).click();
    submissions.push(await (await accepted).json());
  }
  await expect(page.getByRole("heading",{name:"Benchmark complete"})).toBeVisible();
  await expect(page.getByText("Overall accuracy",{exact:true})).toBeVisible();
  expect(submissions).toHaveLength(40);for(const result of submissions) expect(JSON.stringify(result)).not.toMatch(/"(correct|score|answer)"/);
  await page.goto("/human-benchmark");await expect(page.getByText("You already completed this benchmark.")).toBeVisible();
  await expect(page.getByRole("button",{name:"Start Human Benchmark"})).toHaveCount(0);
  await page.screenshot({path:testInfo.outputPath("completed.png"),fullPage:true});
});

test("normal challenge mode still verifies and offers its existing progression controls", async ({page}) => {
  const challenge = CATALOG.find(c => c.variant === "street-grid")!;
  await page.goto(`/challenge/${challenge.id}`);
  await expect(page.getByRole("button",{name:"Verify (None Match)"})).toBeVisible();
  await page.getByRole("button",{name:"Verify (None Match)"}).click();
  await expect(page.getByRole("button",{name:/Try Again|Retry/})).toBeVisible();
  await expect(page.getByRole("button",{name:/Try Another/})).toBeVisible();
  await page.getByRole("button",{name:/Try Again/}).click();
  await page.route(`**/api/challenges/${challenge.id}/submit`,route => route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({correct:true,challengeId:challenge.id,variant:challenge.variant,solveTimeMs:1000})}));
  await page.getByRole("button",{name:"Verify (None Match)"}).click();
  await expect(page.getByRole("button",{name:/Next Level/})).toBeVisible();
});
