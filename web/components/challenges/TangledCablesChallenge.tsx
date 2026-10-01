"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { ClientChallenge } from "@/lib/challenges/types";

interface TangledCablesChallengeProps {
  challenge: ClientChallenge;
  isSubmitting: boolean;
  onSubmit: (selectedOption: string) => void;
  onAssetsReady: () => void;
  disabled?: boolean;
}

export function TangledCablesChallenge({
  challenge,
  isSubmitting,
  onSubmit,
  onAssetsReady,
  disabled = false,
}: TangledCablesChallengeProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const assetReadyFired = useRef<boolean>(false);
  const imgRef = useRef<HTMLImageElement | null>(null);

  const markAssetReady = useCallback(() => {
    if (!assetReadyFired.current) {
      assetReadyFired.current = true;
      onAssetsReady();
    }
  }, [onAssetsReady]);

  useEffect(() => {
    setSelectedOption(null);
    setZoomLevel(1);
    setIsExpanded(false);
    assetReadyFired.current = false;

    // Cached image safeguard
    const timer = setTimeout(() => {
      if (!assetReadyFired.current && imgRef.current?.complete) {
        markAssetReady();
      }
    }, 50);

    return () => clearTimeout(timer);
  }, [challenge.id, markAssetReady]);

  const handleImageLoaded = () => {
    markAssetReady();
  };

  const options = challenge.ui.options || [];
  const assetUrl = challenge.assets[0];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOption || disabled || isSubmitting) return;
    onSubmit(selectedOption);
  };

  const handleZoom = (delta: number) => {
    setZoomLevel((prev) => Math.min(Math.max(0.75, prev + delta), 2.5));
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col items-center w-full max-w-5xl mx-auto">
      {/* Header Instruction Banner */}
      <div className="w-full bg-[#161a25] border-t border-x border-[#2b3145] rounded-t-xl p-4 sm:p-5 text-center shadow-lg">
        <span className="text-xs uppercase tracking-wider font-mono text-emerald-400 font-semibold block mb-1">
          {challenge.levelLabel}: Visual Path Tracing
        </span>
        <h2 className="text-base sm:text-xl font-semibold text-white">
          {challenge.instruction}
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          Trace the continuous highlighted cable across crossover bridges to its connected destination.
        </p>
      </div>

      {/* Image Canvas Container with Zoom/Pan controls */}
      <div className="w-full bg-[#0d1017] border border-[#2b3145] p-3 relative flex flex-col items-center">
        {/* Toolbar */}
        <div className="w-full flex items-center justify-between pb-2.5 px-2 text-xs font-mono text-gray-400 border-b border-gray-800 mb-2">
          <span className="text-gray-300 font-medium">Pan & Zoom Controls</span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => handleZoom(-0.25)}
              className="px-2.5 py-1 rounded-md bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 font-bold transition-colors cursor-pointer"
              title="Zoom out"
            >
              -
            </button>
            <span className="w-14 text-center text-gray-300 font-semibold">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              type="button"
              onClick={() => handleZoom(0.25)}
              className="px-2.5 py-1 rounded-md bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 font-bold transition-colors cursor-pointer"
              title="Zoom in"
            >
              +
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel(1)}
              className="px-2.5 py-1 rounded-md bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 ml-1 transition-colors cursor-pointer"
            >
              Reset
            </button>
            <button
              type="button"
              onClick={() => setIsExpanded((prev) => !prev)}
              className="px-3 py-1 rounded-md bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 ml-2 transition-colors cursor-pointer"
            >
              {isExpanded ? "Standard View" : "Enlarge View"}
            </button>
          </div>
        </div>

        {/* Scrollable Viewport */}
        <div
          className={`w-full overflow-auto rounded-lg bg-black/40 border border-gray-900 transition-all ${
            isExpanded ? "max-h-[80vh]" : "max-h-[520px]"
          }`}
        >
          <div
            style={{
              width: `${zoomLevel * 100}%`,
              minWidth: zoomLevel > 1 ? "1200px" : "100%",
              transformOrigin: "top left",
            }}
            className="flex items-center justify-center p-1"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={imgRef}
              src={assetUrl}
              alt="Tangled cable paths connection diagram"
              onLoad={handleImageLoaded}
              loading="eager"
              className="w-full h-auto object-contain select-none"
            />
          </div>
        </div>
      </div>

      {/* Answer Selection Keypad / Options */}
      <div className="w-full bg-[#161a25] border-b border-x border-[#2b3145] rounded-b-xl p-4 sm:p-5 flex flex-col gap-4 shadow-lg">
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-xs sm:text-sm font-mono text-gray-300 font-semibold">
              Select Connected Destination:
            </span>
            {selectedOption && (
              <span className="text-xs font-mono text-emerald-400 font-bold bg-emerald-950/60 px-3 py-1 rounded-md border border-emerald-800/80">
                Selected: {selectedOption.replace(/_/g, " ")}
              </span>
            )}
          </div>

          {/* Options Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-4 lg:grid-cols-8 gap-2 p-2 bg-[#10131b] rounded-lg border border-gray-800">
            {options.map((option) => {
              const isSelected = selectedOption === option;
              const displayLabel = option.replace(/_/g, " ");

              return (
                <button
                  key={option}
                  type="button"
                  disabled={disabled || isSubmitting}
                  onClick={() => setSelectedOption(option)}
                  aria-pressed={isSelected}
                  className={`py-2 px-2.5 rounded-lg text-xs font-mono font-medium transition-all duration-100 border text-center truncate cursor-pointer ${
                    isSelected
                      ? "bg-emerald-600 border-emerald-400 text-white font-bold shadow-md shadow-emerald-600/30 scale-102"
                      : "bg-[#181d29] border-gray-800 text-gray-300 hover:bg-[#22293a] hover:text-white"
                  }`}
                >
                  {displayLabel}
                </button>
              );
            })}
          </div>
        </div>

        {/* Submit Action */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-800">
          <span className="text-xs font-mono text-gray-400">
            {selectedOption ? "Ready to verify connection" : "Please select an option above"}
          </span>

          <button
            type="submit"
            disabled={!selectedOption || disabled || isSubmitting}
            className={`px-6 py-2.5 rounded-lg text-xs sm:text-sm font-mono font-semibold transition-all duration-150 flex items-center justify-center gap-2 ${
              !selectedOption || disabled || isSubmitting
                ? "bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700/50"
                : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-md hover:shadow-emerald-500/25 border border-emerald-400 cursor-pointer"
            }`}
          >
            {isSubmitting ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Verifying...
              </>
            ) : (
              "Verify Answer"
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
