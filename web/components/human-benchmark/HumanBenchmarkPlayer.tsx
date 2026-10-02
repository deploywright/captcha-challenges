"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ImageGridChallenge } from "../challenges/ImageGridChallenge";
import { BinaryChoiceChallenge } from "../challenges/BinaryChoiceChallenge";
import { RoutingPuzzleChallenge } from "../challenges/RoutingPuzzleChallenge";
import { TrialClock } from "@/lib/human-benchmark/clock";
import type { ClockSnapshot } from "@/lib/human-benchmark/clock";
import { TRIAL_TIMEOUT_MS } from "@/lib/human-benchmark/protocol";
import type { SessionView, TrialSubmission } from "@/lib/human-benchmark/types";

function storageRead<T>(key: string): T | undefined {
  try { const value = sessionStorage.getItem(key); return value ? JSON.parse(value) as T : undefined; } catch { return undefined; }
}
function storageWrite(key: string, value: unknown) { try { sessionStorage.setItem(key,JSON.stringify(value)); } catch {} }
async function post(path: string, body: unknown) {
  const response = await fetch(`/api/human-benchmark/${path}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  if (!response.ok) {
    const error = await response.json() as {error?:string};
    throw new Error(error.error ?? "Connection unavailable. Your response has not been confirmed.");
  }
  const confirmation = await response.json() as {accepted?:boolean;ready?:boolean;stopped?:boolean};
  const confirmed = path === "trial" ? confirmation.accepted : path === "present" ? confirmation.ready : confirmation.stopped;
  if (confirmed !== true) throw new Error("The server did not confirm this request. Keep the saved response and try again.");
  return confirmation;
}

function HumanTrial({trial,onAccepted}: {trial:NonNullable<SessionView["trial"]>;onAccepted:() => Promise<void>}) {
  const key = `hb:${trial.trialId}`;
  const clock = useRef(new TrialClock(undefined,undefined,storageRead<ClockSnapshot>(`${key}:clock`)));
  const interrupted = useRef(Boolean(storageRead<boolean>(`${key}:interrupted`)) || trial.presented);
  const pending = useRef<TrialSubmission | undefined>(storageRead<TrialSubmission>(`${key}:pending`));
  const submitting = useRef(false);
  const presenting = useRef(false);
  const [ready,setReady] = useState(false);
  const [started,setStarted] = useState(false);
  const [frozen,setFrozen] = useState(Boolean(pending.current));
  const [busy,setBusy] = useState(false);
  const [elapsed,setElapsed] = useState(pending.current?.solveTimeMs ?? 0);
  const [error,setError] = useState("");
  const [assetError,setAssetError] = useState(false);
  const submitRef = useRef<(action:TrialSubmission["action"],answer?:number[]|string) => Promise<void>>(async () => {});

  const assetsReady = useCallback(() => {
    clock.current.start(trial.elapsedMs);
    storageWrite(`${key}:clock`,clock.current.snapshot());
    setStarted(true);
    if (presenting.current || pending.current) return;
    presenting.current = true;
    post("present",{trialId:trial.trialId}).then(() => {setReady(true);setError("");}).catch(err => {
      presenting.current = false; setError(err instanceof Error ? err.message : "Unable to confirm stimulus readiness.");
    });
  },[key,trial.elapsedMs,trial.trialId]);

  async function deliver() {
    if (submitting.current || !pending.current) return;
    submitting.current = true; setBusy(true); setError("");
    try {
      await post("trial",pending.current);
      try { for (const suffix of ["clock","pending","interrupted"]) sessionStorage.removeItem(`${key}:${suffix}`); } catch {}
      await onAccepted();
    } catch(err) { setError(err instanceof Error ? err.message : "Unable to confirm your response. Send the same response again."); }
    finally { submitting.current = false; setBusy(false); }
  }
  submitRef.current = async (action,answer) => {
    if (pending.current || (action === "answer" && !ready)) return;
    const solveTimeMs = clock.current.stop();
    pending.current = {trialId:trial.trialId,action,...(action === "answer" ? {answer} : {}),solveTimeMs,interrupted:interrupted.current};
    storageWrite(`${key}:pending`,pending.current);
    storageWrite(`${key}:clock`,clock.current.snapshot());
    setElapsed(solveTimeMs); setFrozen(true);
    await deliver();
  };
  useEffect(() => {
    const hidden = () => { if (document.hidden && !clock.current.stopped) { interrupted.current = true;storageWrite(`${key}:interrupted`,true); } };
    document.addEventListener("visibilitychange",hidden);
    return () => document.removeEventListener("visibilitychange",hidden);
  },[key]);
  useEffect(() => {
    if (!started || frozen) return;
    const timer = window.setInterval(() => {
      const value = clock.current.elapsed(); setElapsed(value);
      if (value >= TRIAL_TIMEOUT_MS) void submitRef.current("timeout");
    },200);
    return () => clearInterval(timer);
  },[started,frozen]);

  const rendererProps = {challenge:trial.challenge,benchmarkMode:true,isSubmitting:busy,disabled:!ready || frozen,onAssetsReady:assetsReady};
  return <section className="space-y-5" aria-label={`Question ${trial.position}`}>
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-300"><span>{started ? `${Math.ceil(Math.max(0,TRIAL_TIMEOUT_MS-elapsed)/1000)} seconds remaining` : "Loading visual stimulus…"}</span><span>One final response · No feedback</span></div>
    <div onErrorCapture={() => setAssetError(true)} className="hb-stimulus">
      {trial.challenge.variant === "routing-puzzle" ? <RoutingPuzzleChallenge {...rendererProps} onSubmit={answer => void submitRef.current("answer",answer)} /> : trial.challenge.type === "single-choice" ? <BinaryChoiceChallenge {...rendererProps} onSubmit={answer => void submitRef.current("answer",answer)} /> : <ImageGridChallenge {...rendererProps} onSubmit={answer => void submitRef.current("answer",answer)} />}
    </div>
    {assetError && <p className="hb-error" role="alert">An image could not load. <button className="hb-link" onClick={() => location.reload()}>Reload the visual stimulus</button>, or skip this question.</p>}
    <div className="flex flex-wrap justify-between gap-3"><button type="button" className="hb-secondary" disabled={frozen || busy} onClick={() => void submitRef.current("skip")}>Skip question</button>
      {frozen && !busy && <button type="button" className="hb-button" onClick={() => void deliver()}>Send saved response</button>}
      {!ready && started && !frozen && !busy && <button type="button" className="hb-secondary" onClick={assetsReady}>Confirm connection</button>}</div>
    {busy && <p role="status" className="hb-notice">{pending.current?.action === "timeout" ? "Time is up. Saving this trial…" : "Saving your response…"}</p>}
    {error && <p role="alert" className="hb-error">{error}</p>}
  </section>;
}

export function HumanBenchmarkPlayer() {
  const [view,setView] = useState<SessionView | null>(null);
  const [error,setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const load = useCallback(async () => {
    const response = await fetch("/api/human-benchmark/session",{cache:"no-store"});
    if (!response.ok) throw new Error("Your session could not be loaded. Return to the benchmark page or retry loading.");
    setView(await response.json() as SessionView); setError("");
  },[]);
  useEffect(() => {void load().catch(err => setError(String(err.message)));},[load]);
  useEffect(() => {heading.current?.focus();},[view?.trial?.trialId,view?.status]);
  async function stop() {
    if (!window.confirm(`Stop this session? Your accepted responses remain saved.${view?.cohort === "main" || view?.cohort === "creator" ? ` This ${view.cohort} session cannot be restarted.` : ""}`)) return;
    try {await post("stop",{});await load();} catch(err) {setError(err instanceof Error ? err.message : "Unable to stop.");}
  }
  return <main className="hb-shell hb-run">
    <header className="space-y-4 mb-7"><div className="flex flex-wrap items-center justify-between gap-3"><p className="hb-eyebrow">Human Benchmark{view?.cohort && view.cohort !== "main" ? ` · ${view.cohort}` : ""}</p><Link href="/human-benchmark" className="hb-link">Leave for now</Link></div>
      <h1 ref={heading} tabIndex={-1} className="text-2xl sm:text-3xl font-semibold outline-none" aria-live="polite">{view?.status === "completed" ? view.cohort === "creator" ? "Creator baseline complete" : "Benchmark complete" : view?.status === "abandoned" ? "Session stopped" : view?.trial ? `Question ${view.trial.position} of 40` : "Preparing your benchmark…"}</h1>
      {view && <progress className="w-full h-2 accent-blue-500" aria-label="Benchmark progress" value={view.progress.completed} max={40} />}
    </header>
    {view?.status === "active" && view.trial && <HumanTrial key={view.trial.trialId} trial={view.trial} onAccepted={load} />}
    {view?.status === "completed" && view.summary && <section className="hb-card space-y-6"><p className="text-lg">Thank you for taking part. Your anonymous responses are saved.</p><dl className="grid grid-cols-2 gap-6">
      <div><dt className="text-slate-400">Overall accuracy</dt><dd className="text-3xl font-semibold">{(view.summary.accuracy*100).toFixed(1)}%</dd></div>
      <div><dt className="text-slate-400">Median solve time</dt><dd className="text-3xl font-semibold">{view.summary.medianSolveTimeMs === null ? "—" : `${(view.summary.medianSolveTimeMs/1000).toFixed(1)} s`}</dd></div>
      <div><dt className="text-slate-400">Skipped (including timeouts)</dt><dd className="text-2xl">{view.summary.skipped}</dd></div><div><dt className="text-slate-400">Timed out</dt><dd className="text-2xl">{view.summary.timedOut}</dd></div>
    </dl><p className="text-sm text-slate-400">All 40 assigned questions contribute to your accuracy. Skips and timeouts count as unsuccessful responses.</p><Link className="hb-link" href="/">Return to challenges</Link></section>}
    {view?.status === "abandoned" && <div className="hb-card space-y-4"><p>Your accepted responses remain saved. You may leave this page.</p><Link href="/" className="hb-link">Return to challenges</Link></div>}
    {view?.status === "active" && <button className="hb-link mt-8 text-slate-400" type="button" onClick={() => void stop()}>Stop session permanently</button>}
    {error && <div className="hb-error space-y-3" role="alert"><p>{error}</p><button className="hb-secondary" onClick={() => void load().catch(err => setError(String(err.message)))}>Reload saved session</button><Link href="/human-benchmark" className="hb-link block">Benchmark landing page</Link></div>}
  </main>;
}
