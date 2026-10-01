import { describe, it, expect } from "vitest";
import {
  getAllChallenges,
  getChallengeById,
  getChallengesByVariant,
  getNextProgressionChallenge,
  getLevelInfos,
} from "../lib/challenges/catalog";
import { toClientChallenge } from "../lib/challenges/adapter";

describe("Catalog Queries & Client Adapter", () => {
  it("loads all catalog entries correctly", () => {
    const all = getAllChallenges();
    expect(all.length).toBe(82);
  });

  it("finds challenge by ID and verifies fields", () => {
    const firstLvl1 = getChallengesByVariant("street-grid")[0];
    expect(firstLvl1).toBeDefined();
    const challenge = getChallengeById(firstLvl1.id);
    expect(challenge).toBeDefined();
    expect(challenge?.level).toBe(1);
    expect(challenge?.variant).toBe("street-grid");
    expect(challenge?.assetCount).toBe(9);
  });

  it("returns challenges filtered by variant", () => {
    expect(getChallengesByVariant("street-grid").length).toBe(20);
    expect(getChallengesByVariant("hard-street-grid").length).toBe(20);
    expect(getChallengesByVariant("checker-shadow").length).toBe(6);
    expect(getChallengesByVariant("tangled-cables").length).toBe(8);
    expect(getChallengesByVariant("degraded-vision").length).toBe(28);
  });

  it("progresses sequentially across all five levels", () => {
    // Level 1 -> Level 2A
    const lvl1 = getChallengesByVariant("street-grid")[0];
    const next1 = getNextProgressionChallenge(lvl1.id);
    expect(next1?.variant).toBe("hard-street-grid");

    // Level 2A -> Level 2B
    const lvl2a = getChallengesByVariant("hard-street-grid")[0];
    const next2a = getNextProgressionChallenge(lvl2a.id);
    expect(next2a?.variant).toBe("checker-shadow");

    // Level 2B -> Level 3A
    const lvl2b = getChallengesByVariant("checker-shadow")[0];
    const next2b = getNextProgressionChallenge(lvl2b.id);
    expect(next2b?.variant).toBe("tangled-cables");

    // Level 3A -> Level 3B
    const lvl3a = getChallengesByVariant("tangled-cables")[0];
    const next3a = getNextProgressionChallenge(lvl3a.id);
    expect(next3a?.variant).toBe("degraded-vision");

    // Level 3B is terminal
    const lvl3b = getChallengesByVariant("degraded-vision")[0];
    const next3b = getNextProgressionChallenge(lvl3b.id);
    expect(next3b).toBeUndefined();
  });

  it("adapts raw challenge to ClientChallenge and strips private fields", () => {
    const rawMock = {
      id: "mock_123",
      level: 1,
      variant: "street-grid",
      instruction: "Select target",
      assets: ["assets/a.webp"],
      ui: { rows: 3, columns: 3 },
      // Private fields that might be accidentally passed:
      correctSelection: [0, 1],
      answer: "target",
      annotations: { bboxes: [] },
    };

    const client = toClientChallenge(rawMock as any);
    expect(client.id).toBe("mock_123");
    expect(client.instruction).toBe("Select target");
    expect(client.ui.rows).toBe(3);
    expect(client.ui.columns).toBe(3);

    // Assert private fields are absent from client object
    expect((client as any).correctSelection).toBeUndefined();
    expect((client as any).answer).toBeUndefined();
    expect((client as any).annotations).toBeUndefined();
  });

  it("rejects malformed raw challenge missing id or variant", () => {
    expect(() => toClientChallenge({} as any)).toThrow();
    expect(() => toClientChallenge({ id: "test" } as any)).toThrow();
  });

  it("retrieves level summaries with correct challenge counts", () => {
    const infos = getLevelInfos();
    expect(infos.length).toBe(5);

    const lvl1Info = infos.find((i) => i.levelNumber === "1");
    expect(lvl1Info?.count).toBe(20);

    const lvl3bInfo = infos.find((i) => i.levelNumber === "3B");
    expect(lvl3bInfo?.count).toBe(28);
  });
});
