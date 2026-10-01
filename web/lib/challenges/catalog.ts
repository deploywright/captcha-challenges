import type {
  ChallengeCatalogEntry,
  ChallengeVariant,
  LevelInfo,
} from "./types";
import catalogJson from "../../public/challenges/catalog.json";

export const CATALOG: ChallengeCatalogEntry[] =
  catalogJson as ChallengeCatalogEntry[];

export const PROGRESSION_VARIANTS: ChallengeVariant[] = [
  "street-grid",
  "hard-street-grid",
  "checker-shadow",
  "tangled-cables",
  "degraded-vision",
];

export function getAllChallenges(): ChallengeCatalogEntry[] {
  return CATALOG;
}

export function getChallengeById(id: string): ChallengeCatalogEntry | undefined {
  return CATALOG.find((c) => c.id === id);
}

export function getChallengesByVariant(
  variant: ChallengeVariant
): ChallengeCatalogEntry[] {
  return CATALOG.filter((c) => c.variant === variant);
}

export function getChallengesByLevel(level: number): ChallengeCatalogEntry[] {
  return CATALOG.filter((c) => c.level === level);
}

export function getRandomChallenge(
  variant?: ChallengeVariant,
  excludeId?: string
): ChallengeCatalogEntry | undefined {
  const pool = variant
    ? CATALOG.filter((c) => c.variant === variant && c.id !== excludeId)
    : CATALOG.filter((c) => c.id !== excludeId);

  if (pool.length === 0) {
    // If excluding the only challenge, fallback to pool without exclude
    const fallback = variant
      ? CATALOG.filter((c) => c.variant === variant)
      : CATALOG;
    return fallback[0];
  }
  const randomIndex = Math.floor(Math.random() * pool.length);
  return pool[randomIndex];
}

export function getNextProgressionChallenge(
  currentId: string
): ChallengeCatalogEntry | undefined {
  const current = getChallengeById(currentId);
  if (!current) return undefined;

  const currentVariantIndex = PROGRESSION_VARIANTS.indexOf(current.variant);
  if (currentVariantIndex === -1 || currentVariantIndex === PROGRESSION_VARIANTS.length - 1) {
    // End of progression reached or unknown variant
    return undefined;
  }

  const nextVariant = PROGRESSION_VARIANTS[currentVariantIndex + 1];
  const candidates = getChallengesByVariant(nextVariant);
  if (candidates.length === 0) return undefined;

  // Pick deterministic or first candidate from next variant
  return candidates[0];
}

export function getLevelInfos(): LevelInfo[] {
  const countsByVariant: Record<string, number> = {};
  const firstIdByVariant: Record<string, string> = {};

  for (const c of CATALOG) {
    countsByVariant[c.variant] = (countsByVariant[c.variant] || 0) + 1;
    if (!firstIdByVariant[c.variant]) {
      firstIdByVariant[c.variant] = c.id;
    }
  }

  return [
    {
      levelNumber: "1",
      variant: "street-grid",
      levelKey: "level_1_street_grid",
      title: "Level 1: Normal CAPTCHA",
      subtitle: "3×3 Standard Street Driving Grid",
      description:
        "Select all images containing the target object (motorcycles, bicycles, buses, trucks, pedestrians, traffic lights) from clearly visible street scenes.",
      count: countsByVariant["street-grid"] || 0,
      sampleId: firstIdByVariant["street-grid"],
    },
    {
      levelNumber: "2A",
      variant: "hard-street-grid",
      levelKey: "level_2a_hard_street_grid",
      title: "Level 2A: Hard CAPTCHA",
      subtitle: "3×3 High-Complexity Street Grid",
      description:
        "Challenging real-world scenes with subtle context, controlled distance, night-time lighting, and distractor objects.",
      count: countsByVariant["hard-street-grid"] || 0,
      sampleId: firstIdByVariant["hard-street-grid"],
    },
    {
      levelNumber: "2B",
      variant: "checker-shadow",
      levelKey: "level_2b_checker_shadow",
      title: "Level 2B: Visual Illusion",
      subtitle: "Canonical Visual Illusions Library",
      description:
        "Test human perception against physical ground truth across canonical visual illusions (Checker Shadow, Müller-Lyer, Ebbinghaus, Ponzo, Simultaneous Contrast, Café Wall).",
      count: countsByVariant["checker-shadow"] || 0,
      sampleId: firstIdByVariant["checker-shadow"],
    },
    {
      levelNumber: "3A",
      variant: "tangled-cables",
      levelKey: "level_3a_tangled_cables",
      title: "Level 3A: Tangled Cables",
      subtitle: "Bijective Visual Path Tracing",
      description:
        "Trace continuous cable paths through clear crossover bridges connecting devices to wall outlets.",
      count: countsByVariant["tangled-cables"] || 0,
      sampleId: firstIdByVariant["tangled-cables"],
    },
    {
      levelNumber: "3B",
      variant: "degraded-vision",
      levelKey: "level_3b_degraded_vision",
      title: "Level 3B: Degraded Vision",
      subtitle: "Controlled Pixelation Ladder",
      description:
        "Multi-resolution downsampled street scenes testing perceptual limits down to extreme pixelation.",
      count: countsByVariant["degraded-vision"] || 0,
      sampleId: firstIdByVariant["degraded-vision"],
    },
  ];
}
