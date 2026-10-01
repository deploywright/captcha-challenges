import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import {
  getLevelInfos,
  getChallengesByVariant,
} from "@/lib/challenges/catalog";

export const metadata = {
  title: "Level Select | CAPTCHA Benchmark",
  description: "Select from 5 standardized perceptual visual challenge tiers or begin sequential progression.",
};

export default function ChallengesPage() {
  const levels = getLevelInfos();
  const firstLevel1 = getChallengesByVariant("street-grid")[0]?.id || "lvl1_05ema8";

  const levelBadges: Record<string, { tag: string; color: string; border: string; bg: string }> = {
    "1": {
      tag: "Object Recognition",
      color: "text-blue-400",
      border: "border-blue-500/30",
      bg: "bg-blue-950/40",
    },
    "2A": {
      tag: "Occlusion & Glare",
      color: "text-indigo-400",
      border: "border-indigo-500/30",
      bg: "bg-indigo-950/40",
    },
    "2B": {
      tag: "Optical Illusion",
      color: "text-amber-400",
      border: "border-amber-500/30",
      bg: "bg-amber-950/40",
    },
    "3A": {
      tag: "Topological Tracing",
      color: "text-emerald-400",
      border: "border-emerald-500/30",
      bg: "bg-emerald-950/40",
    },
    "3B": {
      tag: "Severe Sensor Noise",
      color: "text-red-400",
      border: "border-red-500/30",
      bg: "bg-red-950/40",
    },
  };

  return (
    <>
      <Navbar />

      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 w-full space-y-8">
        {/* Page Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#121624] via-[#0e111a] to-[#0a0c14] border border-[#232a3e] p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-blue-950/80 border border-blue-700/60 text-blue-300">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>TEST SUITE CATALOG</span>
            </div>
            <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-white">
              Benchmark Level Select
            </h1>
            <p className="text-xs sm:text-sm text-gray-300">
              Select an individual test level below or launch standard sequential progression across all 5 tiers.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href={`/challenge/${firstLevel1}`}
              className="px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white shadow-lg shadow-blue-500/25 border border-cyan-400/40 transition-all flex items-center gap-1.5"
            >
              <span>Sequential Run</span>
              <span>→</span>
            </Link>
          </div>
        </div>

        {/* Level Cards Stack */}
        <div className="space-y-4">
          {levels.map((lvl) => {
            const challengesInLevel = getChallengesByVariant(lvl.variant);
            const firstId = challengesInLevel[0]?.id;
            const badgeMeta = levelBadges[lvl.levelNumber] || {
              tag: "Perception",
              color: "text-blue-400",
              border: "border-blue-500/30",
              bg: "bg-blue-950/40",
            };

            return (
              <div
                key={lvl.variant}
                className="group bg-[#111520]/90 hover:bg-[#141926] border border-[#212739] hover:border-[#38435f] rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 transition-all duration-200 shadow-md hover:shadow-xl relative overflow-hidden"
              >
                <div className="space-y-2 max-w-3xl">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="px-3 py-1 rounded-lg text-xs font-mono font-bold bg-white/5 text-white border border-white/10 shadow-inner">
                      Level {lvl.levelNumber}
                    </span>
                    <span className={`text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded-full border ${badgeMeta.bg} ${badgeMeta.border} ${badgeMeta.color}`}>
                      {badgeMeta.tag}
                    </span>
                    <h2 className="text-lg font-bold text-white group-hover:text-cyan-200 transition-colors">
                      {lvl.title.replace(`Level ${lvl.levelNumber}: `, "")}
                    </h2>
                  </div>

                  <p className="text-xs sm:text-sm text-gray-300 leading-relaxed">
                    {lvl.description}
                  </p>

                  <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-gray-400 pt-1">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                      Probes: <strong className="text-white">{lvl.count}</strong>
                    </span>
                    <span>•</span>
                    <span className="text-gray-400">
                      Variant: <code className="text-gray-300 font-mono">{lvl.variant}</code>
                    </span>
                    <span>•</span>
                    <span className="text-gray-400">
                      Type: <span className="text-gray-300">{lvl.subtitle}</span>
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto justify-end shrink-0">
                  {firstId && (
                    <Link
                      href={`/challenge/${firstId}`}
                      className="w-full md:w-auto px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-[#1a2133] hover:bg-blue-600 text-gray-200 hover:text-white border border-[#2d3752] hover:border-blue-400 transition-all text-center flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      <span>Launch Tier {lvl.levelNumber}</span>
                      <span>→</span>
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Experiment Integrity Notice */}
        <div className="rounded-2xl p-6 bg-[#0c0f18] border border-gray-800 text-xs font-mono text-gray-400 space-y-2">
          <div className="flex items-center gap-2 text-gray-200 font-semibold">
            <span className="w-2 h-2 rounded-full bg-blue-400" />
            BENCHMARK INTEGRITY PROTOCOL
          </div>
          <p className="leading-relaxed">
            All challenges are derived from held-out validation sets (BDD100K val) and procedural algorithms with fixed seeds.
            Ground truth evaluation executes strictly on the secure server side, preventing answer leakage.
          </p>
        </div>
      </main>
    </>
  );
}
