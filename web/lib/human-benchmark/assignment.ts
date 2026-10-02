import type { ChallengeCatalogEntry } from "../challenges/types";
import { DIFFICULTIES, QUOTAS, RESOLUTIONS, ROUTING_SUBTYPES, TOTAL_TRIALS } from "./protocol";

export type ExposureCounts = Readonly<Record<string, number>>;

/** Stable seed-derived tie breaking, never used for authentication. */
function randomFor(seed: string) {
  let state = 2166136261;
  for (const char of seed) state = Math.imul(state ^ char.charCodeAt(0), 16777619);
  return () => {
    state += 0x6D2B79F5;
    let value = Math.imul(state ^ state >>> 15, 1 | state);
    value ^= value + Math.imul(value ^ value >>> 7, 61 | value);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

export function assignChallenges(catalog: readonly ChallengeCatalogEntry[], counts: ExposureCounts, seed: string): ChallengeCatalogEntry[] {
  if (new Set(catalog.map(c => c.id)).size !== catalog.length) throw new Error("Duplicate catalog IDs");
  const random = randomFor(seed);
  const tie = new Map(catalog.map(c => c.id).sort().map(id => [id, random()]));
  const exposure = (c: ChallengeCatalogEntry) => counts[c.id] ?? 0;
  const least = (pool: ChallengeCatalogEntry[]) => pool.sort((a,b) => exposure(a) - exposure(b) || tie.get(a.id)! - tie.get(b.id)!);
  const selected: ChallengeCatalogEntry[] = [];
  for (const variant of ["street-grid", "hard-street-grid", "checker-shadow"] as const) {
    const pool = least(catalog.filter(c => c.variant === variant));
    if (pool.length < QUOTAS[variant] || (variant === "checker-shadow" && pool.length !== 6)) throw new Error(`Invalid ${variant} pool`);
    selected.push(...pool.slice(0, QUOTAS[variant]));
  }

  // Actual pools differ in size (2/3/5/3/2 per difficulty). Prefer least-exposed
  // IDs, then fresh strata, while reserving coverage of every subtype/difficulty.
  const routing = catalog.filter(c => c.variant === "routing-puzzle");
  const strata = ROUTING_SUBTYPES.flatMap(subtype => DIFFICULTIES.map(difficulty => {
    const pool = least(routing.filter(c => c.subtype === subtype && c.difficulty === difficulty));
    if (!pool.length) throw new Error("Incomplete routing strata");
    return { subtype, difficulty, pool, count: pool.reduce((sum,c) => sum + exposure(c), 0), tie: random() };
  }));
  const routingSelected: ChallengeCatalogEntry[] = [];
  const stratumCounts = new Map<string,number>();
  const stratumKey = (c: ChallengeCatalogEntry) => `${c.subtype}:${c.difficulty}`;
  const historicStrata = new Map(strata.map(s => [`${s.subtype}:${s.difficulty}`,s.count/s.pool.length]));
  while (routingSelected.length < QUOTAS["routing-puzzle"]) {
    const candidates = routing.filter(c => !routingSelected.some(s => s.id === c.id));
    candidates.sort((a,b) => exposure(a)-exposure(b) || (stratumCounts.get(stratumKey(a)) ?? 0)-(stratumCounts.get(stratumKey(b)) ?? 0) || (historicStrata.get(stratumKey(a)) ?? 0)-(historicStrata.get(stratumKey(b)) ?? 0) || tie.get(a.id)!-tie.get(b.id)!);
    const choice = candidates.find(c => {
      const prospective = [...routingSelected,c];
      const slots = QUOTAS["routing-puzzle"] - prospective.length;
      const missingSubtypes = ROUTING_SUBTYPES.filter(s => !prospective.some(x => x.subtype === s));
      const missingDifficulties = DIFFICULTIES.filter(d => !prospective.some(x => x.difficulty === d));
      return Math.max(missingSubtypes.length,missingDifficulties.length) <= slots;
    });
    if (!choice) throw new Error("Routing coverage is unavailable");
    routingSelected.push(choice);
    stratumCounts.set(stratumKey(choice),(stratumCounts.get(stratumKey(choice)) ?? 0)+1);
  }
  selected.push(...routingSelected);

  const degraded = catalog.filter(c => c.variant === "degraded-vision");
  const series = [...new Set(degraded.map(c => c.seriesId))].sort();
  if (series.length !== 4 || series.some(s => !s)) throw new Error("Expected four distinct degraded series");
  const pools = series.map(id => {
    const pool = degraded.filter(c => c.seriesId === id);
    if (pool.length !== RESOLUTIONS.length || RESOLUTIONS.some(r => pool.filter(c => c.resolution === r).length !== 1)) throw new Error("Incomplete resolution ladder");
    // Lowest assignment count per scene takes priority over resolution diversity.
    const min = Math.min(...pool.map(exposure));
    return pool.filter(c => exposure(c) === min);
  });
  const resolutionCounts = new Map(RESOLUTIONS.map(r => [r, degraded.filter(c => c.resolution === r).reduce((sum,c) => sum + exposure(c), 0)]));
  let best: ChallengeCatalogEntry[] = [];
  let bestScore = [Infinity, Infinity, Infinity];
  const search = (chosen: ChallengeCatalogEntry[], index: number) => {
    if (index < pools.length) { for (const c of pools[index]) search([...chosen,c], index + 1); return; }
    const score = [4 - new Set(chosen.map(c => c.resolution)).size, chosen.reduce((sum,c) => sum + (resolutionCounts.get(c.resolution!) ?? 0), 0), chosen.reduce((sum,c) => sum + tie.get(c.id)!, 0)];
    if (score[0] < bestScore[0] || score[0] === bestScore[0] && (score[1] < bestScore[1] || score[1] === bestScore[1] && score[2] < bestScore[2])) { best = chosen; bestScore = score; }
  };
  search([],0);
  selected.push(...best);
  if (selected.length !== TOTAL_TRIALS || new Set(selected.map(c => c.id)).size !== TOTAL_TRIALS) throw new Error("Invalid assignment");

  // Seeded shuffle followed by a constrained draw prevents runs longer than three.
  const pool = selected.map(c => ({c, tie: random()})).sort((a,b) => a.tie - b.tie).map(x => x.c);
  const ordered: ChallengeCatalogEntry[] = [];
  while (pool.length) {
    const recent = ordered.slice(-3);
    const blocked = recent.length === 3 && recent.every(c => c.variant === recent[0].variant) ? recent[0].variant : null;
    let index = pool.findIndex(c => {
      if (c.variant === blocked) return false;
      const lastRun = [...ordered].reverse().findIndex(x => x.variant !== c.variant);
      const runLength = ordered.at(-1)?.variant === c.variant ? (lastRun < 0 ? ordered.length : lastRun) + 1 : 1;
      const remaining = pool.filter(x => x.id !== c.id);
      return Object.keys(QUOTAS).every(variant => {
        const same = remaining.filter(x => x.variant === variant).length;
        const others = remaining.length - same;
        return same <= others * 3 + (variant === c.variant ? 3 - runLength : 3);
      });
    });
    if (index < 0) index = 0;
    ordered.push(...pool.splice(index,1));
  }
  return ordered;
}
