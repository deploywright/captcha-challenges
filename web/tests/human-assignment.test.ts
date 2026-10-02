import { describe, expect, it } from "vitest";
import { CATALOG } from "../lib/challenges/catalog";
import { assignChallenges } from "../lib/human-benchmark/assignment";
import { QUOTAS, RESOLUTIONS } from "../lib/human-benchmark/protocol";

function verifyAssignment(seed: string, counts: Record<string,number> = {}) {
  const selected = assignChallenges(CATALOG,counts,seed);
  expect(selected).toHaveLength(40);
  expect(new Set(selected.map(c => c.id)).size).toBe(40);
  for (const [variant,count] of Object.entries(QUOTAS)) expect(selected.filter(c => c.variant === variant)).toHaveLength(count);
  expect(selected.filter(c => c.variant === "checker-shadow").map(c => c.id).sort()).toEqual(CATALOG.filter(c => c.variant === "checker-shadow").map(c => c.id).sort());
  const routing = selected.filter(c => c.variant === "routing-puzzle");
  expect(new Set(routing.map(c => c.subtype)).size).toBe(4);
  expect(new Set(routing.map(c => c.difficulty)).size).toBe(5);
  if (!Object.keys(counts).length) expect(new Set(routing.map(c => `${c.subtype}:${c.difficulty}`)).size).toBe(18);
  const degraded = selected.filter(c => c.variant === "degraded-vision");
  expect(new Set(degraded.map(c => c.seriesId)).size).toBe(4);
  for (let i=3;i<selected.length;i++) expect(new Set(selected.slice(i-3,i+1).map(c => c.variant)).size).toBeGreaterThan(1);
  return selected;
}
describe("human-v1 assignment", () => {
  it("preserves every quota, routing stratum diversity, scene isolation, and mixed order for 100 seeds", () => {
    for(let i=0;i<100;i++) verifyAssignment(`seed-${i}`);
  });
  it("is deterministic independent of catalog input ordering", () => {
    const expected = assignChallenges(CATALOG,{},"fixed").map(c => c.id);
    expect(assignChallenges([...CATALOG].reverse(),{},"fixed").map(c => c.id)).toEqual(expected);
  });
  it("prefers unexposed challenges, including lowest-count resolution of each scene", () => {
    const counts = Object.fromEntries(CATALOG.map(c => [c.id,100]));
    for (const variant of ["street-grid","hard-street-grid"] as const) for(const c of CATALOG.filter(c => c.variant === variant).slice(0,6)) counts[c.id] = 0;
    for (const c of CATALOG.filter(c => c.variant === "degraded-vision" && c.resolution === 8)) counts[c.id] = 0;
    const selected = verifyAssignment("least",counts);
    for(const c of selected.filter(c => ["street-grid","hard-street-grid","degraded-vision"].includes(c.variant))) expect(counts[c.id]).toBe(0);
  });
  it("uses distinct resolutions when equally exposed candidates permit it", () => {
    expect(new Set(verifyAssignment("resolution-diversity").filter(c => c.variant === "degraded-vision").map(c => c.resolution)).size).toBe(4);
  });
  it("balances 30 simulated participants across IDs, routing strata, and all resolution ladders", () => {
    const counts = Object.fromEntries(CATALOG.map(c => [c.id,0]));
    for(let i=0;i<30;i++) for(const c of verifyAssignment(`participant-${i}`,counts)) counts[c.id]++;
    const evidence: Record<string,unknown> = {};
    for(const variant of Object.keys(QUOTAS)) {
      const values = CATALOG.filter(c => c.variant === variant).map(c => counts[c.id]);
      const mean = values.reduce((a,b) => a+b,0)/values.length;
      expect(Math.max(...values)-Math.min(...values)).toBeLessThanOrEqual(2);
      expect(Math.min(...values)).toBeGreaterThan(0);
      if (["street-grid","hard-street-grid","routing-puzzle"].includes(variant)) expect(mean).toBe(9);
      evidence[variant] = {min:Math.min(...values),max:Math.max(...values),mean};
    }
    const resolutions = RESOLUTIONS.map(r => CATALOG.filter(c => c.variant === "degraded-vision" && c.resolution === r).reduce((sum,c) => sum+counts[c.id],0));
    expect(Math.max(...resolutions)-Math.min(...resolutions)).toBeLessThanOrEqual(3);
    console.log("30-participant assignment simulation:",JSON.stringify(evidence),"resolution assignments:",resolutions);
  });
});
