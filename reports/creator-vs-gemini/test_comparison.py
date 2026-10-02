"""Analysis checks; reads the ignored D1 snapshot, never mutates production."""
import copy
import unittest

from scipy.stats import binomtest
from generate_comparison import ROOT, load_gemini, markdown, mcnemar_exact, quantiles, read_json, validate_creator, build_report


class AnalysisTests(unittest.TestCase):
    def test_exact_test_agrees_with_scipy_and_handles_edges(self):
        for b, c in [(14, 5), (5, 14), (0, 8), (8, 0), (5, 5), (0, 1)]:
            self.assertAlmostEqual(mcnemar_exact(b, c), binomtest(b, b+c, .5, alternative="two-sided").pvalue, places=14)
        self.assertEqual(mcnemar_exact(0, 0), 1)

    def test_quantiles_are_median_and_nearest_rank(self):
        self.assertEqual(quantiles(list(range(1, 41))), (20.5, 38))
        self.assertEqual(quantiles([]), (None, None))

    def test_actual_raw_rows_agree_with_counters(self):
        audit = read_json(ROOT / ".tmp/creator-comparison-production-audit.json")
        metric = validate_creator(audit)
        self.assertEqual(metric["answered"] + metric["skipped"], metric["total"])
        self.assertEqual(metric["correct"] + metric["incorrect_or_failure"], metric["total"])
        self.assertLessEqual(metric["timed_out"], metric["skipped"])
        self.assertEqual(metric["median_solve_time_ms"], 7683)  # UI cross-check, not metric source.

    def test_invalid_snapshot_is_rejected(self):
        audit = read_json(ROOT / ".tmp/creator-comparison-production-audit.json")
        for mutation in ["counter", "duplicate", "timeout_correct", "unfinalized"]:
            bad = copy.deepcopy(audit)
            if mutation == "counter": bad["session"]["skipped_count"] += 1
            if mutation == "duplicate": bad["trials"][1]["challenge_id"] = bad["trials"][0]["challenge_id"]
            if mutation == "timeout_correct": bad["trials"][0]["correct"] = 1
            if mutation == "unfinalized": bad["trials"][0]["status"] = "presented"
            with self.assertRaises(ValueError): validate_creator(bad)

    def test_arbitrary_main_session_cannot_use_confirmed_attribution(self):
        audit = read_json(ROOT / ".tmp/creator-comparison-production-audit.json")
        audit["session"]["session_id"] = "00000000-0000-4000-8000-000000000001"
        path = ROOT / ".tmp/creator-comparison-untrusted-session.json"
        path.write_text(__import__("json").dumps(audit), encoding="utf-8")
        try:
            with self.assertRaisesRegex(ValueError, "Attribution session ID mismatch"):
                build_report(path)
        finally:
            path.unlink(missing_ok=True)

    def test_exact_creator_confirmed_historical_main_is_attributed_without_relabeling(self):
        report = build_report(ROOT / ".tmp/creator-comparison-production-audit.json")
        self.assertEqual(report["report_status"], "attributed")
        self.assertEqual(report["creator"]["cohort"], "main")
        self.assertEqual(report["creator"]["stored_cohort"], "main")
        self.assertEqual(report["creator"]["analysis_role"], "creator")
        self.assertEqual(report["creator"]["attribution_status"], "creator_confirmed")
        self.assertEqual(report["creator"]["identity_confirmation"], "creator_confirmed_by_user")
        self.assertEqual(report["creator"]["correct"], 30)
        self.assertEqual(report["creator"]["median_solve_time_ms"], 7683)
        self.assertEqual(report["provenance"]["creator_attribution"]["status"], "creator_confirmed")
        self.assertIn("stored cohort is **`main`**", __import__("generate_comparison").markdown(report))

    def test_attribution_fails_when_any_confirmed_session_invariant_changes(self):
        baseline = read_json(ROOT / ".tmp/creator-comparison-production-audit.json")
        mutations = ["protocol", "status", "stored_cohort", "assigned", "correct", "skipped", "timeout", "median", "quota", "duplicate_id", "creator_exists"]
        for field in mutations:
            bad = copy.deepcopy(baseline)
            if field == "protocol": bad["session"]["protocol_version"] = "human-v2"
            elif field == "status": bad["session"]["status"] = "abandoned"
            elif field == "stored_cohort": bad["session"]["cohort"] = "creator"
            elif field == "assigned": bad["session"]["assigned_count"] = 39
            elif field == "correct": bad["trials"][5]["correct"] = 1 - bad["trials"][5]["correct"]
            elif field == "skipped": bad["trials"][0]["skipped"] = 0
            elif field == "timeout": bad["trials"][0]["timed_out"] = 0
            elif field == "median":
                for row in bad["trials"]: row["client_solve_time_ms"] += 20_000
            elif field == "quota": bad["trials"][0]["variant"] = "street-grid"
            elif field == "duplicate_id": bad["trials"][1]["challenge_id"] = bad["trials"][0]["challenge_id"]
            elif field == "creator_exists": bad["completed_creator_count"] = 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                from generate_comparison import validate_confirmed_attribution, read_json as load_json
                validate_confirmed_attribution(bad,load_json(ROOT / "reports/creator-vs-gemini/creator-attribution.json"))

    def test_attribution_record_cannot_be_bypassed_for_an_unrelated_main_session(self):
        audit = read_json(ROOT / ".tmp/creator-comparison-production-audit.json")
        audit["session"]["session_id"] = "00000000-0000-4000-8000-000000000001"
        path = ROOT / ".tmp/creator-comparison-untrusted-session.json"
        path.write_text(__import__("json").dumps(audit), encoding="utf-8")
        try:
            with self.assertRaisesRegex(ValueError, "Attribution session ID mismatch"):
                build_report(path, allow_unattributed_draft=True)
        finally:
            path.unlink(missing_ok=True)

    def test_attributed_report_preserves_public_case_partition(self):
        report = build_report(ROOT / ".tmp/creator-comparison-production-audit.json")
        groups = report["matched"]["outcome_categories"]
        ids = [row["challenge_id"] for group in groups.values() for row in group]
        self.assertEqual(len(ids), 40)
        self.assertEqual(len(set(ids)), 40)
        public_fields = {"challenge_id", "stage", "variant", "subtype", "difficulty", "resolution", "series_id"}
        for category, cases in report["matched"]["case_studies"].items():
            self.assertEqual({row["stage"] for row in cases}, {row["stage"] for row in groups[category]})
            for row in cases:
                self.assertIn(row, groups[category])
                self.assertEqual(set(row), public_fields)

    def test_report_states_attribution_cause_exclusion_and_full_comparison_context(self):
        report = build_report(ROOT / ".tmp/creator-comparison-production-audit.json")
        rendered = markdown(report)
        for required in [
            "stored cohort is **`main`**", "analysis role is **`creator`**", "creator confirmed in project conversation",
            "cross-cohort resume behavior", "main/all aggregate analytics exclude this exact session",
            "No human or Gemini benchmark was rerun", "30/40 correct (75.00%)", "21/40 (52.50%)",
            "0.0635681152", "16 | 14", "5 | 5", "Full coverage is 134/134", "Full Gemini Baseline Context",
        ]:
            with self.subTest(required=required): self.assertIn(required, rendered)
        self.assertEqual(report["gemini"]["full_population_metrics"]["correct"], 60)
        self.assertEqual(report["gemini"]["full_population_metrics"]["total"], 134)
        self.assertEqual(report["creator"]["stored_cohort"], "main")
        self.assertEqual(report["creator"]["analysis_role"], "creator")
        self.assertIsNone(report["matched"]["challenge_outcomes"][0].get("answer"))

    def test_canonical_raw_runs_reproduce_full_json(self):
        canonical, rows, _ = load_gemini(ROOT / "AI-Solver/reports/gemini-zero-shot-baseline.json")
        self.assertEqual(len(rows), canonical["total_challenges"])
        self.assertEqual(sum(row["correct"] for row in rows.values()), canonical["correct_challenges"])


if __name__ == "__main__":
    unittest.main()
