import importlib.util
import sys
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
            "success", "success", "true", "APPROVED", "skipped", "", ""
        )
        self.assertEqual(result, (True, "APPROVED"))

    def test_selects_api_after_subscription_failure(self):
        result = decision.select_result(
            "failure", "skipped", "", "", "success", "false", "CHANGES_REQUESTED"
        )
        self.assertEqual(result, (False, "CHANGES_REQUESTED"))

    def test_rejects_missing_api_fallback_output(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result("failure", "skipped", "", "", "failure", "", "")

    def test_rejects_inconsistent_approval_and_verdict(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result(
                "success", "success", "true", "CHANGES_REQUESTED", "skipped", "", ""
            )

    def test_rejects_both_routes_running(self):
        with self.assertRaises(decision.ReviewError):
            decision.select_result(
                "success", "success", "true", "APPROVED", "success", "false", "ERROR"
            )


if __name__ == "__main__":
    unittest.main()
