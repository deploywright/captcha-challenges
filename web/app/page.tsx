import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { getLevelInfos, getChallengesByVariant } from "@/lib/challenges/catalog";

export const metadata = {
  title: "CAPTCHA Challenges | Visual Perception Benchmark",
  description: "Standardized visual perception benchmark evaluating visual cognition across 5 difficulty tiers.",
};

export default function HomePage() {
  const levels = getLevelInfos();
  const level1Challenges = getChallengesByVariant("street-grid");
  const firstChallengeId = level1Challenges[0]?.id || "lvl1_05ema8";

  return (
    <>
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16 space-y-16">
        {/* Hero Section */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-[#121626]/90 via-[#0d101a]/95 to-[#080a10] border border-[#232a40] p-8 sm:p-14 shadow-2xl text-center">
          {/* Ambient Glow Effects */}
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-96 h-96 bg-blue-500/15 rounded-full blur-[100px] pointer-events-none" />
          <div className="absolute top-1/2 -left-20 w-80 h-80 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />
          <div className="absolute bottom-0 right-10 w-80 h-80 bg-cyan-500/10 rounded-full blur-[90px] pointer-events-none" />

          <div className="relative z-10 max-w-4xl mx-auto space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono font-medium bg-blue-950/70 border border-blue-600/50 text-blue-300 shadow-inner">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>COGNITIVE MACHINE VISION LAB • BENCHMARK V1.0</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
              Visual Perception <br />
              <span className="bg-gradient-to-r from-blue-400 via-cyan-300 to-indigo-300 bg-clip-text text-transparent">
                CAPTCHA Challenges
              </span>
            </h1>

            <p className="text-base sm:text-lg text-gray-300 max-w-2xl mx-auto leading-relaxed">
              Standardized empirical evaluation across 5 perceptual tiers. Test fine-grained recognition,
              contextual illumination illusions, tangled visual tracing, and severe sensor degradation.
            </p>

            {/* CTAs */}
            <div className="pt-4 flex flex-wrap items-center justify-center gap-3.5">
              <Link
                href={`/challenge/${firstChallengeId}`}
                className="px-6 py-3 rounded-xl font-mono text-sm font-bold bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white shadow-lg shadow-blue-500/25 border border-cyan-400/40 transition-all hover:scale-[1.02] flex items-center gap-2"
              >
                <span>Start Challenge (Level 1)</span>
                <span>→</span>
              </Link>

              <Link
                href="/challenges"
                className="px-5 py-3 rounded-xl font-mono text-sm text-gray-300 hover:text-white bg-[#141824] hover:bg-[#1a2030] border border-gray-700/80 transition-all"
              >
                Browse All Tiers
              </Link>
            </div>
          </div>
        </div>

        {/* Level Tiers Grid Showcase */}
        <section className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-mono font-bold text-blue-400 uppercase tracking-wider mb-1">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                STANDARDIZED TEST SUITE
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                Perceptual Challenge Tiers
              </h2>
            </div>

            <Link
              href="/challenges"
              className="text-xs font-mono text-blue-400 hover:text-cyan-300 font-semibold flex items-center gap-1 group"
            >
              <span>View details on all 5 tiers</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {levels.map((lvl) => {
              const accentColor =
                lvl.levelNumber === "1"
                  ? "from-blue-500/20 to-transparent border-blue-500/30 text-blue-400"
                  : lvl.levelNumber === "2A"
                  ? "from-indigo-500/20 to-transparent border-indigo-500/30 text-indigo-400"
                  : lvl.levelNumber === "2B"
                  ? "from-amber-500/20 to-transparent border-amber-500/30 text-amber-400"
                  : lvl.levelNumber === "3A"
                  ? "from-emerald-500/20 to-transparent border-emerald-500/30 text-emerald-400"
                  : "from-red-500/20 to-transparent border-red-500/30 text-red-400";

              return (
                <div
                  key={lvl.variant}
                  className="group bg-[#121622]/90 hover:bg-[#151a2a] border border-[#22283a] hover:border-[#3b4766] rounded-2xl p-5 flex flex-col justify-between transition-all duration-300 relative overflow-hidden shadow-lg hover:shadow-2xl hover:scale-[1.01]"
                >
                  <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl ${accentColor} rounded-bl-full pointer-events-none opacity-40 group-hover:opacity-80 transition-opacity`} />

                  <div className="relative z-10 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-white">
                        Level {lvl.levelNumber}
                      </span>
                      <span className="text-[11px] font-mono text-gray-400 bg-black/40 px-2 py-0.5 rounded">
                        {lvl.count} probes
                      </span>
                    </div>

                    <div>
                      <h3 className="text-base font-bold text-white group-hover:text-cyan-200 transition-colors">
                        {lvl.title.replace(`Level ${lvl.levelNumber}: `, "")}
                      </h3>
                      <span className="text-xs font-mono text-gray-400 block mt-0.5">
                        {lvl.subtitle}
                      </span>
                    </div>

                    <p className="text-xs text-gray-300 leading-relaxed">
                      {lvl.description}
                    </p>
                  </div>

                  <div className="relative z-10 mt-6 pt-3 border-t border-white/5 flex items-center justify-between">
                    <span className="text-[10px] font-mono text-gray-500 uppercase">
                      ID: {lvl.variant}
                    </span>
                    <Link
                      href={lvl.sampleId ? `/challenge/${lvl.sampleId}` : "/challenges"}
                      className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-white/5 hover:bg-blue-600 text-gray-200 hover:text-white border border-white/10 hover:border-blue-400 transition-all flex items-center gap-1 cursor-pointer"
                    >
                      <span>Play Level</span>
                      <span>→</span>
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Experiment Protocol Footer */}
        <div className="p-4 rounded-xl bg-[#0c0f18] border border-gray-800/80 text-center">
          <p className="text-xs font-mono text-gray-400">
            Timing measured strictly client-side from stimulus render to submission. All challenges evaluated against sealed server-side ground truth.
          </p>
        </div>
      </main>
    </>
  );
}
