import { describe, it, expect } from "vitest";
import { gradeSubmission } from "../lib/challenges/validation.server";
import { ANSWERS_REGISTRY } from "../src/generated-private/answers";

describe("Server-Side Answer Grading Evaluation", () => {
  const streetGridEntry = Object.values(ANSWERS_REGISTRY).find(
    (e) => e.variant === "street-grid" && Array.isArray(e.correctSelection) && e.correctSelection.length > 0
  )!;
  const checkerShadowEntry = Object.values(ANSWERS_REGISTRY).find(
    (e) => e.variant === "checker-shadow"
  )!;
  const routingPuzzleEntry = Object.values(ANSWERS_REGISTRY).find(
    (e) => e.variant === "routing-puzzle" || e.variant === "tangled-cables"
  )!;

  it("grades image-grid correctly and ignores selection index order", () => {
    expect(streetGridEntry).toBeDefined();
    const challengeId = streetGridEntry.challengeId;
    const correct = streetGridEntry.correctSelection!;

    // Matching order
    const res1 = gradeSubmission(challengeId, correct);
    expect(res1.valid).toBe(true);
    expect(res1.correct).toBe(true);

    // Permuted order
    const reversed = [...correct].reverse();
    const res2 = gradeSubmission(challengeId, reversed);
    expect(res2.valid).toBe(true);
    expect(res2.correct).toBe(true);

    // Partial selection (incorrect)
    const partial = correct.slice(0, 1);
    const res3 = gradeSubmission(challengeId, partial);
    expect(res3.valid).toBe(true);
    expect(res3.correct).toBe(false);

    // Extra index (incorrect)
    const extraIndex = [0, 1, 2, 3, 4, 5, 6, 7, 8].find((idx) => !correct.includes(idx)) ?? 99;
    const res4 = gradeSubmission(challengeId, [...correct, extraIndex]);
    expect(res4.valid).toBe(true);
    expect(res4.correct).toBe(false);

    // Empty array (incorrect)
    const res5 = gradeSubmission(challengeId, []);
    expect(res5.valid).toBe(true);
    expect(res5.correct).toBe(false);
  });

  it("grades binary choice illusion challenge correctly", () => {
    expect(checkerShadowEntry).toBeDefined();
    const challengeId = checkerShadowEntry.challengeId;
    const answer = checkerShadowEntry.answer!;

    // Text match exact
    expect(gradeSubmission(challengeId, answer).correct).toBe(true);

    // Case-insensitive text match
    expect(gradeSubmission(challengeId, answer.toLowerCase()).correct).toBe(true);
    expect(gradeSubmission(challengeId, ` ${answer.toUpperCase()} `).correct).toBe(true);

    // Wrong option
    const wrongAnswer = answer.toLowerCase() === "yes" ? "No" : "Yes";
    expect(gradeSubmission(challengeId, wrongAnswer).correct).toBe(false);

    // Index match
    const correctIdx = checkerShadowEntry.correctSelection?.[0] ?? 0;
    const wrongIdx = correctIdx === 0 ? 1 : 0;
    expect(gradeSubmission(challengeId, correctIdx).correct).toBe(true);
    expect(gradeSubmission(challengeId, wrongIdx).correct).toBe(false);
  });

  it("grades routing puzzles correctly", () => {
    expect(routingPuzzleEntry).toBeDefined();
    const challengeId = routingPuzzleEntry.challengeId;
    const answer = routingPuzzleEntry.answer!;

    // Exact string match
    expect(gradeSubmission(challengeId, answer).correct).toBe(true);

    // Incorrect answer string
    expect(gradeSubmission(challengeId, "Definitely Wrong Option").correct).toBe(false);

    // Option index match
    if (routingPuzzleEntry.correctSelection && routingPuzzleEntry.correctSelection.length > 0) {
      const correctIdx = routingPuzzleEntry.correctSelection[0];
      expect(gradeSubmission(challengeId, correctIdx).correct).toBe(true);
      expect(gradeSubmission(challengeId, 999).correct).toBe(false);
    }
  });

  it("handles missing challenge ID gracefully with clean error", () => {
    const res = gradeSubmission("non_existent_id", [0, 1]);
    expect(res.valid).toBe(false);
    expect(res.correct).toBe(false);
    expect(res.error).toContain("not found");
  });

  it("rejects non-array submission for image-selection challenge", () => {
    const res = gradeSubmission(streetGridEntry.challengeId, "Yes");
    expect(res.valid).toBe(false);
    expect(res.correct).toBe(false);
    expect(res.error).toContain("Expected array");
  });
});
