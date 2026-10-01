import { ANSWERS_REGISTRY, getPrivateAnswer } from "../../src/generated-private/answers";
import type { ChallengeVariant, SubmissionResponse } from "./types";

export interface GradeResult {
  valid: boolean;
  correct: boolean;
  challengeId: string;
  variant?: ChallengeVariant;
  error?: string;
}

export function gradeSubmission(
  challengeId: string,
  submittedAnswer: unknown
): GradeResult {
  const groundTruth = getPrivateAnswer(challengeId);
  if (!groundTruth) {
    return {
      valid: false,
      correct: false,
      challengeId,
      error: `Challenge '${challengeId}' not found in answer registry.`,
    };
  }

  const variant = groundTruth.variant as ChallengeVariant;

  // 1. Image Selection Challenges (Level 1, Level 2A, Level 3B)
  if (
    groundTruth.type === "image-selection" ||
    variant === "street-grid" ||
    variant === "hard-street-grid" ||
    variant === "degraded-vision"
  ) {
    if (!Array.isArray(submittedAnswer)) {
      return {
        valid: false,
        correct: false,
        challengeId,
        variant,
        error: "Expected array of selected tile indices.",
      };
    }

    const submittedIndices = submittedAnswer.map(Number);
    const truthIndices = groundTruth.correctSelection ?? [];

    const submittedSet = new Set(submittedIndices);
    const truthSet = new Set(truthIndices);

    // Order-independent set equality
    let isCorrect = submittedSet.size === truthSet.size;
    if (isCorrect) {
      for (const idx of submittedSet) {
        if (!truthSet.has(idx)) {
          isCorrect = false;
          break;
        }
      }
    }

    return {
      valid: true,
      correct: isCorrect,
      challengeId,
      variant,
    };
  }

  // 2. Single Choice Challenges (Level 2B: Checker Shadow, Level 3A: Tangled Cables)
  if (groundTruth.type === "single-choice") {
    let isCorrect = false;

    // A. Submitted as string option
    if (typeof submittedAnswer === "string") {
      const cleanSub = submittedAnswer.trim().toLowerCase();
      if (groundTruth.answer) {
        isCorrect = cleanSub === groundTruth.answer.trim().toLowerCase();
      }
    }
    // B. Submitted as number (index)
    else if (typeof submittedAnswer === "number") {
      const truthIndex = groundTruth.correctSelection?.[0];
      if (truthIndex !== undefined) {
        isCorrect = submittedAnswer === truthIndex;
      }
    }
    // C. Submitted as array of single index
    else if (Array.isArray(submittedAnswer) && submittedAnswer.length === 1) {
      const truthIndex = groundTruth.correctSelection?.[0];
      if (truthIndex !== undefined) {
        isCorrect = Number(submittedAnswer[0]) === truthIndex;
      }
    }

    return {
      valid: true,
      correct: isCorrect,
      challengeId,
      variant,
    };
  }

  return {
    valid: false,
    correct: false,
    challengeId,
    variant,
    error: `Unsupported challenge type: ${groundTruth.type}`,
  };
}
