import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "publish_claude_review.py"
SPEC = importlib.util.spec_from_file_location("publish_claude_review", MODULE_PATH)
publisher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(publisher)


class PublishClaudeReviewTests(unittest.TestCase):
    def test_model_text_is_inert(self):
        rendered = publisher.inert("@team <!-- hidden --> [x](https://bad.test) `code`")
        self.assertNotIn("@team", rendered)
        self.assertNotIn("<!-- hidden -->", rendered)
        self.assertNotIn("https://", rendered)
        self.assertNotIn("[x]", rendered)

    def test_paths_reject_traversal_and_controls(self):
        self.assertTrue(publisher.safe_path("scripts/check.py"))
        for path in ("../secret", "/root/secret", "a\\b", "bad\npath", "a/../b", ""):
            self.assertFalse(publisher.safe_path(path))

    def test_diff_parser_prefers_added_line_anchor(self):
        files = [
            {
                "filename": "src/app.py",
                "patch": "@@ -2,2 +2,3 @@\n old\n+new\n tail",
            }
        ]
        right, left, anchor = publisher.diff_anchors(files)
        self.assertIn(3, right["src/app.py"])
        self.assertIn(2, left["src/app.py"])
        self.assertEqual(anchor, {"path": "src/app.py", "line": 3, "side": "RIGHT"})

    def test_finding_marker_is_stable_but_sha_scoped(self):
        finding = {"id": "stable-id"}
        first = publisher.finding_marker(finding, "a" * 40)
        self.assertEqual(first, publisher.finding_marker(finding, "a" * 40))
        self.assertNotEqual(first, publisher.finding_marker(finding, "b" * 40))
        self.assertNotIn("stable-id", first)

    def test_blocking_severities_match_kaasu_policy(self):
        self.assertEqual(publisher.BLOCKING, {"critical", "high", "medium"})

    def test_round_is_explicit_and_stable_for_same_sha(self):
        comments = [
            {"id": 1, "body": f"{publisher.ROUND_MARKER}{'a' * 40}:r1 -->"},
            {"id": 2, "body": f"{publisher.ROUND_MARKER}{'b' * 40}:r2 -->"},
        ]
        number, comment = publisher.review_round(comments, "b" * 40)
        self.assertEqual((number, comment["id"]), (2, 2))
        self.assertEqual(publisher.review_round(comments, "c" * 40), (3, None))

    def test_legacy_round_marker_is_rewritten_as_round_one(self):
        comment = {"id": 7, "body": f"{publisher.ROUND_MARKER}{'a' * 40} -->"}
        number, same = publisher.review_round([comment], "a" * 40)
        self.assertEqual((number, same["id"]), (1, 7))

    def test_anchor_budget_exhaustion_is_visible(self):
        patch = "@@ -1,1 +1,1 @@\n" + " context\n" * 50_001
        with io.StringIO() as output, redirect_stdout(output):
            publisher.diff_anchors([{"filename": "large.txt", "patch": patch}])
            message = output.getvalue()
        self.assertIn("50,000-line limit", message)


if __name__ == "__main__":
    unittest.main()
