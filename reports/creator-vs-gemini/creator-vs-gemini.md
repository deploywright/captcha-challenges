# Creator vs Gemini Benchmark

Generated: 2026-10-02T19:11:59.005210+00:00

## Executive Summary

**Single-participant creator baseline; matched challenge comparison is primary.**

**Attribution:** creator confirmed in project conversation. Raw D1 stored cohort is **`main`**; analysis role is **`creator`**; attribution status is **`creator_confirmed`**. The session began before creator cohort support and was completed through the confirmed cross-cohort resume behavior. D1 history was not rewritten. Future main/all aggregate analytics exclude this exact session; raw exports retain the stored cohort and show analysis role separately. No human or Gemini benchmark was rerun and no production D1 writes were issued.

The production session contains **30/40 correct (75.00%)**, median solve time **7.683 s**, 3 skips **including** 1 timeout. All 40 assigned trials were finalized; skips/timeouts count as failures.

On those exact 40 IDs, Gemini achieved **21/40 (52.50%)**. Creator minus Gemini is **+22.50 percentage points**. This describes one participant on this subset, not human-versus-AI superiority.

## Matched 40-Challenge Comparison

| Stage | N matched | Creator | Gemini | Gap (pp) |
| --- | ---: | ---: | ---: | ---: |
| Level 1 | 6 | 3/6 (50.00%) | 4/6 (66.67%) | -16.67 |
| Level 2A | 6 | 5/6 (83.33%) | 5/6 (83.33%) | +0.00 |
| Level 2B | 6 | 5/6 (83.33%) | 6/6 (100.00%) | -16.67 |
| Level 3A | 18 | 16/18 (88.89%) | 6/18 (33.33%) | +55.56 |
| Level 3B | 4 | 1/4 (25.00%) | 0/4 (0.00%) | +25.00 |
| **Overall matched** | **40** | **30/40 (75.00%)** | **21/40 (52.50%)** | **+22.50** |

## Paired Outcome Matrix

| | Gemini correct | Gemini wrong |
| --- | ---: | ---: |
| Creator correct | 16 | 14 |
| Creator wrong / failure | 5 | 5 |

A+B+C+D = 40. Discordant pairs: B=14, C=5; N discordant=19. Exact two-sided McNemar p-value = **0.0635681152** (conditional binomial, doubled lower tail capped at one; no mid-p or chi-square approximation).

This p-value is exploratory for N=40 matched challenges from one participant. Shared participant/task dependencies and stratified selection limit inference; it does not establish a population-level human/AI difference. [Exact McNemar method](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html).

## Case Studies for Review

One case per represented stage in each discordant/both-wrong category; lexicographically smallest challenge ID within stage. All cases are also listed in outcome_categories. These are navigation examples, not evidence of general superiority.

| Outcome | Challenge ID | Stage | Public subtype | Difficulty | Resolution | Series |
| --- | --- | --- | --- | --- | ---: | --- |
| Where Creator Succeeded and Gemini Failed | lvl1_y82na0 | Level 1 | — | — | — | — |
| Where Creator Succeeded and Gemini Failed | lvl2a_02gwmw | Level 2A | — | — | — | — |
| Where Creator Succeeded and Gemini Failed | lvl3a_cables_1sbi07 | Level 3A | device-cables | medium | — | — |
| Where Creator Succeeded and Gemini Failed | lvl3b_xel0ut | Level 3B | — | — | 24 | series-02 |
| Where Gemini Succeeded and Creator Failed | lvl1_6j29rx | Level 1 | — | — | — | — |
| Where Gemini Succeeded and Creator Failed | lvl2a_ke53bn | Level 2A | — | — | — | — |
| Where Gemini Succeeded and Creator Failed | lvl2b_4oq84p | Level 2B | — | — | — | — |
| Where Gemini Succeeded and Creator Failed | lvl3a_conveyor_lyqxa9 | Level 3A | conveyor-routing | easy | — | — |
| Both Failed | lvl1_92m6az | Level 1 | — | — | — | — |
| Both Failed | lvl3a_pipe_oj4oct | Level 3A | pipe-flow | extreme | — | — |
| Both Failed | lvl3b_e1m46k | Level 3B | — | — | 16 | series-03 |

## Both Correct

N = 16. Every assigned case is listed; no cherry-picking or answer keys.

| Challenge ID | Stage | Variant | Public subtype | Difficulty | Resolution | Series |
| --- | --- | --- | --- | --- | ---: | --- |
| lvl2a_2sf1re | Level 2A | hard-street-grid | — | — | — | — |
| lvl2b_2mlh9o | Level 2B | checker-shadow | — | — | — | — |
| lvl3a_conveyor_v7s2yz | Level 3A | routing-puzzle | conveyor-routing | medium | — | — |
| lvl1_un41ic | Level 1 | street-grid | — | — | — | — |
| lvl3a_pipe_801x42 | Level 3A | routing-puzzle | pipe-flow | hard | — | — |
| lvl2a_eqvg41 | Level 2A | hard-street-grid | — | — | — | — |
| lvl3a_conveyor_ychwk1 | Level 3A | routing-puzzle | conveyor-routing | extreme | — | — |
| lvl2a_d8t3q3 | Level 2A | hard-street-grid | — | — | — | — |
| lvl2a_7ygcgq | Level 2A | hard-street-grid | — | — | — | — |
| lvl1_6nssnc | Level 1 | street-grid | — | — | — | — |
| lvl3a_pipe_zqe8jr | Level 3A | routing-puzzle | pipe-flow | medium | — | — |
| lvl2b_90aspy | Level 2B | checker-shadow | — | — | — | — |
| lvl2b_7c5cth | Level 2B | checker-shadow | — | — | — | — |
| lvl2b_m73rcm | Level 2B | checker-shadow | — | — | — | — |
| lvl2b_w8fc0h | Level 2B | checker-shadow | — | — | — | — |
| lvl3a_laser_345s9l | Level 3A | routing-puzzle | laser-maze | easy | — | — |

## Where Creator Succeeded and Gemini Failed

N = 14. Every assigned case is listed; no cherry-picking or answer keys.

| Challenge ID | Stage | Variant | Public subtype | Difficulty | Resolution | Series |
| --- | --- | --- | --- | --- | ---: | --- |
| lvl1_y82na0 | Level 1 | street-grid | — | — | — | — |
| lvl3a_cables_9k688m | Level 3A | routing-puzzle | device-cables | hard | — | — |
| lvl3a_laser_9xyskd | Level 3A | routing-puzzle | laser-maze | hard | — | — |
| lvl3b_xel0ut | Level 3B | degraded-vision | — | — | 24 | series-02 |
| lvl3a_pipe_35jwu5 | Level 3A | routing-puzzle | pipe-flow | story | — | — |
| lvl3a_cables_1sbi07 | Level 3A | routing-puzzle | device-cables | medium | — | — |
| lvl3a_laser_5lmdur | Level 3A | routing-puzzle | laser-maze | medium | — | — |
| lvl3a_laser_5m0pzq | Level 3A | routing-puzzle | laser-maze | extreme | — | — |
| lvl2a_02gwmw | Level 2A | hard-street-grid | — | — | — | — |
| lvl3a_conveyor_p0gcxa | Level 3A | routing-puzzle | conveyor-routing | story | — | — |
| lvl3a_cables_cu8tha | Level 3A | routing-puzzle | device-cables | story | — | — |
| lvl3a_laser_ykg18w | Level 3A | routing-puzzle | laser-maze | story | — | — |
| lvl3a_pipe_mwfaeh | Level 3A | routing-puzzle | pipe-flow | easy | — | — |
| lvl3a_cables_r4ut85 | Level 3A | routing-puzzle | device-cables | extreme | — | — |

## Where Gemini Succeeded and Creator Failed

N = 5. Every assigned case is listed; no cherry-picking or answer keys.

| Challenge ID | Stage | Variant | Public subtype | Difficulty | Resolution | Series |
| --- | --- | --- | --- | --- | ---: | --- |
| lvl3a_conveyor_lyqxa9 | Level 3A | routing-puzzle | conveyor-routing | easy | — | — |
| lvl1_6j29rx | Level 1 | street-grid | — | — | — | — |
| lvl2a_ke53bn | Level 2A | hard-street-grid | — | — | — | — |
| lvl1_gb5rr2 | Level 1 | street-grid | — | — | — | — |
| lvl2b_4oq84p | Level 2B | checker-shadow | — | — | — | — |

## Both Failed

N = 5. Every assigned case is listed; no cherry-picking or answer keys.

| Challenge ID | Stage | Variant | Public subtype | Difficulty | Resolution | Series |
| --- | --- | --- | --- | --- | ---: | --- |
| lvl3a_pipe_oj4oct | Level 3A | routing-puzzle | pipe-flow | extreme | — | — |
| lvl1_92m6az | Level 1 | street-grid | — | — | — | — |
| lvl3b_knpiig | Level 3B | degraded-vision | — | — | 8 | series-01 |
| lvl3b_sosvla | Level 3B | degraded-vision | — | — | 32 | series-04 |
| lvl3b_e1m46k | Level 3B | degraded-vision | — | — | 16 | series-03 |

## Creator Breakdown

Answered 37; secondary answered-only accuracy 81.08%. Skipped 3 includes timed-out 1, so timeout is not a fourth disjoint failure category. Interrupted trials: 1. p95 solve time: 47.391 s (nearest rank).

| Stage | Correct / N | Primary accuracy | Median solve time |
| --- | ---: | ---: | ---: |
| Level 1 | 3/6 | 50.00% | 7.683 s |
| Level 2A | 5/6 | 83.33% | 6.516 s |
| Level 2B | 5/6 | 83.33% | 6.995 s |
| Level 3A | 16/18 | 88.89% | 9.351 s |
| Level 3B | 1/4 | 25.00% | 4.266 s |

### Optical Illusions

Named subtype is absent from the stored rows and public catalog. The exact public task and ID identify each of the six cases; no subtype names or correct options are inferred.

| Challenge ID | Public task | Creator | Gemini | Creator status |
| --- | --- | --- | --- | --- |
| lvl2b_2mlh9o | Are squares A and B the same shade? | Correct | Correct | answered |
| lvl2b_90aspy | Are the two orange center circles the same size? | Correct | Correct | answered |
| lvl2b_7c5cth | Are the horizontal mortar lines dividing the rows parallel? | Correct | Correct | answered |
| lvl2b_4oq84p | Are horizontal bars A and B the same length? | Incorrect / failure | Correct | answered |
| lvl2b_m73rcm | Are squares A and B the same shade of grey? | Correct | Correct | answered |
| lvl2b_w8fc0h | Are horizontal lines A and B the same length? | Correct | Correct | answered |

### Routing by Subtype

| Bucket | N | Correct | Accuracy | Median solve time |
| --- | ---: | ---: | ---: | ---: |
| laser-maze | 5 | 5 | 100.00% | 10.609 s |
| conveyor-routing | 4 | 3 | 75.00% | 11.553 s |
| pipe-flow | 5 | 4 | 80.00% | 19.888 s |
| device-cables | 4 | 4 | 100.00% | 7.224 s |

### Routing by Difficulty

| Bucket | N | Correct | Accuracy | Median solve time |
| --- | ---: | ---: | ---: | ---: |
| easy | 3 | 2 | 66.67% | 5.577 s |
| medium | 4 | 4 | 100.00% | 7.417 s |
| story | 4 | 4 | 100.00% | 9.370 s |
| hard | 3 | 3 | 100.00% | 15.415 s |
| extreme | 4 | 3 | 75.00% | 15.006 s |

### Degraded Vision by Resolution

| Bucket | N | Correct | Accuracy | Median solve time |
| --- | ---: | ---: | ---: | ---: |
| 64 | 0 | 0 | — | — |
| 48 | 0 | 0 | — | — |
| 32 | 1 | 0 | 0.00% | 4.279 s |
| 24 | 1 | 1 | 100.00% | 5.790 s |
| 16 | 1 | 0 | 0.00% | 2.370 s |
| 12 | 0 | 0 | — | — |
| 8 | 1 | 0 | 0.00% | 4.253 s |

Only four distinct scene/resolution assignments were observed; N=0 denotes an unobserved bucket, not a failure. No continuous resolution threshold is inferred.

### Degraded Vision by Series

| Bucket | N | Correct | Accuracy | Median solve time |
| --- | ---: | ---: | ---: | ---: |
| series-01 | 1 | 0 | 0.00% | 4.253 s |
| series-02 | 1 | 1 | 100.00% | 5.790 s |
| series-03 | 1 | 0 | 0.00% | 2.370 s |
| series-04 | 1 | 0 | 0.00% | 4.279 s |

### Routing Subtype × Difficulty

Cells show correct / N. Empty strata remain visible.

| Subtype | easy | medium | story | hard | extreme |
| --- | ---: | ---: | ---: | ---: | ---: |
| laser-maze | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| conveyor-routing | 0/1 | 1/1 | 1/1 | — (N=0) | 1/1 |
| pipe-flow | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 |
| device-cables | — (N=0) | 1/1 | 1/1 | 1/1 | 1/1 |

## Full Gemini Baseline Context

Canonical model **gemini-3.5-flash-lite**, **zero-shot**, thinking **MINIMAL**. Full coverage is 134/134; this run was not rerun.

| Stage | Gemini full benchmark | Creator subset (different IDs/weights) |
| --- | ---: | ---: |
| Level 1 | 14/20 (70.00%) | 3/6 (50.00%) |
| Level 2A | 11/20 (55.00%) | 5/6 (83.33%) |
| Level 2B | 6/6 (100.00%) | 5/6 (83.33%) |
| Level 3A | 26/60 (43.33%) | 16/18 (88.89%) |
| Level 3B | 3/28 (10.71%) | 1/4 (25.00%) |
| Overall (unmatched populations) | 60/134 (44.78%) | 30/40 (75.00%) |

**These overall percentages come from different challenge populations and weighting schemes and should not be interpreted as a paired head-to-head score.** The matched 40-trial comparison above is the direct descriptive comparison.

| Stage | Creator weight | Gemini full weight |
| --- | ---: | ---: |
| Level 1 | 6/40 (15.00%) | 20/134 (14.93%) |
| Level 2A | 6/40 (15.00%) | 20/134 (14.93%) |
| Level 2B | 6/40 (15.00%) | 6/134 (4.48%) |
| Level 3A | 18/40 (45.00%) | 60/134 (44.78%) |
| Level 3B | 4/40 (10.00%) | 28/134 (20.90%) |

**Creator stage-standardized descriptive estimate:** 68.66%, computed as Σ (Gemini full stage N/134) × creator stage accuracy. It is not observed accuracy on 134 trials; observed creator accuracy remains 75.00%.

## Timing

| Process | Population | Median | p95 |
| --- | --- | ---: | ---: |
| Creator human solve time, visual readiness to final response | Assigned 40, presented trials including skips/timeouts | 7.683 s | 47.391 s |
| Gemini provider inference latency | Matched 40 | 2.412 s | 11.568 s |
| Gemini provider inference latency | Full 134 | 2.848 s | 14.017 s |

Client human timing is primary; server elapsed is an audit interval including different network/resume semantics. Provider inference may include retries. These are different processes, so no equivalent faster/slower claim is made.

Quality audit: trial 1 (`lvl3a_conveyor_lyqxa9`) was timed_out, interrupted=true, with capped client time 120.000 s and server elapsed 5217.423 s. The Boolean flag cannot identify the cause of the long interval. It remains a primary failure and is not dropped. Session wall time was 5708.103 s; this is not summed active solve time.

## Verification and Provenance

Session: `73fac77a-7985-4755-a26d-16ea9046541f`; stored cohort `main`; analysis role `creator`; attribution status `creator_confirmed`; protocol `human-v1`. Read-only production D1 retrieval at 2026-10-02T17:40:03.609Z. Counters agree with raw rows; positions 1..40 and IDs are unique, quotas are 6/6/6/18/4, and degraded series are distinct. Canonical raw correctness totals reproduce the JSON aggregate exactly and all 40 IDs match. UI values are cross-checks only.

The public JSON contains hashes/source paths and outcomes, never submitted answers, predictions, secret cookies, token hashes, participant IDs, or ground-truth keys. The ignored local audit contains only the requested submitted-response fields and source timestamps. Raw Gemini files and canonical reports remain unchanged.

MINIMAL is recorded in the frozen canonical aggregate; the raw run configs do not separately persist a thinking-level field.

## Methodological Limitations

1. Historical routing anomaly: the creator-confirmed human-v1 session was stored as main because the session began before creator cohort support. The Creator URL can resume an active cookie-bound session without checking cohort. Raw D1 cohort remains main and is never rewritten; analysis_role is creator under the explicit attribution record.
2. Exactly one creator; this is a single-participant creator baseline, not representative human performance.
3. The creator saw 40 of 134 challenges, selected with fixed stratified quotas rather than a simple random full-population sample.
4. Creator stage estimates have small N; Level 2B has six total challenges and is completely shared, while Level 3B samples only four distinct scenes/resolutions.
5. No continuous degraded-resolution threshold can be inferred from four trials.
6. The creator knows the project and may have more context than a naive participant; prior exposure is not measured by this session.
7. Human solve time and Gemini provider inference latency measure different processes; this is not an equivalent speed comparison.
8. The strongest direct descriptive comparison uses the exact same 40 IDs; full-population overall percentages use different challenge populations and weighting schemes.
9. The stage-standardized creator score is a descriptive estimate from within-stage subsets, not observed performance on all 134 challenges.
10. McNemar's exact conditional binomial p-value is exploratory and assumes exchangeable independent discordant pairs under its null; shared participant/task dependencies and stratified selection limit inferential interpretation.
11. No population-level humans-versus-AI superiority claim follows from one participant or these 40 matched challenges.
12. Named illusion subtype is absent from D1 and the public catalog; optical cases use exact public instructions and IDs, with no guessed names.
13. Main and all-cohort aggregate human-sample analytics exclude the exact annotated creator-role session; authenticated raw exports preserve cohort=main and provide analysis_role=creator separately.

## Reproduction

Run the local generator against the ignored read-only production audit snapshot and the committed creator attribution record. It validates the exact session ID, user confirmation, stored cohort, protocol, completion, outcomes, median display rounding, quotas, and unique challenge IDs. Main/all aggregate analytics apply the same annotation as an exclusion; raw exports preserve the stored cohort and include analysis_role separately. All report statistics derive from the structured result.
