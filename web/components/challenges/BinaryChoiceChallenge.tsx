"use client";

import { useState, useEffect, useRef } from "react";
import type { ClientChallenge } from "@/lib/challenges/types";

interface BinaryChoiceChallengeProps {
  challenge: ClientChallenge;
  isSubmitting: boolean;
  onSubmit: (selectedOption: string) => void;
  onAssetsReady: () => void;
  disabled?: boolean;
}

export function BinaryChoiceChallenge({
  challenge,
  isSubmitting,
  onSubmit,
  onAssetsReady,
  disabled = false,
}: BinaryChoiceChallengeProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const assetReadyFired = useRef<boolean>(false);

  useEffect(() => {
    setSelectedOption(null);
    assetReadyFired.current = false;
  }, [challenge.id]);

  const options = challenge.ui.options && challenge.ui.options.length > 0
    ? challenge.ui.options
    : ["Yes", "No"];

  const handleImageLoaded = () => {
    if (!assetReadyFired.current) {
      assetReadyFired.current = true;
      onAssetsReady();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOption || disabled || isSubmitting) return;
    onSubmit(selectedOption);
  };

  const assetUrl = challenge.assets[0];

  return (
    <form onSubmit={handleSubmit} className="flex flex-col items-center w-full max-w-xl mx-auto">
      {/* Instruction Banner */}
      <div className="w-full bg-[#161a25] border-t border-x border-[#2b3145] rounded-t-lg p-4 text-center">
        <span className="text-xs uppercase tracking-wider font-mono text-purple-400 font-semibold block mb-1">
          {challenge.levelLabel}: Visual Perception Illusion
        </span>
        <h2 className="text-base sm:text-lg font-medium text-white">
          {challenge.instruction}
        </h2>
      </div>

      {/* Asset Display Card */}
      <div className="w-full bg-[#12151e] border border-[#2b3145] p-3 flex justify-center items-center">
        <div className="relative max-w-md w-full rounded overflow-hidden border border-gray-800 shadow-md">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={assetUrl}
            alt="Adelson checker shadow illusion visual stimulus"
            onLoad={handleImageLoaded}
            loading="eager"
            className="w-full h-auto object-contain select-none"
          />
        </div>
      </div>

      {/* Options and Submission Footer */}
      <div className="w-full bg-[#161a25] border-b border-x border-[#2b3145] rounded-b-lg p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Binary Choice Buttons */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          {options.map((option) => {
            const isSelected = selectedOption === option;
            return (
              <button
                key={option}
                type="button"
                disabled={disabled || isSubmitting}
                onClick={() => setSelectedOption(option)}
                aria-pressed={isSelected}
                className={`flex-1 sm:flex-none px-6 py-2.5 rounded font-mono text-sm font-semibold transition-all duration-150 border focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 ${
                  isSelected
                    ? "bg-purple-600 border-purple-400 text-white shadow-md shadow-purple-600/30 scale-102"
                    : "bg-[#1f2433] border-gray-700 text-gray-300 hover:bg-[#282e42] hover:text-white"
                }`}
              >
                {option}
              </button>
            );
          })}
        </div>

        {/* Submit Verification Button */}
        <button
          type="submit"
          disabled={!selectedOption || disabled || isSubmitting}
          className={`w-full sm:w-auto px-6 py-2.5 rounded text-xs sm:text-sm font-mono font-semibold transition-all duration-150 flex items-center justify-center gap-2 ${
            !selectedOption || disabled || isSubmitting
              ? "bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700/50"
              : "bg-purple-600 hover:bg-purple-500 text-white shadow-md hover:shadow-purple-500/25 border border-purple-400"
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
    </form>
  );
}

