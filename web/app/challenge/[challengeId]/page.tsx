import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import {
  getChallengeById,
  getRandomChallenge,
  getNextProgressionChallenge,
  getAllChallenges,
} from "@/lib/challenges/catalog";
import { toClientChallenge } from "@/lib/challenges/adapter";
import { ChallengePlayer } from "@/components/challenges/ChallengePlayer";

export async function generateStaticParams() {
  const challenges = getAllChallenges();
  return challenges.map((c) => ({
    challengeId: c.id,
  }));
}

interface PageProps {
  params: Promise<{ challengeId: string }>;
}

export default async function ChallengePage({ params }: PageProps) {
  const { challengeId } = await params;
  const entry = getChallengeById(challengeId);

  if (!entry) {
    return (
      <>
        <Navbar />
        <main className="flex-1 max-w-lg mx-auto px-4 py-16 flex flex-col items-center justify-center text-center">
          <div className="p-4 rounded-full bg-red-950/60 border border-red-800 text-red-400 mb-4 font-mono text-sm">
            404
          </div>
          <h1 className="text-xl font-bold text-white mb-2">Challenge Not Found</h1>
          <p className="text-xs text-gray-400 mb-6 font-mono">
            ID: {challengeId}
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

  const clientChallenge = toClientChallenge(entry);
  const anotherInLevel = getRandomChallenge(entry.variant, entry.id)?.id;
  const nextProgression = getNextProgressionChallenge(entry.id)?.id;

  return (
    <>
      <Navbar currentLevelLabel={clientChallenge.levelLabel} />

      <main className="flex-1 max-w-5xl mx-auto px-4 py-6 sm:py-8 w-full flex flex-col items-center">
        <ChallengePlayer
          challenge={clientChallenge}
          anotherInLevelId={anotherInLevel}
          nextProgressionId={nextProgression}
        />
      </main>
    </>
  );
}
