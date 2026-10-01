export type ChallengeVariant =
  | "street-grid"
  | "hard-street-grid"
  | "checker-shadow"
  | "tangled-cables"
  | "routing-puzzle"
  | "degraded-vision";

export type RoutingPuzzleSubtype =
  | "laser-maze"
  | "conveyor-routing"
  | "pipe-flow"
  | "device-cables";

export type ChallengeType = "image-selection" | "single-choice";

export interface ChallengeUiConfig {
  rows?: number;
  columns?: number;
  selectionMode?: "single" | "multiple";
  options?: string[];
}

export interface ClientChallenge {
  id: string;
  level: number;
  levelKey: string;
  variant: ChallengeVariant;
  subtype?: RoutingPuzzleSubtype | string;
  displayName: string;
  levelLabel: string;
  type: ChallengeType;
  instruction: string;
  seed: number;
  assets: string[];
  ui: ChallengeUiConfig;
  resolution?: number;
  seriesId?: string;
}

export interface ChallengeCatalogEntry {
  id: string;
  level: number;
  levelKey: string;
  variant: ChallengeVariant;
  subtype?: RoutingPuzzleSubtype | string;
  displayName: string;
  levelLabel: string;
  type: ChallengeType;
  instruction: string;
  seed?: number;
  ui: ChallengeUiConfig;
  assetCount: number;
  assets: string[];
  challengeUrl: string;
  resolution?: number;
  seriesId?: string;
}

export interface SubmissionPayload {
  answer: number[] | string | number;
  solveTimeMs?: number;
}

export interface SubmissionResponse {
  correct: boolean;
  challengeId: string;
  variant: ChallengeVariant;
  solveTimeMs?: number;
  message?: string;
}

export interface LevelInfo {
  levelNumber: string; // "1", "2A", "2B", "3A", "3B"
  variant: ChallengeVariant;
  levelKey: string;
  title: string;
  subtitle: string;
  description: string;
  count: number;
  sampleId?: string;
}
