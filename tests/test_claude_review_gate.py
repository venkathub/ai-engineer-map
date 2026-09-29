import importlib.util
import json
import tempfile
import unittest
import os
import sys
from pathlib import Path
from unittest import mock


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

    def test_approved_review_rejects_blocking_findings(self):
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

    def test_approved_review_allows_low_notes(self):
        finding = {
            "id": "src-low",
            "severity": "low",
            "path": "src/example.py",
            "line": 7,
            "title": "Optional cleanup",
            "details": "The name is less direct than it could be.",
            "recommendation": "Consider a clearer name.",
        }
        review = review_gate.normalize_review(review_payload("APPROVED", [finding]))
        self.assertEqual(review_gate.blocking_finding_count(review), 0)

    def test_changes_requested_requires_blocking_finding(self):
        finding = {
            "id": "src-low",
            "severity": "low",
            "path": "src/example.py",
            "line": None,
            "title": "Optional cleanup",
            "details": "This is non-blocking.",
            "recommendation": "Consider changing it.",
        }
        with self.assertRaises(review_gate.ReviewError):
            review_gate.normalize_review(review_payload("CHANGES_REQUESTED", [finding]))

    def test_evidence_lists_reject_blank_entries(self):
        for field in ("tests_reviewed", "residual_risks"):
            payload = json.loads(review_payload())
            payload[field] = ["   "]
            with self.assertRaises(review_gate.ReviewError):
                review_gate.normalize_review(json.dumps(payload))

    def test_findings_are_bounded(self):
        finding = {
            "id": "bounded",
            "severity": "low",
            "path": "file.py",
            "line": 1,
            "title": "Finding",
            "details": "Details",
            "recommendation": "Fix it",
        }
        payload = json.loads(review_payload("CHANGES_REQUESTED", [finding]))
        payload["findings"] = [finding] * (review_gate.MAX_FINDINGS + 1)
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

    def test_long_report_truncates_only_at_finding_boundary(self):
        finding = {
            "id": "long",
            "severity": "low",
            "path": "src/example.py",
            "line": 7,
            "title": "Long finding",
            "details": "d" * 5_000,
            "recommendation": "r" * 5_000,
        }
        review = review_gate.normalize_review(
            review_payload("APPROVED", [finding] * review_gate.MAX_FINDINGS)
        )
        report = review_gate.render_review(review, "a" * 40)
        self.assertLess(len(report), 60_000)
        self.assertIn("omitted from this comment at a finding boundary", report)
        self.assertTrue(report.endswith("zero blocking findings.\n"))

    def test_machine_artifact_contains_only_validated_review(self):
        review = review_gate.normalize_review(review_payload())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.json"
            review_gate.write_review_artifact(
                path,
                reviewed_sha="a" * 40,
                route="Claude subscription OAuth",
                review=review,
            )
            artifact = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(artifact["schema_version"], 1)
        self.assertEqual(artifact["status"], "OK")
        self.assertEqual(artifact["review"], review)

    def test_error_artifact_neutralizes_control_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.json"
            review_gate.write_review_artifact(
                path,
                reviewed_sha="a" * 40,
                route="API",
                error="notify @team <!-- hidden -->",
            )
            artifact = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "ERROR")
        self.assertNotIn("@team", artifact["error"])
        self.assertNotIn("<!-- hidden -->", artifact["error"])

    def test_subscription_error_writes_matching_report_and_error_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "review.md"
            artifact_path = Path(directory) / "review.json"
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "REVIEWED_SHA": "a" * 40,
                        "CLAUDE_AUTH_CONFIGURED": "false",
                        "CLAUDE_ACTION_OUTCOME": "skipped",
                    },
                    clear=True,
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "claude_review_gate.py",
                        "--output",
                        str(report),
                        "--json-output",
                        str(artifact_path),
                    ],
                ),
            ):
                self.assertEqual(review_gate.main(), 0)
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            report_text = report.read_text(encoding="utf-8")
        self.assertEqual(artifact["status"], "ERROR")
        self.assertIn("REVIEW UNAVAILABLE", report_text)

if __name__ == "__main__":
    unittest.main()
