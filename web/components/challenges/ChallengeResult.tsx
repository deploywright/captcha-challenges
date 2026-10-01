"use client";

import Link from "next/link";

export interface ChallengeResultProps {
  correct: boolean;
  solveTimeMs: number;
  onTryAgain: () => void;
  onTryAnother?: () => void;
  onNextChallenge?: () => void;
  hasNextProgression: boolean;
  hasOtherInLevel?: boolean;
  levelLabel?: string;
}

export function ChallengeResult({
  correct,
  solveTimeMs,
  onTryAgain,
  onTryAnother,
  onNextChallenge,
  hasNextProgression,
  hasOtherInLevel = true,
}: ChallengeResultProps) {
  const seconds = (solveTimeMs / 1000).toFixed(2);

  return (
    <div
      role="alert"
      className={`rounded-2xl p-6 border text-center transition-all duration-300 animate-fade-in shadow-2xl relative overflow-hidden ${
        correct
          ? "bg-gradient-to-b from-emerald-950/50 via-[#0d1c16] to-[#091510] border-emerald-500/50 text-emerald-100"
          : "bg-gradient-to-b from-red-950/50 via-[#1e0e11] to-[#12080a] border-red-500/50 text-red-100"
      }`}
    >
      {/* Background Accent Glow */}
      <div
        className={`absolute -top-16 left-1/2 -translate-x-1/2 w-48 h-48 rounded-full blur-3xl pointer-events-none ${
          correct ? "bg-emerald-500/15" : "bg-red-500/15"
        }`}
      />

      <div className="relative z-10 flex flex-col items-center gap-2">
        <span
          className={`inline-flex items-center justify-center px-4 py-1 rounded-full text-xs font-mono font-bold tracking-widest uppercase border shadow-inner ${
            correct
              ? "bg-emerald-500/20 border-emerald-400/60 text-emerald-300 shadow-emerald-500/20"
              : "bg-red-500/20 border-red-400/60 text-red-300 shadow-red-500/20"
          }`}
        >
          {correct ? "✓ VERIFICATION PASSED" : "✕ VERIFICATION FAILED"}
        </span>

        <div className="font-mono text-3xl sm:text-4xl font-extrabold tracking-tight text-white mt-1">
          {seconds}s
        </div>

        <p className="text-xs text-gray-400 max-w-sm">
          {correct
            ? "Ground truth verification succeeded. Challenge completed."
            : "Ground truth verification did not match your answer."}
        </p>
      </div>

      {/* Action Buttons */}
      <div className="relative z-10 flex flex-wrap items-center justify-center gap-2.5 pt-6 mt-4 border-t border-white/10">
        {/* If incorrect, primary action is Try Again */}
        {!correct && (
          <button
            type="button"
            onClick={onTryAgain}
            className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-red-600 hover:bg-red-500 text-white shadow-md border border-red-400 transition-all cursor-pointer"
          >
            Try Again ↻
          </button>
        )}

        {/* If correct and has next level, primary action is Next Challenge */}
        {correct && hasNextProgression && onNextChallenge && (
          <button
            type="button"
            onClick={onNextChallenge}
            className="px-5 py-2 rounded-lg text-xs font-mono font-bold bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:from-blue-500 hover:to-cyan-500 shadow-md shadow-blue-500/25 border border-cyan-400 transition-all flex items-center gap-1 cursor-pointer"
          >
            <span>Next Level</span>
            <span>→</span>
          </button>
        )}

        {/* Try Another Challenge in the same level (only if there are others) */}
        {hasOtherInLevel && onTryAnother && (
          <button
            type="button"
            onClick={onTryAnother}
            className="px-4 py-2 rounded-lg text-xs font-mono font-semibold bg-[#1a2030] text-gray-200 hover:bg-[#232b40] hover:text-white border border-gray-700 transition-all cursor-pointer"
          >
            Try Another Challenge
          </button>
        )}

        {/* If correct and NO next level (e.g. final level), offer Replay */}
        {correct && (!hasNextProgression || !onNextChallenge) && (
          <button
            type="button"
            onClick={onTryAgain}
            className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md border border-emerald-400 transition-all cursor-pointer"
          >
            Replay Challenge ↻
          </button>
        )}

        <Link
          href="/challenges"
          className="px-4 py-2 rounded-lg text-xs font-mono text-gray-400 hover:text-gray-200 hover:bg-white/5 border border-transparent hover:border-gray-800 transition-all"
        >
          Back to Levels
        </Link>
      </div>
    </div>
  );
}
