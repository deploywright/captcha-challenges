"use client";

import { useState, useEffect, useRef } from "react";
import type { ClientChallenge } from "@/lib/challenges/types";

interface RoutingPuzzleChallengeProps {
  challenge: ClientChallenge;
  isSubmitting: boolean;
  onSubmit: (selectedOption: string) => void;
  onAssetsReady: () => void;
  disabled?: boolean;
}

export function RoutingPuzzleChallenge({
  challenge,
  isSubmitting,
  onSubmit,
  onAssetsReady,
  disabled = false,
}: RoutingPuzzleChallengeProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const assetReadyFired = useRef<boolean>(false);

  useEffect(() => {
    setSelectedOption(null);
    setZoomLevel(1);
    setIsExpanded(false);
    assetReadyFired.current = false;
  }, [challenge.id]);

  const handleImageLoaded = () => {
    if (!assetReadyFired.current) {
      assetReadyFired.current = true;
      onAssetsReady();
    }
  };

  const options = challenge.ui.options || [];
  const assetUrl = challenge.assets[0];
  const subtype = challenge.subtype || "laser-maze";

  // Subtype badge and styling configuration
  const subtypeConfig: Record<
    string,
    { label: string; badgeCls: string; subtitle: string }
  > = {
    "laser-maze": {
      label: "Laser Maze",
      badgeCls: "bg-amber-950/80 text-amber-300 border-amber-700/80",
      subtitle: "Optical Reflection Ray Tracing",
    },
    "conveyor-routing": {
      label: "Conveyor Routing",
      badgeCls: "bg-emerald-950/80 text-emerald-300 border-emerald-700/80",
      subtitle: "Industrial Mechanical Diverters",
    },
    "pipe-flow": {
      label: "Pipe Flow",
      badgeCls: "bg-blue-950/80 text-blue-300 border-blue-700/80",
      subtitle: "Fluid Gate Valve Network",
    },
    "device-cables": {
      label: "Device Cables",
      badgeCls: "bg-purple-950/80 text-purple-300 border-purple-700/80",
      subtitle: "Clear Bridge Cable Tracing",
    },
  };

  const currentSubtypeConfig = subtypeConfig[subtype] || {
    label: "Routing Puzzle",
    badgeCls: "bg-cyan-950/80 text-cyan-300 border-cyan-700/80",
    subtitle: "Visual Path Reasoning",
  };

  // Keyboard shortcut listener (1-9 or A-E)
  useEffect(() => {
    if (disabled || isSubmitting) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Check number keys: '1' -> options[0], '2' -> options[1], etc.
      const num = parseInt(e.key, 10);
      if (!isNaN(num) && num >= 1 && num <= options.length) {
        setSelectedOption(options[num - 1]);
        return;
      }

      // Check letter keys (e.g. 'a', 'b', 'c', 'd')
      const letter = e.key.toUpperCase();
      const match = options.find(
        (opt) =>
          opt.toUpperCase() === letter ||
          opt.toUpperCase().endsWith(` ${letter}`) ||
          opt.toUpperCase().startsWith(`${letter}:`)
      );
      if (match) {
        setSelectedOption(match);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [disabled, isSubmitting, options]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOption || disabled || isSubmitting) return;
    onSubmit(selectedOption);
  };

  const handleZoom = (delta: number) => {
    setZoomLevel((prev) => Math.min(Math.max(0.75, Math.round((prev + delta) * 100) / 100), 2.5));
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col items-center w-full max-w-4xl mx-auto shadow-2xl rounded-xl overflow-hidden border border-slate-800 bg-[#0b0f19]"
    >
      {/* Header Instruction Banner */}
      <div className="w-full bg-[#111827] border-b border-slate-800 px-4 py-3.5 sm:px-6 sm:py-4 flex flex-col items-center text-center">
        <div className="flex items-center gap-2 mb-1.5 flex-wrap justify-center">
          <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800/80">
            {challenge.levelLabel}
          </span>
          <span
            className={`text-xs font-mono font-semibold px-2.5 py-0.5 rounded border ${currentSubtypeConfig.badgeCls}`}
          >
            {currentSubtypeConfig.label}
          </span>
          <span className="text-xs text-slate-400 font-mono hidden md:inline">
            • {currentSubtypeConfig.subtitle}
          </span>
        </div>

        <h2 className="text-base sm:text-lg md:text-xl font-semibold text-white tracking-tight">
          {challenge.instruction}
        </h2>
      </div>

      {/* Image Canvas Container with Zoom/Pan controls */}
      <div className="w-full bg-[#070b13] p-2 relative flex flex-col items-center">
        {/* Toolbar */}
        <div className="w-full flex items-center justify-between pb-2 px-3 text-xs font-mono text-slate-400 border-b border-slate-800/70 mb-2">
          <span className="text-[11px] text-slate-500">
            Use mouse / touch to trace path
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => handleZoom(-0.25)}
              className="w-7 h-6 flex items-center justify-center rounded bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
              title="Zoom out"
            >
              -
            </button>
            <span className="w-12 text-center text-slate-300 select-none">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              type="button"
              onClick={() => handleZoom(0.25)}
              className="w-7 h-6 flex items-center justify-center rounded bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
              title="Zoom in"
            >
              +
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel(1)}
              className="px-2 h-6 flex items-center justify-center rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 ml-1 text-[11px] transition"
            >
              Reset
            </button>
            <button
              type="button"
              onClick={() => setIsExpanded((prev) => !prev)}
              className="px-2.5 h-6 flex items-center justify-center rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 ml-1.5 text-[11px] transition"
            >
              {isExpanded ? "Collapse" : "Expand"}
            </button>
          </div>
        </div>

        {/* Scrollable Viewport */}
        <div
          className={`w-full overflow-auto rounded-lg bg-black/60 border border-slate-900 transition-all ${
            isExpanded ? "max-h-[82vh]" : "max-h-[520px]"
          }`}
        >
          <div
            style={{
              width: `${zoomLevel * 100}%`,
              minWidth: zoomLevel > 1 ? "1100px" : "100%",
              transformOrigin: "top left",
            }}
            className="flex items-center justify-center p-1 mx-auto"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={assetUrl}
              alt={challenge.instruction}
              onLoad={handleImageLoaded}
              loading="eager"
              className="w-full h-auto object-contain select-none rounded"
            />
          </div>
        </div>
      </div>

      {/* Answer Selection Keypad / Options */}
      <div className="w-full bg-[#111827] border-t border-slate-800 p-4 sm:p-5 flex flex-col gap-4">
        <div>
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="text-xs font-mono text-slate-300 font-semibold tracking-wide">
              Select Your Answer:
            </span>
            {selectedOption ? (
              <span className="text-xs font-mono text-emerald-400 font-bold bg-emerald-950/80 px-2.5 py-0.5 rounded border border-emerald-800/80">
                Selected: {selectedOption}
              </span>
            ) : (
              <span className="text-[11px] font-mono text-slate-500">
                Press 1-{options.length} or click an option
              </span>
            )}
          </div>

          {/* Options Grid */}
          <div
            className={`grid gap-2.5 ${
              options.length <= 4
                ? "grid-cols-2 sm:grid-cols-4"
                : options.length <= 6
                ? "grid-cols-2 sm:grid-cols-3 md:grid-cols-6"
                : "grid-cols-2 sm:grid-cols-4 md:grid-cols-8"
            }`}
          >
            {options.map((option, idx) => {
              const isSelected = selectedOption === option;

              return (
                <button
                  key={option}
                  type="button"
                  disabled={disabled || isSubmitting}
                  onClick={() => setSelectedOption(option)}
                  aria-pressed={isSelected}
                  className={`py-2.5 px-3 rounded-lg text-xs sm:text-sm font-mono font-medium transition-all duration-150 border text-center flex flex-col items-center justify-center gap-0.5 select-none ${
                    isSelected
                      ? "bg-blue-600 border-blue-400 text-white font-bold shadow-lg shadow-blue-600/30 scale-102 ring-2 ring-blue-400/50"
                      : "bg-[#1a2234] border-slate-800 text-slate-200 hover:bg-[#232d44] hover:text-white hover:border-slate-700"
                  }`}
                >
                  <span className="text-[10px] text-slate-400 font-mono">
                    [{idx + 1}]
                  </span>
                  <span className="truncate w-full">{option}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Submit Action Bar */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
          <span className="text-xs font-mono text-slate-500">
            {selectedOption
              ? "Option chosen. Click verify or press Enter."
              : "Please select an answer above"}
          </span>

          <button
            type="submit"
            disabled={!selectedOption || disabled || isSubmitting}
            className={`px-7 py-2.5 rounded-lg text-xs sm:text-sm font-mono font-semibold transition-all duration-150 flex items-center justify-center gap-2 ${
              !selectedOption || disabled || isSubmitting
                ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/40"
                : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg hover:shadow-blue-500/25 border border-blue-400 active:scale-98"
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
