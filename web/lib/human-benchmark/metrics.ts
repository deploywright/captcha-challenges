export function wilsonInterval(correct: number, total: number): [number, number] | null {
  if (!total) return null;
  const z = 1.959963984540054;
  const p = correct / total;
  const denominator = 1 + z*z/total;
  const center = (p + z*z/(2*total))/denominator;
  const margin = z * Math.sqrt(p*(1-p)/total + z*z/(4*total*total))/denominator;
  return [Math.max(0,center-margin),Math.min(1,center+margin)];
}
export interface MetricCounts {
  assigned: number; answered: number; skipped: number; timed_out: number; correct: number;
  interrupted: number; median_ms: number | null; p95_ms: number | null; timed_samples: number;
}
export function metricResult(counts: MetricCounts) {
  return {
    assignedTrials:counts.assigned,answeredTrials:counts.answered,skippedTrials:counts.skipped,
    timedOutTrials:counts.timed_out,correctTrials:counts.correct,interruptedTrials:counts.interrupted,
    primaryExactAccuracy:counts.assigned ? counts.correct/counts.assigned : null,
    wilson95: wilsonInterval(counts.correct,counts.assigned),
    secondaryAnsweredOnlyAccuracy:counts.answered ? counts.correct/counts.answered : null,
    medianSolveTimeMs:counts.median_ms,p95SolveTimeMs:counts.p95_ms,timedSampleCount:counts.timed_samples,
  };
}
