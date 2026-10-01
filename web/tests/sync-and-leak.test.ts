import { describe, it, expect, beforeAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { syncChallenges } from "../scripts/sync-challenges";

describe("Challenge Synchronization & Security Leak Audit", () => {
  const publicDir = path.resolve(__dirname, "../public/challenges");
  const privateDir = path.resolve(__dirname, "../src/generated-private");
  let synced: ReturnType<typeof syncChallenges>;

  beforeAll(() => {
    // Execute synchronization
    synced = syncChallenges();
  });

  it("synchronizes public catalog and challenge files", () => {
    const catalogPath = path.join(publicDir, "catalog.json");
    expect(fs.existsSync(catalogPath)).toBe(true);

    const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf-8"));
    expect(Array.isArray(catalog)).toBe(true);
    expect(catalog.length).toBeGreaterThan(0);
    expect(catalog.length).toBe(synced.totalSynced);
    expect(catalog.length).toBe(synced.catalogCount);
    const generatedDir = path.resolve(__dirname, "../../challenges/generated");
    const countGenerated = (dir: string): number => fs.readdirSync(dir, { withFileTypes: true })
      .reduce((count, entry) => count + (entry.isDirectory() ? countGenerated(path.join(dir, entry.name)) : Number(entry.name === "challenge.json")), 0);
    expect(catalog.length).toBe(countGenerated(generatedDir));
    const routing = catalog.filter((c: any) => c.variant === "routing-puzzle");
    expect(new Set(routing.map((c: any) => c.subtype))).toEqual(new Set(["laser-maze", "conveyor-routing", "pipe-flow", "device-cables"]));
    expect(routing.some((c: any) => c.subtype === "laser-maze" && c.difficulty === "story")).toBe(true);
    for (const c of routing) {
      const python = JSON.parse(fs.readFileSync(path.join(generatedDir, "level-3a", c.id, "challenge.json"), "utf-8"));
      const publicJson = JSON.parse(fs.readFileSync(path.join(publicDir, c.id, "challenge.json"), "utf-8"));
      expect(c.difficulty).toBe(python.difficulty);
      expect(publicJson.difficulty).toBe(python.difficulty);
    }

    // Verify all 5 variants are represented
    const variants = new Set(catalog.map((c: any) => c.variant));
    expect(variants.has("street-grid")).toBe(true);
    expect(variants.has("hard-street-grid")).toBe(true);
    expect(variants.has("checker-shadow")).toBe(true);
    expect(variants.has("routing-puzzle")).toBe(true);
    expect(variants.has("degraded-vision")).toBe(true);
  });

  it("never copies answer.json into any public directory", () => {
    const findAnswerJson = (dir: string): string[] => {
      const results: string[] = [];
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          results.push(...findAnswerJson(full));
        } else if (entry.name.toLowerCase() === "answer.json") {
          results.push(full);
        }
      }
      return results;
    };

    const leaks = findAnswerJson(publicDir);
    expect(leaks).toEqual([]);
  });

  it("creates server-only private answers registry", () => {
    const answersJsonPath = path.join(privateDir, "answers.json");
    const answersTsPath = path.join(privateDir, "answers.ts");

    expect(fs.existsSync(answersJsonPath)).toBe(true);
    expect(fs.existsSync(answersTsPath)).toBe(true);

    const registry = JSON.parse(fs.readFileSync(answersJsonPath, "utf-8"));
    const catalog = JSON.parse(fs.readFileSync(path.join(publicDir, "catalog.json"), "utf-8"));
    expect(Object.keys(registry).sort()).toEqual(catalog.map((c: any) => c.id).sort());

    // Verify answers exist in private registry
    const sampleLvl1 = Object.values(registry).find((r: any) => r.variant === "street-grid");
    expect(sampleLvl1).toBeDefined();
    expect(Array.isArray((sampleLvl1 as any).correctSelection)).toBe(true);
  });

  it("asserts public JSON files contain zero private answer keys or bounding boxes", () => {
    const forbiddenPatterns = [
      "correctSelection",
      "correctselection",
      "isPositive",
      "ispositive",
      "groundTruth",
      "groundtruth",
      "targetClass",
      "targetclass",
      "connections",
      "annotations",
      "routing",
      "finalTarget",
      "raySegments",
      "mirrorHits",
      "solutionPath",
      "switchStates",
      "openValves",
      "closedValves",
      "reflectionCount", "mirrorCount", "totalMirrorCount", "distractorMirrorCount", "targetCount",
      "routeDecisionDepth", "totalSwitchCount", "decoyBranchCount", "binCount", "switchGraph",
      "solutionDecisionDepth", "totalJunctionCount", "criticalClosedValveCount", "tankCount",
      "cableCount", "waypointColumnCount", "answerOptionCount",
      "generationConfig", "gridDimensions", "mirrors", "decoyPaths", "edges",
    ];

    const scanDirectoryForLeaks = (dir: string) => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          scanDirectoryForLeaks(fullPath);
        } else if (entry.name.endsWith(".json")) {
          const content = fs.readFileSync(fullPath, "utf-8");
          for (const pattern of forbiddenPatterns) {
            expect(
              content.includes(`"${pattern}"`),
              `Leak detected in ${fullPath}: contains forbidden key "${pattern}"`
            ).toBe(false);
          }
        }
      }
    };

    scanDirectoryForLeaks(publicDir);
  });
});
