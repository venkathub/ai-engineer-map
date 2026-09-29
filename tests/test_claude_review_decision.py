import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "claude_review_decision.py"
SPEC = importlib.util.spec_from_file_location("claude_review_decision", MODULE_PATH)
decision = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(decision)


class ClaudeReviewDecisionTests(unittest.TestCase):
    def test_selects_successful_subscription_review(self):
        result = decision.select_result(
            "success", "success", "true", "APPROVED", "0", "skipped", "", "", ""
        )
        self.assertEqual(result, (True, "APPROVED", 0))

    def test_selects_api_after_subscription_failure(self):
        result = decision.select_result(
            "failure", "skipped", "", "", "", "success", "false", "CHANGES_REQUESTED", "2"
        )
        self.assertEqual(result, (False, "CHANGES_REQUESTED", 2))

    def test_rejects_missing_api_fallback_output(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result("failure", "skipped", "", "", "", "failure", "", "", "")

    def test_rejects_inconsistent_approval_and_verdict(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result(
                "success", "success", "true", "CHANGES_REQUESTED", "1", "skipped", "", "", ""
            )

    def test_rejects_both_routes_running(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result(
                "success", "success", "true", "APPROVED", "0", "success", "false", "ERROR", "0"
            )

    def test_rejects_unset_api_outcome_after_subscription_success(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result("success", "success", "true", "APPROVED", "0", "", "", "", "")

    def test_rejects_subscription_gate_success_after_subscription_failure(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result(
                "failure", "success", "true", "APPROVED", "0", "success", "false", "ERROR", "0"
            )

    def test_rejects_finding_count_inconsistent_with_verdict(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result(
                "failure", "skipped", "", "", "", "success", "false", "CHANGES_REQUESTED", "0"
            )

    def test_failure_report_is_written_when_route_report_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "review.md"
            written = decision.write_failure_report(report, "route failed", "abc123")
            self.assertTrue(written)
            self.assertIn("REVIEW UNAVAILABLE", report.read_text(encoding="utf-8"))

    def test_failure_report_returns_false_for_unwritable_path(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "missing" / "review.md"
            self.assertFalse(decision.write_failure_report(report, "route failed", "abc123"))


if __name__ == "__main__":
    unittest.main()
