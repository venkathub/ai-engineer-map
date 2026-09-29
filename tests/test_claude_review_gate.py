import importlib.util
import json
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

    def test_evidence_lists_reject_blank_entries(self):
        for field in ("tests_reviewed", "residual_risks"):
            payload = json.loads(review_payload())
            payload[field] = ["   "]
            with self.assertRaises(review_gate.ReviewError):
                review_gate.normalize_review(json.dumps(payload))

    def test_reviewed_sha_requires_full_lowercase_commit_id(self):
        valid = "b" * 40
        self.assertEqual(review_gate.validate_reviewed_sha(valid), valid)
        with self.assertRaises(review_gate.ReviewError):
            review_gate.validate_reviewed_sha("not-a-commit")

    def test_report_neutralizes_mentions_and_comment_markers(self):
        payload = json.loads(review_payload())
        payload["summary"] = "Notify @team <!-- hidden -->"
        review = review_gate.normalize_review(json.dumps(payload))
        report = review_gate.render_review(review, "abc123")
        self.assertNotIn("@team", report)
        self.assertIn("@\u200bteam", report)
        self.assertNotIn("<!-- hidden -->", report)
        self.assertNotIn("<!--", report.split("\n", 1)[1])
        self.assertNotIn("-->", report.split("\n", 1)[1])

    def test_subscription_success_requires_structured_output(self):
        with self.assertRaises(review_gate.ReviewError) as raised:
            review_gate.validate_subscription_result(True, "success", "   ")
        self.assertIn("without a structured_output value", str(raised.exception))

    def test_report_renders_model_text_as_inert_markdown(self):
        payload = json.loads(review_payload())
        payload["summary"] = (
            "# heading\n[click](https://evil.test) ![pixel](https://evil.test/p.png) "
            "```spoof``` <b>raw</b> www.evil.test"
        )
        report = review_gate.render_review(review_gate.normalize_review(json.dumps(payload)), "abc123")
        self.assertNotIn("https://", report)
        self.assertNotIn("[click]", report)
        self.assertNotIn("![pixel]", report)
        self.assertNotIn("```spoof```", report)
        self.assertNotIn("<b>", report)
        self.assertNotIn("www.evil.test", report)

    def test_report_names_authentication_route(self):
        review = review_gate.normalize_review(review_payload())
        report = review_gate.render_review(review, "abc123", "Claude subscription OAuth")
        self.assertIn("Review route: `Claude subscription OAuth`", report)

if __name__ == "__main__":
    unittest.main()
