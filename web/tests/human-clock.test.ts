import { describe, expect, it } from "vitest";
import { TrialClock } from "../lib/human-benchmark/clock";
import { TRIAL_TIMEOUT_MS } from "../lib/human-benchmark/protocol";
import { wilsonInterval } from "../lib/human-benchmark/metrics";
describe("human timing", () => {
  it("starts only when assets are ready and never starts twice", () => {
    let now = 0; const clock = new TrialClock(() => now,() => now);
    now = 5000; expect(clock.elapsed()).toBe(0); expect(clock.started).toBe(false);
    clock.start(); now = 5300; clock.start(); now = 5700;
    expect(clock.elapsed()).toBe(700);
  });
  it.each(["submit","skip","timeout"])("stops once on %s and retains time across retry delivery", action => {
    let now = 0; const clock = new TrialClock(() => now,() => now); clock.start();
    now = action === "timeout" ? TRIAL_TIMEOUT_MS : 4321;
    const stopped = clock.stop(); now += 6000;
    expect(clock.stop()).toBe(stopped); expect(clock.elapsed()).toBe(stopped);
    clock.start(); expect(clock.elapsed()).toBe(stopped);
  });
  it("restores interruption/refresh elapsed time and immutable pending timing", () => {
    const running = new TrialClock(() => 0,() => 15000,{startedAtUnixMs:10000,stoppedMs:null});
    running.start(); expect(running.elapsed()).toBe(5000);
    const stopped = new TrialClock(() => 0,() => 20000,{startedAtUnixMs:10000,stoppedMs:3000});
    stopped.start(); expect(stopped.stop()).toBe(3000);
  });
  it("caps late timeouts at the fixed protocol limit", () => {
    const clock = new TrialClock(() => 0,() => 999999,{startedAtUnixMs:0,stoppedMs:null});
    clock.start(); expect(clock.stop()).toBe(TRIAL_TIMEOUT_MS);
  });
  it("restores a zero-time skip before assets were ready without starting a new timer", () => {
    const clock = new TrialClock(() => 1000,() => 1000,{startedAtUnixMs:null,stoppedMs:0});
    clock.start();expect(clock.stopped).toBe(true);expect(clock.started).toBe(false);expect(clock.elapsed()).toBe(0);
  });
  it("computes Wilson intervals without inventing a sample", () => {
    expect(wilsonInterval(0,0)).toBeNull();
    const bounds = wilsonInterval(14,20)!;
    expect(bounds[0]).toBeCloseTo(.4810,3); expect(bounds[1]).toBeCloseTo(.8545,3);
    expect(wilsonInterval(0,10)![0]).toBe(0);
    expect(wilsonInterval(10,10)![1]).toBeCloseTo(1,14);
  });
});
