import { describe, it, expect, beforeAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { syncChallenges } from "../scripts/sync-challenges";

describe("Challenge Synchronization & Security Leak Audit", () => {
  const publicDir = path.resolve(__dirname, "../public/challenges");
  const privateDir = path.resolve(__dirname, "../src/generated-private");

  beforeAll(() => {
    // Execute synchronization
    syncChallenges();
  });

  it("synchronizes public catalog and challenge files", () => {
    const catalogPath = path.join(publicDir, "catalog.json");
    expect(fs.existsSync(catalogPath)).toBe(true);

    const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf-8"));
    expect(Array.isArray(catalog)).toBe(true);
    expect(catalog.length).toBe(134);

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
    expect(Object.keys(registry).length).toBe(134);

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
