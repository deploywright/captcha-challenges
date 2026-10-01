import Link from "next/link";
import { Navbar } from "@/components/Navbar";

export default function NotFound() {
  return (
    <>
      <Navbar />
      <main className="flex-1 max-w-lg mx-auto px-4 py-16 flex flex-col items-center justify-center text-center">
        <div className="p-4 rounded-full bg-red-950/60 border border-red-800 text-red-400 mb-4 font-mono text-sm">
          404
        </div>
        <h1 className="text-xl font-bold text-white mb-2">Page Not Found</h1>
        <p className="text-xs text-gray-400 mb-6 font-mono">
          The requested page or challenge does not exist.
        </p>
        <Link
          href="/challenges"
          className="px-5 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs font-semibold"
        >
          Return to Level Select
        </Link>
      </main>
    </>
  );
}
