"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ClientChallenge, SubmissionResponse } from "@/lib/challenges/types";
import { getChallengesByVariant } from "@/lib/challenges/catalog";
import { ChallengeTimer } from "./ChallengeTimer";
import { ChallengeResult } from "./ChallengeResult";
import { ImageGridChallenge } from "./ImageGridChallenge";
import { BinaryChoiceChallenge } from "./BinaryChoiceChallenge";
import { TangledCablesChallenge } from "./TangledCablesChallenge";
import { RoutingPuzzleChallenge } from "./RoutingPuzzleChallenge";

interface ChallengePlayerProps {
  challenge: ClientChallenge;
  nextProgressionId?: string;
  anotherInLevelId?: string;
}

export function ChallengePlayer({
  challenge,
  nextProgressionId,
}: ChallengePlayerProps) {
  const router = useRouter();

  // Attempt key used to cleanly remount child components on Retry/Reset
  const [attemptKey, setAttemptKey] = useState<number>(0);

  // Timing state
  const [isTimerRunning, setIsTimerRunning] = useState<boolean>(false);
  const [finalTimeMs, setFinalTimeMs] = useState<number | undefined>(undefined);
  const startTimeRef = useRef<number | null>(null);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<SubmissionResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Reset all state whenever a new challenge is loaded
  useEffect(() => {
    setResult(null);
    setIsSubmitting(false);
    setErrorMsg(null);
    setFinalTimeMs(undefined);
    setIsTimerRunning(false);
    startTimeRef.current = null;
    setAttemptKey((k) => k + 1);
  }, [challenge.id]);

  // Callback triggered when images/visuals have loaded into the browser
  const handleAssetsReady = useCallback(() => {
    if (result) return; // Already solved
    startTimeRef.current = performance.now();
    setIsTimerRunning(true);
  }, [result]);

  // Generic submit handler for all challenge interaction types
  const handleSubmit = async (answer: number[] | string | number) => {
    if (isSubmitting || result) return;

    // 1. Stop timer immediately
    const endTime = performance.now();
    setIsTimerRunning(false);
    const elapsed = startTimeRef.current !== null ? endTime - startTimeRef.current : 0;
    setFinalTimeMs(elapsed);

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const response = await fetch(`/api/challenges/${challenge.id}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer,
          solveTimeMs: Math.round(elapsed),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Submission failed.");
      }

      const resData = (await response.json()) as SubmissionResponse;
      setResult({
        ...resData,
        solveTimeMs: elapsed,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error verifying answer.";
      setErrorMsg(msg);
      // Allow re-trying if network error
      setIsTimerRunning(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Try Again: Reset the current challenge in place
  const handleTryAgain = () => {
    setResult(null);
    setIsSubmitting(false);
    setErrorMsg(null);
    setFinalTimeMs(undefined);
    setIsTimerRunning(false);
    startTimeRef.current = null;
    setAttemptKey((k) => k + 1);
  };

  // Try Another Challenge: Pick a different challenge in the same level dynamically
  const handleTryAnother = () => {
    const allInVariant = getChallengesByVariant(challenge.variant);
    const siblings = allInVariant.filter((c) => c.id !== challenge.id);

    if (siblings.length > 0) {
      const randomIndex = Math.floor(Math.random() * siblings.length);
      const nextChallenge = siblings[randomIndex];
      router.push(`/challenge/${nextChallenge.id}`);
    } else {
      // If there are no other challenges in this level, reset in place
      handleTryAgain();
    }
  };

  const handleNextChallenge = () => {
    if (nextProgressionId) {
      router.push(`/challenge/${nextProgressionId}`);
    } else {
      router.push("/challenges");
    }
  };

  // Check if there are other challenges in the current level
  const hasOtherInLevel = getChallengesByVariant(challenge.variant).length > 1;

  const containerMaxWidth =
    challenge.variant === "routing-puzzle" || challenge.variant === "tangled-cables"
      ? "max-w-5xl"
      : challenge.variant === "checker-shadow"
      ? "max-w-xl"
      : challenge.variant === "hard-street-grid"
      ? "max-w-lg"
      : "max-w-md";

  return (
    <div className={`flex flex-col items-center w-full ${containerMaxWidth} mx-auto space-y-3.5`}>
      {/* Top Status Bar: Level Badge & Timer */}
      <div className="w-full flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-blue-950/80 text-blue-300 border border-blue-800/80">
            {challenge.levelLabel}
          </span>
          <span className="text-xs font-mono text-gray-400 hidden sm:inline-block">
            {challenge.displayName}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <ChallengeTimer
            isRunning={isTimerRunning}
            finalTimeMs={finalTimeMs}
          />
        </div>
      </div>

      {/* Network or Validation Error Alert */}
      {errorMsg && (
        <div className="w-full p-3 rounded bg-red-950/60 border border-red-800 text-xs font-mono text-red-200 text-center">
          {errorMsg}
        </div>
      )}

      {/* Challenge Interaction Component */}
      <div className="w-full">
        {challenge.variant === "checker-shadow" ? (
          <BinaryChoiceChallenge
            key={`${challenge.id}-${attemptKey}`}
            challenge={challenge}
            isSubmitting={isSubmitting}
            onSubmit={handleSubmit}
            onAssetsReady={handleAssetsReady}
            disabled={result !== null}
          />
        ) : challenge.variant === "routing-puzzle" || challenge.variant === "tangled-cables" ? (
          <RoutingPuzzleChallenge
            key={`${challenge.id}-${attemptKey}`}
            challenge={challenge}
            isSubmitting={isSubmitting}
            onSubmit={handleSubmit}
            onAssetsReady={handleAssetsReady}
            disabled={result !== null}
          />
        ) : (
          <ImageGridChallenge
            key={`${challenge.id}-${attemptKey}`}
            challenge={challenge}
            isSubmitting={isSubmitting}
            onSubmit={handleSubmit}
            onAssetsReady={handleAssetsReady}
            disabled={result !== null}
          />
        )}
      </div>

      {/* Post-Submission Result Card */}
      {result !== null && (
        <div className="w-full pt-1">
          <ChallengeResult
            correct={result.correct}
            solveTimeMs={result.solveTimeMs ?? finalTimeMs ?? 0}
            onTryAgain={handleTryAgain}
            onTryAnother={handleTryAnother}
            onNextChallenge={handleNextChallenge}
            hasNextProgression={Boolean(nextProgressionId)}
            hasOtherInLevel={hasOtherInLevel}
            levelLabel={challenge.levelLabel}
          />
        </div>
      )}
    </div>
  );
}
