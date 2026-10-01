import Link from "next/link";

interface NavbarProps {
  currentLevelLabel?: string;
}

export function Navbar({ currentLevelLabel }: NavbarProps) {
  return (
    <header className="border-b border-[#23293d]/80 bg-[#0d111b]/80 backdrop-blur-md sticky top-0 z-50 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="group flex items-center gap-2.5 font-mono text-sm tracking-wider font-bold text-gray-100 hover:text-white transition-all"
          >
            <span className="w-3 h-3 rounded bg-gradient-to-tr from-blue-600 to-cyan-400 group-hover:scale-110 transition-transform shadow-[0_0_10px_rgba(59,130,246,0.5)]"></span>
            <span className="bg-gradient-to-r from-gray-100 via-gray-200 to-gray-400 bg-clip-text text-transparent group-hover:from-white group-hover:to-cyan-200">
              CAPTCHA BENCHMARK
            </span>
          </Link>
          <span className="text-[11px] font-mono text-cyan-500/80 hidden md:inline-block border-l border-gray-800 pl-3 uppercase tracking-wider">
            Cognitive Machine Vision Lab
          </span>
        </div>

        {/* Navigation Links */}
        <nav className="flex items-center gap-2 sm:gap-4 text-xs font-mono">
          {currentLevelLabel && (
            <span className="px-2.5 py-1 rounded-md bg-blue-950/80 text-blue-300 border border-blue-700/60 font-semibold shadow-inner">
              {currentLevelLabel}
            </span>
          )}

          <Link
            href="/challenges"
            className="text-gray-300 hover:text-white px-3 py-1.5 rounded-lg hover:bg-white/5 border border-transparent hover:border-gray-800 transition-all font-medium"
          >
            Challenges
          </Link>
        </nav>
      </div>
    </header>
  );
}
