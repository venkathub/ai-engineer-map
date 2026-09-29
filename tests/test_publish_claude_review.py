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
        right, left, anchor, truncated = publisher.diff_anchors(files)
        self.assertIn(3, right["src/app.py"])
        self.assertIn(2, left["src/app.py"])
        self.assertEqual(anchor, {"path": "src/app.py", "line": 3, "side": "RIGHT"})
        self.assertFalse(truncated)

    def test_finding_marker_is_stable_but_sha_scoped(self):
        finding = {"id": "stable-id"}
        first = publisher.finding_marker(finding, "a" * 40)
        self.assertEqual(first, publisher.finding_marker(finding, "a" * 40))
        self.assertNotEqual(first, publisher.finding_marker(finding, "b" * 40))
        self.assertNotIn("stable-id", first)

    def test_path_specific_finding_never_uses_unrelated_fallback(self):
        fallback = {"path": "other.py", "line": 1, "side": "RIGHT"}
        finding = {"path": "target.py", "line": 99}
        with io.StringIO() as output, redirect_stdout(output):
            anchor = publisher.finding_anchor(finding, {"target.py": {2, 3}}, fallback)
            warning = output.getvalue()
        self.assertIsNone(anchor)
        self.assertIn("no exact inline anchor", warning)

    def test_exact_finding_anchor_is_preserved(self):
        finding = {"path": "target.py", "line": 3}
        self.assertEqual(
            publisher.finding_anchor(finding, {"target.py": {2, 3}}, None),
            {"path": "target.py", "line": 3, "side": "RIGHT"},
        )

    def test_inline_failure_falls_back_only_for_http_422(self):
        class Client:
            def __init__(self, status):
                self.status = status
                self.calls = []

            def rest(self, method, path, payload=None):
                self.calls.append((method, path, payload))
                if len(self.calls) == 1:
                    raise publisher.PublishError("failed", status=self.status)
                return {}

        anchor = {"path": "target.py", "line": 3, "side": "RIGHT"}
        client = Client(422)
        publisher.create_thread_or_review(client, 4, "a" * 40, anchor, "body")
        self.assertEqual(client.calls[1][1], "/pulls/4/reviews")

        client = Client(500)
        with self.assertRaises(publisher.PublishError):
            publisher.create_thread_or_review(client, 4, "a" * 40, anchor, "body")
        self.assertEqual(len(client.calls), 1)

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

    def test_new_sha_after_legacy_marker_advances_round(self):
        comment = {"id": 7, "body": f"{publisher.ROUND_MARKER}{'a' * 40} -->"}
        self.assertEqual(publisher.review_round([comment], "b" * 40), (2, None))

    def test_mixed_round_markers_never_decrease_in_non_monotonic_order(self):
        comments = [
            {"id": 3, "body": f"{publisher.ROUND_MARKER}{'c' * 40}:r3 -->"},
            {"id": 1, "body": f"{publisher.ROUND_MARKER}{'a' * 40} -->"},
            {"id": 2, "body": f"{publisher.ROUND_MARKER}{'b' * 40}:r2 -->"},
        ]
        self.assertEqual(publisher.review_round(comments, "d" * 40), (4, None))

    def test_duplicate_explicit_markers_do_not_inflate_next_round(self):
        comments = [
            {"id": 2, "body": f"{publisher.ROUND_MARKER}{'b' * 40}:r2 -->"},
            {"id": 3, "body": f"{publisher.ROUND_MARKER}{'c' * 40}:r3 -->"},
            {"id": 4, "body": f"{publisher.ROUND_MARKER}{'c' * 40}:r3 -->"},
        ]
        self.assertEqual(publisher.review_round(comments, "d" * 40), (4, None))

    def test_legacy_same_sha_uses_deterministic_comment_id_order(self):
        comments = [
            {"id": 20, "body": f"{publisher.ROUND_MARKER}{'b' * 40} -->"},
            {"id": 10, "body": f"{publisher.ROUND_MARKER}{'a' * 40} -->"},
        ]
        self.assertEqual(publisher.review_round(comments, "a" * 40)[0], 1)
        self.assertEqual(publisher.review_round(comments, "b" * 40)[0], 2)

    def test_thread_inventory_fails_closed_when_graphql_is_truncated(self):
        class Client:
            repository = "owner/repo"

            def __init__(self, thread_more=False, comment_more=False):
                self.thread_more = thread_more
                self.comment_more = comment_more

            def graphql(self, _query, _variables):
                return {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": self.thread_more},
                                "nodes": [
                                    {
                                        "comments": {
                                            "pageInfo": {"hasNextPage": self.comment_more},
                                            "nodes": [],
                                        }
                                    }
                                ],
                            }
                        }
                    }
                }

        for client in (Client(thread_more=True), Client(comment_more=True)):
            with self.assertRaises(publisher.PublishError):
                publisher.threads(client, 4)

    def test_anchor_budget_exhaustion_is_visible(self):
        patch = "@@ -1,1 +1,1 @@\n" + " context\n" * 50_001
        with io.StringIO() as output, redirect_stdout(output):
            _right, _left, _anchor, truncated = publisher.diff_anchors(
                [{"filename": "large.txt", "patch": patch}]
            )
            message = output.getvalue()
        self.assertTrue(truncated)
        self.assertIn("50,000-line limit", message)


if __name__ == "__main__":
    unittest.main()
