"use client";

import { useEffect, useState, useRef } from "react";

export interface ChallengeTimerProps {
  isRunning: boolean;
  finalTimeMs?: number;
}

export function ChallengeTimer({ isRunning, finalTimeMs }: ChallengeTimerProps) {
  const [elapsedMs, setElapsedMs] = useState<number>(0);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isRunning) {
      startTimeRef.current = null;
      return;
    }

    startTimeRef.current = performance.now();
    let animId: number;

    const tick = () => {
      if (startTimeRef.current !== null) {
        setElapsedMs(performance.now() - startTimeRef.current);
        animId = requestAnimationFrame(tick);
      }
    };

    animId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [isRunning]);

  const displayMs = finalTimeMs !== undefined ? finalTimeMs : elapsedMs;
  const seconds = (displayMs / 1000).toFixed(2);

  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded bg-[#161a25] border border-gray-800 text-xs font-mono">
      <span
        className={`w-2 h-2 rounded-full ${
          isRunning
            ? "bg-emerald-400 animate-ping"
            : finalTimeMs !== undefined
            ? "bg-blue-400"
            : "bg-gray-600"
        }`}
      />
      <span className="text-gray-400">Time:</span>
      <span className="text-white font-bold tracking-wider">{seconds}s</span>
    </div>
  );
}
