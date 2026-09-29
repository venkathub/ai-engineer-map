import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "claude_review_gate.py"
SPEC = importlib.util.spec_from_file_location("claude_review_gate", MODULE_PATH)
review_gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(review_gate)


def review_payload(verdict="APPROVED", findings=None):
    return json.dumps(
        {
            "verdict": verdict,
            "summary": "The current diff satisfies the repository contract.",
            "findings": findings or [],
            "tests_reviewed": ["./run.sh check"],
            "residual_risks": [],
        }
    )


class ClaudeReviewGateTests(unittest.TestCase):
    def test_approved_review_has_no_findings(self):
        review = review_gate.normalize_review(review_payload())
        self.assertEqual(review["verdict"], "APPROVED")
        self.assertEqual(review["findings"], [])

    def test_changes_requested_requires_a_finding(self):
        with self.assertRaises(review_gate.ReviewError):
            review_gate.normalize_review(review_payload("CHANGES_REQUESTED"))

    def test_approved_review_rejects_findings(self):
        finding = {
            "id": "src-1",
            "severity": "high",
            "path": "src/example.py",
            "line": 7,
            "title": "Broken behavior",
            "details": "The changed path fails.",
            "recommendation": "Add the missing guard.",
        }
        with self.assertRaises(review_gate.ReviewError):
            review_gate.normalize_review(review_payload("APPROVED", [finding]))

    def test_report_neutralizes_mentions_and_comment_markers(self):
        payload = json.loads(review_payload())
        payload["summary"] = "Notify @team <!-- hidden -->"
        review = review_gate.normalize_review(json.dumps(payload))
        report = review_gate.render_review(review, "abc123")
        self.assertNotIn("@team", report)
        self.assertIn("@\u200bteam", report)
        self.assertNotIn("<!-- hidden -->", report)

    def test_failure_diagnostic_exposes_codes_but_not_provider_message(self):
        record = {
            "type": "result",
            "is_error": True,
            "api_error_status": 401,
            "error": "authentication_failed",
            "terminal_reason": "api_error",
            "result": "Failed with secret provider details that must stay private",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "execution.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            diagnostic = review_gate.safe_failure_diagnostic(str(path))
        self.assertIn("HTTP 401", diagnostic)
        self.assertIn("authentication_failed", diagnostic)
        self.assertNotIn("secret provider details", diagnostic)


if __name__ == "__main__":
    unittest.main()
