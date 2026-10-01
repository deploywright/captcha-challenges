"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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
  const [inspectingIndex, setInspectingIndex] = useState<number | null>(null);
  const loadedCount = useRef<number>(0);
  const assetReadyFired = useRef<boolean>(false);
  const imgRefs = useRef<(HTMLImageElement | null)[]>([]);

  const totalAssets = challenge.assets.length;
  const columns = challenge.ui.columns || (totalAssets === 16 ? 4 : 3);

  // Trigger asset ready safely once all images are loaded
  const markAssetsReady = useCallback(() => {
    if (!assetReadyFired.current) {
      assetReadyFired.current = true;
      onAssetsReady();
    }
  }, [onAssetsReady]);

  // Reset selection and image loading tracking when challenge ID changes
  useEffect(() => {
    setSelectedIndices(new Set());
    setInspectingIndex(null);
    loadedCount.current = 0;
    assetReadyFired.current = false;
    imgRefs.current = [];

    // Fallback: check if images are already cached and complete
    const timer = setTimeout(() => {
      if (!assetReadyFired.current) {
        const allDone = imgRefs.current.length === totalAssets &&
          imgRefs.current.every((img) => img?.complete);
        if (allDone) {
          markAssetsReady();
        }
      }
    }, 50);

    return () => clearTimeout(timer);
  }, [challenge.id, totalAssets, markAssetsReady]);

  // Keyboard navigation for inspect modal
  useEffect(() => {
    if (inspectingIndex === null) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setInspectingIndex(null);
      } else if (e.key === "ArrowLeft") {
        setInspectingIndex((prev) => (prev !== null && prev > 0 ? prev - 1 : prev));
      } else if (e.key === "ArrowRight") {
        setInspectingIndex((prev) => (prev !== null && prev < totalAssets - 1 ? prev + 1 : prev));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [inspectingIndex, totalAssets]);

  const handleTileImageLoaded = () => {
    loadedCount.current += 1;
    if (loadedCount.current >= totalAssets) {
      markAssetsReady();
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

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col items-center w-full max-w-2xl sm:max-w-3xl mx-auto"
    >
      {/* Header Banner */}
      <div className="w-full bg-[#161a25] border-t border-x border-[#2b3145] rounded-t-xl p-4 sm:p-5 text-center shadow-lg">
        <span className="text-xs uppercase tracking-wider font-mono text-blue-400 font-semibold block mb-1">
          {challenge.levelLabel}: Grid Image Selection
        </span>
        <h2 className="text-base sm:text-xl font-semibold text-white">
          {challenge.instruction}
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          Click all matching squares. Click the 🔍 magnifying glass to inspect any tile in high resolution.
        </p>
      </div>

      {/* Grid Canvas */}
      <div className="w-full bg-[#10131c] border border-[#2b3145] p-3 sm:p-4 flex justify-center items-center">
        <div
          className={`grid gap-2 sm:gap-3 w-full ${
            columns === 4 ? "grid-cols-4" : "grid-cols-3"
          }`}
        >
          {challenge.assets.map((assetUrl, index) => {
            const isSelected = selectedIndices.has(index);

            return (
              <div
                key={`${challenge.id}-tile-${index}`}
                role="checkbox"
                aria-checked={isSelected}
                tabIndex={0}
                aria-label={`Square ${index + 1}`}
                onClick={() => toggleTile(index)}
                onKeyDown={(e) => {
                  if (e.key === " " || e.key === "Enter") {
                    e.preventDefault();
                    toggleTile(index);
                  }
                }}
                className={`group relative aspect-square w-full rounded-lg overflow-hidden select-none border-2 transition-all duration-150 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
                  isSelected
                    ? "border-blue-400 ring-2 ring-blue-500/80 scale-[0.98] shadow-lg shadow-blue-500/25 bg-blue-950/20"
                    : "border-gray-800 hover:border-gray-600 bg-gray-900"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  ref={(el) => {
                    imgRefs.current[index] = el;
                  }}
                  src={assetUrl}
                  alt={`Tile ${index + 1}`}
                  onLoad={handleTileImageLoaded}
                  loading="eager"
                  className={`w-full h-full object-cover transition-all duration-150 ${
                    isSelected ? "opacity-90 brightness-110" : "opacity-100 group-hover:scale-105"
                  }`}
                />

                {/* Inspect / Zoom Magnifier Button */}
                <button
                  type="button"
                  title="Inspect tile enlarged"
                  aria-label={`Inspect tile ${index + 1} enlarged`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setInspectingIndex(index);
                  }}
                  className="absolute top-2 left-2 p-1.5 rounded-full bg-black/70 hover:bg-black/90 text-white/80 hover:text-white border border-white/20 transition-all opacity-80 sm:opacity-0 group-hover:opacity-100 hover:scale-110 shadow-md z-10"
                >
                  <svg
                    className="w-3.5 h-3.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"
                    />
                  </svg>
                </button>

                {/* Selection Checkmark Badge */}
                {isSelected && (
                  <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-blue-600 border-2 border-white flex items-center justify-center shadow-lg animate-in fade-in zoom-in-75 duration-100 z-10">
                    <svg
                      className="w-3.5 h-3.5 text-white"
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
                <div className="absolute bottom-1.5 left-1.5 px-1.5 py-0.5 rounded bg-black/70 text-[10px] font-mono text-gray-300 pointer-events-none">
                  {index + 1}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="w-full bg-[#161a25] border-b border-x border-[#2b3145] rounded-b-xl p-4 flex items-center justify-between gap-3 shadow-lg">
        <div className="flex items-center gap-2">
          <span className="text-xs sm:text-sm font-mono text-gray-300">
            {selectedIndices.size} selected
          </span>
          {selectedIndices.size > 0 && !disabled && (
            <button
              type="button"
              onClick={() => setSelectedIndices(new Set())}
              className="text-xs font-mono text-gray-400 hover:text-white underline underline-offset-2 ml-1"
            >
              Clear
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="submit"
            disabled={disabled || isSubmitting}
            className={`px-6 py-2.5 rounded-lg text-xs sm:text-sm font-mono font-semibold transition-all duration-150 flex items-center justify-center gap-2 ${
              disabled || isSubmitting
                ? "bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700/50"
                : "bg-blue-600 hover:bg-blue-500 text-white shadow-md hover:shadow-blue-500/25 border border-blue-400 cursor-pointer"
            }`}
          >
            {isSubmitting ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Verifying...
              </>
            ) : selectedIndices.size === 0 ? (
              "Verify (None Match)"
            ) : (
              "Verify Answer"
            )}
          </button>
        </div>
      </div>

      {/* Image Inspect / Zoom Modal */}
      {inspectingIndex !== null && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Inspecting tile ${inspectingIndex + 1}`}
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={() => setInspectingIndex(null)}
        >
          <div
            className="max-w-2xl w-full bg-[#161a25] border border-[#2b3145] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#2b3145] bg-[#12151e]">
              <div>
                <span className="text-xs font-mono text-blue-400 font-bold">
                  Tile {inspectingIndex + 1} of {totalAssets}
                </span>
                <p className="text-xs text-gray-300 font-medium">
                  {challenge.instruction}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setInspectingIndex(null)}
                aria-label="Close inspection modal"
                className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Image View with Prev/Next Controls */}
            <div className="relative w-full bg-black flex items-center justify-center p-2 min-h-[320px] max-h-[65vh]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={challenge.assets[inspectingIndex]}
                alt={`Tile ${inspectingIndex + 1} enlarged view`}
                className="max-h-[60vh] w-auto max-w-full object-contain rounded select-none"
              />

              {/* Prev Button */}
              {inspectingIndex > 0 && (
                <button
                  type="button"
                  title="Previous tile (Left arrow)"
                  aria-label="Previous tile"
                  onClick={() => setInspectingIndex((prev) => (prev !== null ? prev - 1 : 0))}
                  className="absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/70 hover:bg-black/90 text-white border border-white/20 shadow-lg"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
              )}

              {/* Next Button */}
              {inspectingIndex < totalAssets - 1 && (
                <button
                  type="button"
                  title="Next tile (Right arrow)"
                  aria-label="Next tile"
                  onClick={() => setInspectingIndex((prev) => (prev !== null ? prev + 1 : 0))}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/70 hover:bg-black/90 text-white border border-white/20 shadow-lg"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              )}
            </div>

            {/* Modal Footer: Selection Toggle & Done */}
            <div className="flex items-center justify-between px-5 py-3.5 border-t border-[#2b3145] bg-[#12151e]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-gray-400">
                  Status:
                </span>
                <span
                  className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                    selectedIndices.has(inspectingIndex)
                      ? "bg-blue-900/60 text-blue-300 border border-blue-700"
                      : "bg-gray-800 text-gray-400 border border-gray-700"
                  }`}
                >
                  {selectedIndices.has(inspectingIndex) ? "Selected ✓" : "Not Selected"}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => toggleTile(inspectingIndex)}
                  className={`px-4 py-2 rounded-lg text-xs font-mono font-semibold transition-all border ${
                    selectedIndices.has(inspectingIndex)
                      ? "bg-red-950/60 hover:bg-red-900/80 text-red-200 border-red-800"
                      : "bg-blue-600 hover:bg-blue-500 text-white border-blue-400"
                  }`}
                >
                  {selectedIndices.has(inspectingIndex) ? "Deselect Tile" : "Select Tile"}
                </button>
                <button
                  type="button"
                  onClick={() => setInspectingIndex(null)}
                  className="px-4 py-2 rounded-lg text-xs font-mono font-semibold bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </form>
  );
}
