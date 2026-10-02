"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { Cohort } from "@/lib/human-benchmark/protocol";
import type { SessionView } from "@/lib/human-benchmark/types";

export function HumanBenchmarkLanding({cohort}: {cohort: Exclude<Cohort,"smoke">}) {
  const [consent,setConsent] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [existing,setExisting] = useState<SessionView | null>(null);
  const router = useRouter();
  useEffect(() => { fetch("/api/human-benchmark/session",{cache:"no-store"}).then(async r => {
    if (r.ok) setExisting(await r.json() as SessionView);
  }).catch(() => {}); },[]);
  async function start() {
    if (!consent || busy) return;
    setBusy(true); setError("");
    const viewportBucket = window.innerWidth < 640 ? "small" : window.innerWidth < 1024 ? "medium" : "large";
    const deviceClass = viewportBucket === "small" ? "mobile" : viewportBucket === "medium" ? "tablet" : "desktop";
    try {
      const response = await fetch("/api/human-benchmark/session",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({consent:true,cohort,deviceClass,viewportBucket})});
      const body = await response.json() as {error?:string};
      if (!response.ok) throw new Error(body.error ?? "Unable to start. Please try again.");
      router.push("/human-benchmark/run");
    } catch(err) { setError(err instanceof Error ? err.message : "Connection unavailable. Please try again."); setBusy(false); }
  }
  const completed = existing?.cohort === cohort && existing.status === "completed";
  return <main className="hb-shell">
    <Link href="/" className="hb-link">← CAPTCHA Challenges</Link>
    <div className="hb-card mt-8 space-y-7">
      <div><p className="hb-eyebrow">Anonymous participation{cohort === "pilot" ? " · Pilot session" : ""}</p>
        <h1 className="hb-title">How do you see the challenge?</h1>
        <p className="text-lg text-slate-300 mt-4">Take part in the Human Benchmark: 40 visual CAPTCHA challenges, one response at a time.</p></div>
      <ul className="space-y-3 text-slate-300 list-disc pl-5">
        <li>Your responses and solve times will be recorded anonymously. No name, email, account, or identifying profile is required.</li>
        <li>You will receive no correctness feedback during the benchmark. Your aggregate personal summary appears only at the end.</li>
        <li>Work on your own. Do not use external tools, AI assistants, screenshots, search, or other people.</li>
        <li>Each question allows up to two minutes after its images load. Skips and timeouts count as unsuccessful responses.</li>
        <li>You may stop at any time, or leave and resume later in this browser. Accepted responses are final.</li>
      </ul>
      {cohort === "pilot" && <p className="hb-notice">This is a pilot session. Its data is kept separate from the main benchmark sample.</p>}
      {completed ? <div className="space-y-4"><p>You already completed this benchmark.</p><Link href="/human-benchmark/run" className="hb-button">View your summary</Link></div> : existing?.status === "active" ? <div className="space-y-4"><p>Your session is saved at question {existing.progress.completed + 1} of 40.</p><Link href="/human-benchmark/run" className="hb-button">Resume benchmark</Link></div> : <form onSubmit={e => {e.preventDefault(); void start();}} className="space-y-5">
        <label className="flex items-start gap-3 cursor-pointer text-slate-200"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-1 w-5 h-5 shrink-0 accent-blue-500" />
          <span>I understand that my anonymous responses and timing data will be used for this benchmark.</span></label>
        <button className="hb-button" disabled={!consent || busy} type="submit">{busy ? "Preparing your session…" : "Start Human Benchmark"}</button>
      </form>}
      {error && <p role="alert" className="hb-error">{error}</p>}
      <p className="text-sm text-slate-400 border-t border-slate-700 pt-5">This is an anonymous project benchmark, not a representative population study. Participation is voluntary.</p>
    </div>
  </main>;
}
