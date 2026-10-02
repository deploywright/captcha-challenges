/** Frozen collection protocol. Change the version before changing these rules. */
export const PROTOCOL_VERSION = "human-v1";
export const TOTAL_TRIALS = 40;
export const TRIAL_TIMEOUT_MS = 120_000;
export const QUOTAS = {
  "street-grid": 6,
  "hard-street-grid": 6,
  "checker-shadow": 6,
  "routing-puzzle": 18,
  "degraded-vision": 4,
} as const;
export type BenchmarkVariant = keyof typeof QUOTAS;
export const STAGES: Record<BenchmarkVariant, string> = {
  "street-grid": "Level 1", "hard-street-grid": "Level 2A",
  "checker-shadow": "Level 2B", "routing-puzzle": "Level 3A",
  "degraded-vision": "Level 3B",
};
export const COHORTS = ["main", "pilot", "smoke", "creator"] as const;
export type Cohort = typeof COHORTS[number];
export const ROUTING_SUBTYPES = ["laser-maze", "conveyor-routing", "pipe-flow", "device-cables"];
export const DIFFICULTIES = ["easy", "medium", "story", "hard", "extreme"];
export const RESOLUTIONS = [64, 48, 32, 24, 16, 12, 8];
