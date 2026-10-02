import { TRIAL_TIMEOUT_MS } from "./protocol";

export interface ClockSnapshot { startedAtUnixMs: number | null; stoppedMs: number | null }
/** One start after assets-ready, one immutable stop, retained across network retries. */
export class TrialClock {
  private startedAt: number | null = null;
  private startedAtUnixMs: number | null = null;
  private baseElapsed = 0;
  private stoppedMs: number | null = null;
  constructor(private monotonic = () => performance.now(), private wall = () => Date.now(), snapshot?: ClockSnapshot) {
    this.stoppedMs = snapshot?.stoppedMs ?? null;
    if (snapshot?.startedAtUnixMs !== null && snapshot?.startedAtUnixMs !== undefined) {
      this.startedAtUnixMs = snapshot.startedAtUnixMs;
      this.baseElapsed = Math.max(0,this.wall()-snapshot.startedAtUnixMs);
    }
  }
  start(resumeElapsed = 0) {
    if (this.startedAt !== null || this.stoppedMs !== null) return;
    this.baseElapsed = Math.max(this.baseElapsed,resumeElapsed);
    this.startedAt = this.monotonic();
    this.startedAtUnixMs ??= this.wall()-this.baseElapsed;
  }
  get started() { return this.startedAt !== null; }
  get stopped() { return this.stoppedMs !== null; }
  elapsed() { return this.stoppedMs ?? Math.min(TRIAL_TIMEOUT_MS,Math.max(0,this.baseElapsed + (this.startedAt === null ? 0 : this.monotonic()-this.startedAt))); }
  stop() { this.stoppedMs ??= Math.round(this.elapsed()); return this.stoppedMs; }
  snapshot(): ClockSnapshot { return {startedAtUnixMs:this.startedAtUnixMs,stoppedMs:this.stoppedMs}; }
}
