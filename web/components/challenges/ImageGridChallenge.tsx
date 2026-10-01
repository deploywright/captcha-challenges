"use client";

import { useState, useEffect, useRef } from "react";
import type { ClientChallenge } from "@/lib/challenges/types";

interface ImageGridChallengeProps {
  challenge: ClientChallenge;
  isSubmitting: boolean;
  onSubmit: (selectedIndices: number[]) => void;
  onAssetsReady: () => void;
  disabled?: boolean;
}

export function ImageGridChallenge({
  challenge,
  isSubmitting,
  onSubmit,
  onAssetsReady,
  disabled = false,
}: ImageGridChallengeProps) {
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const loadedCount = useRef<number>(0);
  const assetReadyFired = useRef<boolean>(false);

  const totalAssets = challenge.assets.length;
  const columns = challenge.ui.columns || (totalAssets === 16 ? 4 : 3);

  // Reset selection and image loading tracking when challenge ID changes
  useEffect(() => {
    setSelectedIndices(new Set());
    loadedCount.current = 0;
    assetReadyFired.current = false;
  }, [challenge.id]);

  const handleTileImageLoaded = () => {
    loadedCount.current += 1;
    if (loadedCount.current >= totalAssets && !assetReadyFired.current) {
      assetReadyFired.current = true;
      onAssetsReady();
    }
  };

  const toggleTile = (index: number) => {
    if (disabled || isSubmitting) return;

    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled || isSubmitting) return;

    const answer = Array.from(selectedIndices).sort((a, b) => a - b);
    onSubmit(answer);
  };

  const handleSelectAll = () => {
    if (disabled || isSubmitting) return;
    if (selectedIndices.size === totalAssets) {
      setSelectedIndices(new Set());
    } else {
      setSelectedIndices(new Set(Array.from({ length: totalAssets }, (_, i) => i)));
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={`flex flex-col items-center w-full mx-auto ${
        columns === 4 ? "max-w-lg" : "max-w-md"
      }`}
    >
      {/* Header Banner */}
      <div className="w-full bg-[#161a25] border-t border-x border-[#2b3145] rounded-t-lg p-4 text-center">
        <span className="text-xs uppercase tracking-wider font-mono text-blue-400 font-semibold block mb-1">
          {challenge.levelLabel}: Grid Image Selection
        </span>
        <h2 className="text-base sm:text-lg font-medium text-white">
          {challenge.instruction}
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          Click all matching squares. If none match, click Verify directly.
        </p>
      </div>

      {/* Grid Canvas */}
      <div className="w-full bg-[#10131c] border border-[#2b3145] p-3 flex justify-center items-center">
        <div
          className={`grid gap-1.5 w-full ${
            columns === 4 ? "grid-cols-4" : "grid-cols-3"
          }`}
        >
          {challenge.assets.map((assetUrl, index) => {
            const isSelected = selectedIndices.has(index);

            return (
              <button
                key={`${challenge.id}-tile-${index}`}
                type="button"
                role="checkbox"
                aria-checked={isSelected}
                aria-label={`Square ${index + 1}`}
                disabled={disabled || isSubmitting}
                onClick={() => toggleTile(index)}
                className={`relative aspect-square w-full rounded overflow-hidden select-none border transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
                  isSelected
                    ? "border-blue-400 ring-2 ring-blue-500/80 scale-[0.97] shadow-lg shadow-blue-500/20"
                    : "border-gray-800 hover:border-gray-600 bg-gray-900"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={assetUrl}
                  alt={`Tile ${index + 1}`}
                  onLoad={handleTileImageLoaded}
                  loading="eager"
                  className={`w-full h-full object-cover transition-opacity duration-150 ${
                    isSelected ? "opacity-90 brightness-110" : "opacity-100"
                  }`}
                />

                {/* Selection Checkmark Badge */}
                {isSelected && (
                  <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-blue-600 border border-white/80 flex items-center justify-center shadow-md animate-in fade-in zoom-in-75 duration-100">
                    <svg
                      className="w-3 h-3 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="3"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                )}

                {/* Subtle tile index tag in corner */}
                <div className="absolute bottom-1 left-1 px-1 py-0.2 rounded bg-black/60 text-[9px] font-mono text-gray-400 pointer-events-none">
                  {index + 1}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="w-full bg-[#161a25] border-b border-x border-[#2b3145] rounded-b-lg p-3.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-gray-400">
            {selectedIndices.size} selected
          </span>
          {selectedIndices.size > 0 && !disabled && (
            <button
              type="button"
              onClick={() => setSelectedIndices(new Set())}
              className="text-[11px] font-mono text-gray-400 hover:text-white underline underline-offset-2 ml-1"
            >
              Clear
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="submit"
            disabled={disabled || isSubmitting}
            className={`px-5 py-2 rounded text-xs font-mono font-semibold transition-all duration-150 flex items-center justify-center gap-2 ${
              disabled || isSubmitting
                ? "bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700/50"
                : "bg-blue-600 hover:bg-blue-500 text-white shadow-md hover:shadow-blue-500/25 border border-blue-400"
            }`}
          >
            {isSubmitting ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Verifying...
              </>
            ) : selectedIndices.size === 0 ? (
              "Verify (None)"
            ) : (
              "Verify Answer"
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
