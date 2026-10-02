import type { ClientChallenge } from "../challenges/types";
import type { Cohort } from "./protocol";

export type TrialAction = "answer" | "skip" | "timeout";
export interface TrialSubmission {
  trialId: string;
  action: TrialAction;
  answer?: number[] | string;
  solveTimeMs: number;
  interrupted: boolean;
}
export interface PersonalSummary {
  accuracy: number;
  medianSolveTimeMs: number | null;
  skipped: number;
  timedOut: number;
  total: number;
}
export interface SessionView {
  status: "active" | "completed" | "abandoned";
  cohort: Cohort;
  progress: { completed: number; total: number };
  trial?: { trialId: string; position: number; challenge: ClientChallenge; elapsedMs: number; presented: boolean };
  summary?: PersonalSummary;
}
export interface AcceptedSubmission {
  accepted: true;
  progress: { completed: number; total: number };
  hasNext: boolean;
}
