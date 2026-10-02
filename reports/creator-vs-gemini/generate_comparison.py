"""Read-only comparison of a D1 audit snapshot and frozen canonical Gemini runs.

No network calls, database mutations, benchmark runs, or answer-key publication.
The production snapshot remains in ignored .tmp; published records omit answers.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
STAGES = {
    "street-grid": "Level 1", "hard-street-grid": "Level 2A",
    "checker-shadow": "Level 2B", "routing-puzzle": "Level 3A",
    "degraded-vision": "Level 3B",
}
QUOTAS = {"street-grid": 6, "hard-street-grid": 6, "checker-shadow": 6,
          "routing-puzzle": 18, "degraded-vision": 4}
SUBTYPES = ["laser-maze", "conveyor-routing", "pipe-flow", "device-cables"]
DIFFICULTIES = ["easy", "medium", "story", "hard", "extreme"]
RESOLUTIONS = [64, 48, 32, 24, 16, 12, 8]
CATEGORIES = ["both_correct", "creator_only_correct", "gemini_only_correct", "both_wrong"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def provenance(path):
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def quantiles(values):
    if not values:
        return None, None
    ordered = sorted(values)
    return statistics.median(ordered), ordered[math.ceil(.95 * len(ordered)) - 1]


def creator_metric(rows):
    timing = [r["client_solve_time_ms"] for r in rows if r["presented_at"] is not None]
    median, p95 = quantiles(timing)
    correct = sum(r["correct"] for r in rows)
    answered = sum(r["status"] == "answered" for r in rows)
    return {"total": len(rows), "correct": correct, "incorrect_or_failure": len(rows)-correct,
            "accuracy": correct / len(rows) if rows else None,
            "answered": answered, "skipped": sum(r["skipped"] for r in rows),
            "timed_out": sum(r["timed_out"] for r in rows),
            "interrupted": sum(r["interrupted"] for r in rows),
            "median_solve_time_ms": median, "p95_solve_time_ms": p95,
            "timed_sample_count": len(timing),
            "secondary_answered_only_accuracy": correct / answered if answered else None}


def mcnemar_exact(b, c):
    """Two-sided exact conditional binomial test, not chi-square or mid-p."""
    require(isinstance(b, int) and isinstance(c, int) and min(b, c) >= 0, "Invalid discordant counts")
    n = b + c
    if not n:
        return 1.0
    tail = Fraction(sum(math.comb(n, k) for k in range(min(b, c)+1)), 2**n)
    return float(min(Fraction(1), 2*tail))


def validate_creator(audit):
    session, rows = audit["session"], audit["trials"]
    require(session["protocol_version"] == "human-v1" and session["status"] == "completed", "Session is not completed human-v1")
    require(session["cohort"] in ("creator", "main"), "Unexpected candidate cohort")
    require(len(rows) == session["assigned_count"] == 40, "Not exactly 40 assigned rows")
    require(sorted(r["position"] for r in rows) == list(range(1, 41)), "Positions are not exactly 1..40")
    require(len({r["challenge_id"] for r in rows}) == 40, "Repeated challenge IDs")
    require(Counter(r["variant"] for r in rows) == Counter(QUOTAS), "Assignment quota mismatch")
    for row in rows:
        require(row["status"] in ("answered", "skipped", "timed_out") and row["answered_at"] is not None, "Unfinalized trial")
        require(row["correct"] in (0, 1) and row["skipped"] in (0, 1) and row["timed_out"] in (0, 1), "Invalid outcome flags")
        require(not row["timed_out"] or row["skipped"], "Timeout missing skip flag")
        require(not row["skipped"] or row["correct"] == 0, "Skipped trial marked correct")
        require((row["status"] == "answered") == (not row["skipped"]), "Status/skip mismatch")
        require((row["status"] == "timed_out") == bool(row["timed_out"]), "Status/timeout mismatch")
        require(isinstance(row["client_solve_time_ms"], int) and 0 <= row["client_solve_time_ms"] <= 120000, "Invalid primary timing")
        require(row["server_elapsed_ms"] >= 0 and row["interrupted"] in (0, 1), "Invalid audit timing/quality flag")
    metric = creator_metric(rows)
    require(metric["answered"] == session["answered_count"], "D1 answered counter mismatch")
    require(metric["skipped"] == session["skipped_count"], "D1 skipped counter mismatch")
    require(metric["timed_out"] == session["timeout_count"], "D1 timeout counter mismatch")
    require(metric["answered"] + metric["skipped"] == 40, "Finalized counter mismatch")
    degraded = [r for r in rows if r["variant"] == "degraded-vision"]
    require(len({r["series_id"] for r in degraded}) == 4 and all(r["series_id"] for r in degraded), "Repeated degraded scene")
    return metric


def load_gemini(canonical_path):
    canonical = read_json(canonical_path)
    require(canonical["mode"] == "zero-shot" and canonical["thinking_level"] == "MINIMAL", "Not the canonical MINIMAL zero-shot report")
    records, sources = {}, [provenance(canonical_path)]
    for label, directory in canonical["run_artifacts"].items():
        stage = label.split(" (")[0]
        folder = ROOT / "AI-Solver" / directory
        prediction_path = folder / "predictions.jsonl"
        require(prediction_path.exists(), f"Canonical raw predictions unavailable: {prediction_path}; matched results cannot be invented")
        run = read_json(folder / "run.json")
        require(run["status"] == "completed" and run["model"] == canonical["model"], "Wrong/incomplete canonical run")
        require(not run["config"]["dry_run"], "Dry-run results are not acceptable")
        rows = [json.loads(line) for line in prediction_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        expected = canonical["metrics"]["by_stage"][stage]
        require(len(rows) == expected["challenge_count"], f"Raw count differs from canonical {stage}")
        require(all(type(row["correct"]) is bool and row["status"] == "evaluated" and row["model"] == canonical["model"] for row in rows), "Invalid/unevaluated Gemini outcome")
        require(sum(row["correct"] for row in rows) == expected["correct_count"], f"Raw correctness differs from canonical {stage}")
        for row in rows:
            require(STAGES[row["variant"]] == stage, "Raw stage/variant mismatch")
            require(row["challenge_id"] not in records, "Duplicate Gemini challenge ID")
            records[row["challenge_id"]] = row
        for filename in ("predictions.jsonl", "run.json", "summary.json"):
            sources.append(provenance(folder / filename))
    require(len(records) == canonical["total_challenges"] == canonical["evaluated_challenges"], "Canonical coverage mismatch")
    require(sum(row["correct"] for row in records.values()) == canonical["correct_challenges"], "Canonical total correctness mismatch")
    require(math.isclose(canonical["micro_accuracy"], canonical["correct_challenges"] / canonical["total_challenges"]), "Canonical accuracy mismatch")
    return canonical, records, sources


def grouping(rows, field, buckets):
    return {str(bucket): creator_metric([r for r in rows if r.get(field) == bucket]) for bucket in buckets}


def case_studies(categories):
    """Select one public case per represented stage, with deterministic ID ordering."""
    return {
        category: [min((row for row in categories[category] if row["stage"] == stage),
                       key=lambda row: row["challenge_id"])
                   for stage in STAGES.values()
                   if any(row["stage"] == stage for row in categories[category])]
        for category in CATEGORIES[1:]
    }


def build_report(audit_path, allow_unattributed_draft=False):
    audit = read_json(audit_path)
    session, rows = audit["session"], audit["trials"]
    overall = validate_creator(audit)
    if session["cohort"] != "creator":
        require(allow_unattributed_draft, "Cannot attribute a main-cohort session as the Creator Baseline; a completed creator-cohort record is required")
    pending = session["cohort"] != "creator"
    canonical, gemini, sources = load_gemini(ROOT / "AI-Solver/reports/gemini-zero-shot-baseline.json")
    catalog_path = ROOT / "web/public/challenges/catalog.json"
    catalog = {r["id"]: r for r in read_json(catalog_path)}
    missing = [r["challenge_id"] for r in rows if r["challenge_id"] not in gemini or r["challenge_id"] not in catalog]
    require(not missing, f"Incomplete matching; no trials may be dropped: {missing}")
    outcomes, categories = [], {name: [] for name in CATEGORIES}
    for row in rows:
        entry, g = catalog[row["challenge_id"]], gemini[row["challenge_id"]]
        require(entry["variant"] == row["variant"] == g["variant"], "Mismatched stimulus variant")
        for field, key in [("subtype", "subtype"), ("difficulty", "difficulty"), ("resolution", "resolution"), ("series_id", "seriesId")]:
            require(row.get(field) == entry.get(key), f"D1/public metadata differs for {row['challenge_id']} {field}")
        public = {"challenge_id": row["challenge_id"], "stage": STAGES[row["variant"]],
                  **{key: row[key] for key in ("variant", "subtype", "difficulty", "resolution", "series_id")}}
        c_correct, g_correct = bool(row["correct"]), g["correct"]
        category = CATEGORIES[0 if c_correct and g_correct else 1 if c_correct else 2 if g_correct else 3]
        categories[category].append(public)
        outcomes.append({**public, "position": row["position"], "creator_correct": c_correct,
                         "gemini_correct": g_correct, "category": category,
                         "creator_status": row["status"], "creator_solve_time_ms": row["client_solve_time_ms"],
                         "skipped": bool(row["skipped"]), "timed_out": bool(row["timed_out"]),
                         "interrupted": bool(row["interrupted"]), "gemini_inference_time_ms": g["inference_time_ms"]})
    by_stage = {stage: creator_metric([r for r in rows if r["variant"] == variant]) for variant, stage in STAGES.items()}
    matched_stage = {}
    for stage, metric in by_stage.items():
        assigned = [r for r in outcomes if r["stage"] == stage]
        g_correct = sum(r["gemini_correct"] for r in assigned)
        matched_stage[stage] = {"total": metric["total"], "creator_correct": metric["correct"],
                               "creator_accuracy": metric["accuracy"], "gemini_correct": g_correct,
                               "gemini_accuracy": g_correct / len(assigned),
                               "accuracy_gap_pp": 100*(metric["correct"] - g_correct)/len(assigned)}
    routing = [r for r in rows if r["variant"] == "routing-puzzle"]
    degraded = [r for r in rows if r["variant"] == "degraded-vision"]
    g_times = [r["inference_time_ms"] for r in gemini.values() if r["challenge_id"] in {t["challenge_id"] for t in rows}]
    g_median, g_p95 = quantiles(g_times)
    counts = {name: len(values) for name, values in categories.items()}
    g_correct = sum(r["gemini_correct"] for r in outcomes)
    require(sum(counts.values()) == len(outcomes) == 40, "Paired matrix total mismatch")
    require(counts["both_correct"] + counts["creator_only_correct"] == overall["correct"], "Creator paired marginal mismatch")
    require(counts["both_correct"] + counts["gemini_only_correct"] == g_correct, "Gemini paired marginal mismatch")
    full = {"total": canonical["total_challenges"], "correct": canonical["correct_challenges"],
            "incorrect": canonical["incorrect_challenges"], "accuracy": canonical["micro_accuracy"],
            "by_stage": canonical["metrics"]["by_stage"],
            "median_inference_time_ms": canonical["metrics"]["median_inference_time_ms"],
            "p95_inference_time_ms": canonical["metrics"]["p95_inference_time_ms"]}
    standardized = sum(Fraction(by_stage[stage]["correct"], by_stage[stage]["total"]) *
                       Fraction(metric["challenge_count"], full["total"]) for stage, metric in full["by_stage"].items())
    limitations = [
        "Exactly one creator; this is a single-participant creator baseline, not representative human performance.",
        "The creator saw 40 of 134 challenges, selected with fixed stratified quotas rather than a simple random full-population sample.",
        "Creator stage estimates have small N; Level 2B has six total challenges and is completely shared, while Level 3B samples only four distinct scenes/resolutions.",
        "No continuous degraded-resolution threshold can be inferred from four trials.",
        "The creator knows the project and may have more context than a naive participant; prior exposure is not measured by this session.",
        "Human solve time and Gemini provider inference latency measure different processes; this is not an equivalent speed comparison.",
        "The strongest direct descriptive comparison uses the exact same 40 IDs; full-population overall percentages use different challenge populations and weighting schemes.",
        "The stage-standardized creator score is a descriptive estimate from within-stage subsets, not observed performance on all 134 challenges.",
        "McNemar's exact conditional binomial p-value is exploratory and assumes exchangeable independent discordant pairs under its null; shared participant/task dependencies and stratified selection limit inferential interpretation.",
        "No population-level humans-versus-AI superiority claim follows from one participant or these 40 matched challenges.",
        "Named illusion subtype is absent from D1 and the public catalog; optical cases use exact public instructions and IDs, with no guessed names.",
    ]
    if session["cohort"] != "creator":
        limitations.insert(0, "Storage anomaly: there are zero completed creator-cohort sessions. This diagnostic session is stored as main and is explicitly excluded from Creator Baseline attribution. A correct completed creator record must be identified; no D1 row was relabeled or changed.")
    if pending:
        limitations = [note.replace("Exactly one creator; this is a single-participant creator baseline", "Exactly one participant; this is an unattributed candidate session")
                      .replace("The creator knows the project and may have more context than a naive participant; prior exposure is not measured by this session.",
                               "The main session is not attributed to the creator. Project familiarity is a limitation of a future creator baseline, not an established fact about this anonymous participant.")
                      .replace("Creator stage", "Candidate stage").replace("The creator saw", "The participant saw")
                      .replace("creator score", "candidate score")
                      for note in limitations]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_status": "creator_session_missing" if pending else "attributed",
        "creator": {"protocol_version": session["protocol_version"], "cohort": session["cohort"],
                    "session_id": session["session_id"], "analysis_label": "unattributed main-cohort diagnostic; excluded from creator baseline" if pending else "single-participant creator baseline",
                    "identity_confirmation": "not_attributed" if pending else "creator_cohort_record",
                    "session_wall_time_ms": session["completed_at"] - session["started_at"],
                    **overall, "observed_accuracy": overall["accuracy"], "by_stage": by_stage,
                    "by_subtype": grouping(routing, "subtype", SUBTYPES),
                    "by_difficulty": grouping(routing, "difficulty", DIFFICULTIES),
                    "subtype_by_difficulty": {s: grouping([r for r in routing if r["subtype"] == s], "difficulty", DIFFICULTIES) for s in SUBTYPES},
                    "by_resolution": grouping(degraded, "resolution", RESOLUTIONS),
                    "by_series": grouping(degraded, "series_id", sorted({r["series_id"] for r in degraded})),
                    "optical_illusions": [{"challenge_id": r["challenge_id"], "subtype": catalog[r["challenge_id"]].get("subtype"),
                                           "public_instruction": catalog[r["challenge_id"]]["instruction"], "creator_correct": bool(r["correct"]),
                                           "gemini_correct": gemini[r["challenge_id"]]["correct"], "status": r["status"],
                                           "solve_time_ms": r["client_solve_time_ms"]} for r in rows if r["variant"] == "checker-shadow"]},
        "gemini": {"model": canonical["model"], "mode": canonical["mode"], "thinking_level": canonical["thinking_level"],
                   "full_population_metrics": full, "matched_median_inference_time_ms": g_median, "matched_p95_inference_time_ms": g_p95},
        "matched": {"total": 40, "creator_correct": overall["correct"], "gemini_correct": g_correct,
                    "creator_accuracy": overall["accuracy"], "gemini_accuracy": g_correct/40,
                    "accuracy_gap_pp": 100*(overall["correct"]-g_correct)/40, **counts,
                    "mcnemar_exact_p_value": mcnemar_exact(counts["creator_only_correct"], counts["gemini_only_correct"]),
                    "mcnemar_discordant_pairs": counts["creator_only_correct"] + counts["gemini_only_correct"],
                    "by_stage": matched_stage, "challenge_outcomes": outcomes, "outcome_categories": categories,
                    "case_studies": case_studies(categories),
                    "case_study_selection": "One case per represented stage in each discordant/both-wrong category; lexicographically smallest challenge ID within stage. All cases are also listed in outcome_categories. These are navigation examples, not evidence of general superiority."},
        "creator_stage_standardized_accuracy": float(standardized),
        "stage_weights": {stage: {"creator_total": by_stage[stage]["total"], "creator_weight": by_stage[stage]["total"]/40,
                                   "gemini_full_total": metric["challenge_count"], "gemini_full_weight": metric["challenge_count"]/full["total"]}
                          for stage, metric in full["by_stage"].items()},
        "verification": {"completed_creator_cohort_sessions": audit["completed_creator_count"], "assigned": 40, "finalized": 40,
                         "unique_positions": 40, "unique_challenge_ids": 40, "positions": "1..40", "quotas": QUOTAS,
                         "distinct_degraded_series": 4, "canonical_predictions": len(gemini), "matched_ids": 40,
                         "session_counters_match_raw_trials": True, "all_inputs_read_only": True,
                         "long_server_elapsed_trials": [{"position": r["position"], "challenge_id": r["challenge_id"],
                                                         "status": r["status"], "client_solve_time_ms": r["client_solve_time_ms"],
                                                         "server_elapsed_ms": r["server_elapsed_ms"], "interrupted": bool(r["interrupted"])}
                                                        for r in rows if r["server_elapsed_ms"] > 120000],
                         "ui_cross_check": {"expected_correct": 30, "correct_matches": overall["correct"] == 30,
                                            "median_rounds_to_7_7_seconds": round(overall["median_solve_time_ms"]/1000, 1) == 7.7,
                                            "skips_match": overall["skipped"] == 3, "timeouts_match": overall["timed_out"] == 1}},
        "provenance": {"production_database": audit["database_name"], "production_database_id": audit["database_id"],
                       "retrieved_at": audit["retrieved_at"], "session_created_at": session["created_at"],
                       "session_completed_at": session["completed_at"], "sources": sources + [provenance(catalog_path), provenance(audit_path)],
                       "thinking_provenance": "MINIMAL is recorded in the frozen canonical aggregate; the raw run configs do not separately persist a thinking-level field."},
        "methodology_notes": limitations,
    }
    return report


def pct(value):
    return "—" if value is None else f"{value*100:.2f}%"


def seconds(value):
    return "—" if value is None else f"{value/1000:.3f} s"


def outcome(value):
    return "Correct" if value else "Incorrect / failure"


def markdown(report):
    c, g, m = report["creator"], report["gemini"], report["matched"]
    full = g["full_population_metrics"]
    lines = ["# Creator vs Gemini Benchmark", "", f"Generated: {report['generated_at']}", "",
             "## Executive Summary", "", "**Single-participant creator baseline; matched challenge comparison is primary.**", ""]
    if c["cohort"] != "creator":
        identity_note = "This main-cohort record is excluded from Creator Baseline attribution by the user's instruction. These results describe only an anonymous diagnostic session; a correct completed creator-cohort record is still required."
        lines += [f"**Storage anomaly:** D1 contains zero completed `creator` sessions. Session `{c['session_id']}` is stored in **`{c['cohort']}`**, started before creator-cohort deployment. {identity_note} No session or trial was moved, edited, or recreated.", ""]
    lines += [f"The production session contains **{c['correct']}/{c['total']} correct ({pct(c['observed_accuracy'])})**, median solve time **{seconds(c['median_solve_time_ms'])}**, {c['skipped']} skips **including** {c['timed_out']} timeout. All {c['total']} assigned trials were finalized; skips/timeouts count as failures.", "",
              f"On those exact {m['total']} IDs, Gemini achieved **{m['gemini_correct']}/{m['total']} ({pct(m['gemini_accuracy'])})**. Creator minus Gemini is **{m['accuracy_gap_pp']:+.2f} percentage points**. This describes one participant on this subset, not human-versus-AI superiority.", "",
              "## Matched 40-Challenge Comparison", "", "| Stage | N matched | Creator | Gemini | Gap (pp) |", "| --- | ---: | ---: | ---: | ---: |"]
    for stage, metric in m["by_stage"].items():
        lines.append(f"| {stage} | {metric['total']} | {metric['creator_correct']}/{metric['total']} ({pct(metric['creator_accuracy'])}) | {metric['gemini_correct']}/{metric['total']} ({pct(metric['gemini_accuracy'])}) | {metric['accuracy_gap_pp']:+.2f} |")
    lines += [f"| **Overall matched** | **{m['total']}** | **{m['creator_correct']}/{m['total']} ({pct(m['creator_accuracy'])})** | **{m['gemini_correct']}/{m['total']} ({pct(m['gemini_accuracy'])})** | **{m['accuracy_gap_pp']:+.2f}** |", "",
              "## Paired Outcome Matrix", "", "| | Gemini correct | Gemini wrong |", "| --- | ---: | ---: |",
              f"| Creator correct | {m['both_correct']} | {m['creator_only_correct']} |",
              f"| Creator wrong / failure | {m['gemini_only_correct']} | {m['both_wrong']} |", "",
              f"A+B+C+D = {sum(m[key] for key in CATEGORIES)}. Discordant pairs: B={m['creator_only_correct']}, C={m['gemini_only_correct']}; N discordant={m['mcnemar_discordant_pairs']}. Exact two-sided McNemar p-value = **{m['mcnemar_exact_p_value']:.10f}** (conditional binomial, doubled lower tail capped at one; no mid-p or chi-square approximation).", "",
              "This p-value is exploratory for N=40 matched challenges from one participant. Shared participant/task dependencies and stratified selection limit inference; it does not establish a population-level human/AI difference. [Exact McNemar method](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html).", ""]
    titles = ["Both Correct", "Where Creator Succeeded and Gemini Failed", "Where Gemini Succeeded and Creator Failed", "Both Failed"]
    lines += ["## Case Studies for Review", "", m["case_study_selection"], "",
              "| Outcome | Challenge ID | Stage | Public subtype | Difficulty | Resolution | Series |",
              "| --- | --- | --- | --- | --- | ---: | --- |"]
    for category, title in zip(CATEGORIES[1:], titles[1:]):
        for row in m["case_studies"][category]:
            fields = [row[key] for key in ["challenge_id", "stage", "subtype", "difficulty", "resolution", "series_id"]]
            lines.append("| " + title + " | " + " | ".join(str(value) if value is not None else "—" for value in fields) + " |")
    lines += [""]
    for category, title in zip(CATEGORIES, titles):
        lines += [f"## {title}", "", f"N = {m[category]}. Every assigned case is listed; no cherry-picking or answer keys.", "",
                  "| Challenge ID | Stage | Variant | Public subtype | Difficulty | Resolution | Series |",
                  "| --- | --- | --- | --- | --- | ---: | --- |"]
        for row in m["outcome_categories"][category]:
            lines.append("| " + " | ".join(str(row[key]) if row[key] is not None else "—" for key in ["challenge_id","stage","variant","subtype","difficulty","resolution","series_id"]) + " |")
        lines += [""]
    lines += ["## Creator Breakdown", "", f"Answered {c['answered']}; secondary answered-only accuracy {pct(c['secondary_answered_only_accuracy'])}. Skipped {c['skipped']} includes timed-out {c['timed_out']}, so timeout is not a fourth disjoint failure category. Interrupted trials: {c['interrupted']}. p95 solve time: {seconds(c['p95_solve_time_ms'])} (nearest rank).", "",
              "| Stage | Correct / N | Primary accuracy | Median solve time |", "| --- | ---: | ---: | ---: |"]
    for stage, metric in c["by_stage"].items():
        lines.append(f"| {stage} | {metric['correct']}/{metric['total']} | {pct(metric['accuracy'])} | {seconds(metric['median_solve_time_ms'])} |")
    lines += ["", "### Optical Illusions", "", "Named subtype is absent from the stored rows and public catalog. The exact public task and ID identify each of the six cases; no subtype names or correct options are inferred.", "",
              "| Challenge ID | Public task | Creator | Gemini | Creator status |", "| --- | --- | --- | --- | --- |"]
    for row in c["optical_illusions"]:
        lines.append(f"| {row['challenge_id']} | {row['public_instruction']} | {outcome(row['creator_correct'])} | {outcome(row['gemini_correct'])} | {row['status']} |")
    for key, title in [("by_subtype","Routing by Subtype"),("by_difficulty","Routing by Difficulty"),("by_resolution","Degraded Vision by Resolution"),("by_series","Degraded Vision by Series")]:
        lines += ["", f"### {title}", "", "| Bucket | N | Correct | Accuracy | Median solve time |", "| --- | ---: | ---: | ---: | ---: |"]
        for bucket, metric in c[key].items():
            lines.append(f"| {bucket} | {metric['total']} | {metric['correct']} | {pct(metric['accuracy'])} | {seconds(metric['median_solve_time_ms'])} |")
        if key == "by_resolution":
            lines += ["", "Only four distinct scene/resolution assignments were observed; N=0 denotes an unobserved bucket, not a failure. No continuous resolution threshold is inferred."]
    lines += ["", "### Routing Subtype × Difficulty", "", "Cells show correct / N. Empty strata remain visible.", "",
              "| Subtype | " + " | ".join(DIFFICULTIES) + " |", "| --- | " + " | ".join(["---:"]*len(DIFFICULTIES)) + " |"]
    for subtype, cells in c["subtype_by_difficulty"].items():
        lines.append("| " + subtype + " | " + " | ".join(f"{cells[d]['correct']}/{cells[d]['total']}" if cells[d]["total"] else "— (N=0)" for d in DIFFICULTIES) + " |")
    lines += ["", "## Full Gemini Baseline Context", "", f"Canonical model **{g['model']}**, **{g['mode']}**, thinking **{g['thinking_level']}**. Full coverage is {full['total']}/{full['total']}; this run was not rerun.", "",
              "| Stage | Gemini full benchmark | Creator subset (different IDs/weights) |", "| --- | ---: | ---: |"]
    for stage, metric in full["by_stage"].items():
        cm = c["by_stage"][stage]
        lines.append(f"| {stage} | {metric['correct_count']}/{metric['challenge_count']} ({pct(metric['exact_challenge_accuracy'])}) | {cm['correct']}/{cm['total']} ({pct(cm['accuracy'])}) |")
    lines += [f"| Overall (unmatched populations) | {full['correct']}/{full['total']} ({pct(full['accuracy'])}) | {c['correct']}/{c['total']} ({pct(c['observed_accuracy'])}) |", "",
              "**These overall percentages come from different challenge populations and weighting schemes and should not be interpreted as a paired head-to-head score.** The matched 40-trial comparison above is the direct descriptive comparison.", "",
              "| Stage | Creator weight | Gemini full weight |", "| --- | ---: | ---: |"]
    for stage, weight in report["stage_weights"].items():
        lines.append(f"| {stage} | {weight['creator_total']}/{c['total']} ({pct(weight['creator_weight'])}) | {weight['gemini_full_total']}/{full['total']} ({pct(weight['gemini_full_weight'])}) |")
    lines += ["", f"**Creator stage-standardized descriptive estimate:** {pct(report['creator_stage_standardized_accuracy'])}, computed as Σ (Gemini full stage N/{full['total']}) × creator stage accuracy. It is not observed accuracy on 134 trials; observed creator accuracy remains {pct(c['observed_accuracy'])}.", "",
              "## Timing", "", "| Process | Population | Median | p95 |", "| --- | --- | ---: | ---: |",
              f"| Creator human solve time, visual readiness to final response | Assigned 40, presented trials including skips/timeouts | {seconds(c['median_solve_time_ms'])} | {seconds(c['p95_solve_time_ms'])} |",
              f"| Gemini provider inference latency | Matched 40 | {seconds(g['matched_median_inference_time_ms'])} | {seconds(g['matched_p95_inference_time_ms'])} |",
              f"| Gemini provider inference latency | Full 134 | {seconds(full['median_inference_time_ms'])} | {seconds(full['p95_inference_time_ms'])} |", "",
              "Client human timing is primary; server elapsed is an audit interval including different network/resume semantics. Provider inference may include retries. These are different processes, so no equivalent faster/slower claim is made.", "",
              "## Verification and Provenance", "", f"Session: `{c['session_id']}`; stored cohort `{c['cohort']}`; protocol `{c['protocol_version']}`. Read-only production D1 retrieval at {report['provenance']['retrieved_at']}. Counters agree with raw rows; positions 1..40 and IDs are unique, quotas are 6/6/6/18/4, and degraded series are distinct. Canonical raw correctness totals reproduce the JSON aggregate exactly and all 40 IDs match. UI values are cross-checks only.", "",
              "The public JSON contains hashes/source paths and outcomes, never submitted answers, predictions, secret cookies, token hashes, participant IDs, or ground-truth keys. The ignored local audit contains only the requested submitted-response fields and source timestamps. Raw Gemini files and canonical reports remain unchanged.", "",
              report["provenance"]["thinking_provenance"], "", "## Methodological Limitations", ""]
    for row in report["verification"]["long_server_elapsed_trials"]:
        lines[lines.index("## Verification and Provenance"):lines.index("## Verification and Provenance")] = [
            f"Quality audit: trial {row['position']} (`{row['challenge_id']}`) was {row['status']}, interrupted={str(row['interrupted']).lower()}, with capped client time {seconds(row['client_solve_time_ms'])} and server elapsed {seconds(row['server_elapsed_ms'])}. The Boolean flag cannot identify the cause of the long interval. It remains a primary failure and is not dropped. Session wall time was {seconds(c['session_wall_time_ms'])}; this is not summed active solve time.", ""]
    lines += [f"{i}. {note}" for i, note in enumerate(report["methodology_notes"], 1)]
    lines += ["", "## Reproduction", "", "Run the local generator against the ignored read-only production audit snapshot. Only a completed creator-cohort record may produce an attributed Creator Baseline; a main-cohort snapshot is restricted to an anonymous diagnostic draft. All statistics and Markdown numbers derive from the same structured result.", ""]
    rendered = "\n".join(lines)
    if c["cohort"] != "creator":
        rendered = rendered.replace("Creator", "Candidate").replace("creator baseline", "unattributed candidate session")
        rendered = rendered.replace("creator stage accuracy", "candidate stage accuracy").replace("observed creator accuracy", "observed candidate accuracy")
        rendered = rendered.replace("# Candidate vs Gemini Benchmark", "# Anonymous main session vs Gemini — diagnostic only", 1)
        rendered = rendered.replace("## Executive Summary", "This draft compares an anonymous main session. It is excluded from Creator Baseline attribution.\n\n## Executive Summary", 1)
    return rendered


def plot(report, folder):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.size": 10, "svg.fonttype": "none"})
    matched = report["matched"]
    metrics = list(matched["by_stage"].values()) + [matched]
    labels = [f"{stage.replace('Level ', 'L')}\nN={m['total']}" for stage, m in matched["by_stage"].items()] + [f"Overall\nN={matched['total']}"]
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.3), gridspec_kw={"width_ratios": [1.65, 1]})
    positions = np.arange(len(metrics))
    role = "Candidate" if report["creator"]["cohort"] != "creator" else "Creator"
    for offset, field, color, label in [(-.19, "creator_accuracy", "#2563eb", f"{role} (one participant)"),(.19, "gemini_accuracy", "#f59e0b", "Gemini zero-shot")]:
        bars = axes[0].bar(positions+offset, [100*m[field] for m in metrics], width=.36, color=color, label=label)
        for bar, metric in zip(bars, metrics):
            key = "creator_correct" if field == "creator_accuracy" else "gemini_correct"
            axes[0].text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5, f"{metric[key]}/{metric['total']}", ha="center", fontsize=8)
    axes[0].set_xticks(positions, labels)
    axes[0].set_ylim(0, 119)
    axes[0].set_ylabel("Exact accuracy (%)")
    axes[0].set_title("Same exact assigned challenge IDs")
    axes[0].legend(loc="upper left", bbox_to_anchor=(0, 1.14), frameon=False, ncol=2, fontsize=8)
    axes[0].spines[["top", "right"]].set_visible(False)
    values = np.array([[matched["both_correct"], matched["creator_only_correct"]], [matched["gemini_only_correct"], matched["both_wrong"]]])
    axes[1].imshow(values, cmap="Blues", vmin=0, vmax=max(1, values.max()))
    axes[1].set_xticks([0, 1], ["Gemini correct", "Gemini wrong"])
    axes[1].set_yticks([0, 1], [f"{role} correct", f"{role} failure"])
    for i in range(2):
        for j in range(2):
            axes[1].text(j, i, str(values[i, j]), ha="center", va="center", fontsize=24, color="white" if values[i, j] > values.max()/2 else "#172554")
    axes[1].set_title(f"Paired outcomes, N={matched['total']}\nExact McNemar p={matched['mcnemar_exact_p_value']:.5f}")
    figure.suptitle(f"{'Anonymous main session (excluded from Creator Baseline)' if role == 'Candidate' else 'Single-participant creator baseline'} vs Gemini: matched 40 challenges", fontsize=12)
    figure.text(.5, .02, "Descriptive selected-subset comparison. No population-level human/AI inference.", ha="center", fontsize=9)
    figure.tight_layout(rect=(0, .05, 1, .93))
    stem = "candidate-vs-gemini.pending" if role == "Candidate" else "creator-vs-gemini"
    figure.savefig(folder / f"{stem}.png", dpi=180)
    figure.savefig(folder / f"{stem}.svg")
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=ROOT / ".tmp/creator-comparison-production-audit.json")
    parser.add_argument("--unattributed-draft", action="store_true", help="Create an anonymous main-session diagnostic; never attribute it as the Creator Baseline")
    args = parser.parse_args()
    report = build_report(args.audit.resolve(), args.unattributed_draft)
    folder = Path(__file__).resolve().parent
    stem = "candidate-vs-gemini.pending" if report["creator"]["cohort"] != "creator" else "creator-vs-gemini"
    output = folder / f"{stem}.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Render Markdown from the serialized deliverable rather than a second calculation.
    (folder / f"{stem}.md").write_text(markdown(read_json(output)), encoding="utf-8")
    plot(read_json(output), folder)
    print(json.dumps({"creator": report["creator"]["correct"], "gemini_matched": report["matched"]["gemini_correct"],
                      "matched_total": report["matched"]["total"], "output": str(folder)}))


if __name__ == "__main__":
    main()
