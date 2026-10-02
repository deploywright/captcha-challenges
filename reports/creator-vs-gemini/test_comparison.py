"""Analysis checks; reads the ignored D1 snapshot, never mutates production."""
import copy
import unittest

from scipy.stats import binomtest
from generate_comparison import ROOT, load_gemini, mcnemar_exact, quantiles, read_json, validate_creator, build_report


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

    def test_noncreator_identity_cannot_be_guessed(self):
        with self.assertRaisesRegex(ValueError, "identity must be confirmed"):
            build_report(ROOT / ".tmp/creator-comparison-production-audit.json")

    def test_pending_report_preserves_identity_and_public_case_partition(self):
        report = build_report(ROOT / ".tmp/creator-comparison-production-audit.json", allow_unattributed_draft=True)
        self.assertEqual(report["report_status"], "attribution_pending")
        self.assertEqual(report["creator"]["cohort"], "main")
        self.assertEqual(report["creator"]["identity_confirmation"], "pending")
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

    def test_canonical_raw_runs_reproduce_full_json(self):
        canonical, rows, _ = load_gemini(ROOT / "AI-Solver/reports/gemini-zero-shot-baseline.json")
        self.assertEqual(len(rows), canonical["total_challenges"])
        self.assertEqual(sum(row["correct"] for row in rows.values()), canonical["correct_challenges"])


if __name__ == "__main__":
    unittest.main()
