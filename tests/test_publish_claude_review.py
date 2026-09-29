import importlib.util
import io
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


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

    def test_cli_surfaces_a_safely_escaped_actions_error(self):
        error = publisher.PublishError("blocked 100%\nneeds-human")
        with (
            mock.patch.object(publisher, "main", side_effect=error),
            io.StringIO() as stderr,
            mock.patch("sys.stderr", stderr),
        ):
            self.assertEqual(publisher.cli(), 1)
            rendered = stderr.getvalue()
        self.assertIn("::error title=Claude review publisher::", rendered)
        self.assertIn("100%25%0Aneeds-human", rendered)
        self.assertNotIn("100%\n", rendered)

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

    def test_path_only_finding_uses_first_changed_line_in_same_file(self):
        finding = {"path": "target.py", "line": None}
        with io.StringIO() as output, redirect_stdout(output):
            anchor = publisher.finding_anchor(
                finding, {"target.py": {9, 4}, "other.py": {1}}, None
            )
            warning = output.getvalue()
        self.assertEqual(anchor, {"path": "target.py", "line": 4, "side": "RIGHT"})
        self.assertIn("finding omitted a line", warning)

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

    def test_every_legacy_marker_is_treated_as_round_one(self):
        comments = [
            {"id": 20, "body": f"{publisher.ROUND_MARKER}{'b' * 40} -->"},
            {"id": 10, "body": f"{publisher.ROUND_MARKER}{'a' * 40} -->"},
        ]
        self.assertEqual(publisher.review_round(comments, "a" * 40)[0], 1)
        self.assertEqual(publisher.review_round(comments, "b" * 40)[0], 1)
        self.assertEqual(publisher.review_round(comments, "c" * 40)[0], 2)

    def test_explicit_rounds_follow_comment_create_and_edit_shapes(self):
        comments = []
        sha_a, sha_b, sha_c = "a" * 40, "b" * 40, "c" * 40
        round_a, existing = publisher.review_round(comments, sha_a)
        self.assertEqual((round_a, existing), (1, None))
        comments.append({"id": 100, "body": f"{publisher.ROUND_MARKER}{sha_a}:r1 -->"})
        round_b, existing = publisher.review_round(comments, sha_b)
        self.assertEqual((round_b, existing), (2, None))
        comments.append({"id": 101, "body": f"{publisher.ROUND_MARKER}{sha_b}:r2 -->"})
        self.assertEqual(publisher.review_round(comments, sha_b)[0], 2)
        self.assertEqual(publisher.review_round(comments, sha_b)[1]["id"], 101)
        self.assertEqual(publisher.review_round(comments, sha_c), (3, None))

    def test_native_round_review_is_visible_once_per_exact_head(self):
        class Client:
            def __init__(self, existing=None):
                self.existing = existing or []
                self.calls = []

            def rest(self, method, path, payload=None):
                self.calls.append((method, path, payload))
                if method == "GET":
                    return self.existing
                return {}

        sha = "a" * 40
        body = f"{publisher.ROUND_MARKER}{sha}:r1 -->\nAPPROVED"
        client = Client()
        publisher.ensure_native_round_review(client, 4, sha, body)
        self.assertEqual(client.calls[0][1], "/pulls/4/reviews?per_page=100&page=1")
        self.assertEqual(client.calls[1][1], "/pulls/4/reviews")
        self.assertEqual(client.calls[1][2]["commit_id"], sha)
        self.assertEqual(client.calls[1][2]["event"], "COMMENT")

        client = Client([{"body": body}])
        publisher.ensure_native_round_review(client, 4, sha, body)
        self.assertEqual(len(client.calls), 1)

    def test_native_round_review_failure_fails_closed_and_remains_retryable(self):
        class Client:
            def __init__(self):
                self.post_attempts = 0

            def rest(self, method, _path, _payload=None):
                if method == "GET":
                    return []
                self.post_attempts += 1
                if self.post_attempts == 1:
                    raise publisher.PublishError("transient native review failure")
                return {}

        client = Client()
        sha = "a" * 40
        body = f"{publisher.ROUND_MARKER}{sha}:r1 -->\nAPPROVED"
        with self.assertRaisesRegex(publisher.PublishError, "transient native review failure"):
            publisher.ensure_native_round_review(client, 4, sha, body)
        publisher.ensure_native_round_review(client, 4, sha, body)
        self.assertEqual(client.post_attempts, 2)

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

    def test_write_capability_is_probed_before_mutation(self):
        class Client:
            repository = "owner/repo"

            def __init__(self, permission):
                self.permission = permission

            def graphql(self, _query, _variables):
                return {"repository": {"viewerPermission": self.permission}}

        for permission in ("WRITE", "MAINTAIN", "ADMIN"):
            publisher.verify_write_capability(Client(permission))
        for permission in ("READ", "TRIAGE", None):
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(publisher.PublishError):
                    publisher.verify_write_capability(Client(permission))

        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            publisher.verify_write_capability(Client("READ"))
            for permission in ("TRIAGE", None):
                with self.assertRaises(publisher.PublishError):
                    publisher.verify_write_capability(Client(permission))

    def test_publish_authorization_fails_closed_on_human_hold(self):
        class Client:
            def rest(self, _method, _path):
                return {"labels": [{"name": "needs-human"}]}

        with self.assertRaises(publisher.PublishError) as raised:
            publisher.require_publish_authorization(Client(), 4, False, "test mutation")
        self.assertIn("test mutation", str(raised.exception))
        publisher.require_publish_authorization(Client(), 4, True, "forced mutation")

    def test_new_head_revokes_approval_before_later_api_reads(self):
        client = object()
        with (
            mock.patch.object(publisher, "set_labels") as set_labels,
            mock.patch.object(publisher, "labels", return_value=set()),
            mock.patch.object(
                publisher,
                "list_pages",
                side_effect=publisher.PublishError("file inventory failed"),
            ),
        ):
            with self.assertRaisesRegex(publisher.PublishError, "file inventory failed"):
                publisher.block_exact_head(client, 4, "a" * 40, False)
        set_labels.assert_called_once_with(client, 4, set(), {"claude:approved"})

    def test_hold_added_during_blocking_wins_the_race(self):
        client = object()
        with (
            mock.patch.object(publisher, "set_labels"),
            mock.patch.object(
                publisher,
                "labels",
                side_effect=[set(), {"needs-human"}],
            ),
            mock.patch.object(publisher, "list_pages", return_value=[]),
            mock.patch.object(publisher, "ensure_pending_comment"),
            mock.patch.object(publisher, "threads", return_value=[]),
            mock.patch.object(publisher, "remove_legacy_pending_threads"),
        ):
            with self.assertRaisesRegex(
                publisher.PublishError,
                "needs-human was applied while blocking the head",
            ):
                publisher.block_exact_head(client, 4, "a" * 40, False)

    def test_pending_state_is_a_standalone_comment_and_legacy_inline_is_removed(self):
        class Client:
            def __init__(self):
                self.calls = []

            def rest(self, method, path, payload=None):
                self.calls.append((method, path, payload))
                return {}

        client = Client()
        publisher.ensure_pending_comment(client, 4, "a" * 40, [])
        self.assertEqual(client.calls[0][0:2], ("POST", "/issues/4/comments"))
        self.assertNotIn("thread", client.calls[0][2]["body"].lower())

        legacy = {
            "comments": {
                "nodes": [
                    {
                        "databaseId": 99,
                        "body": f"{publisher.LEGACY_PENDING_MARKER}\nlegacy inline state",
                    }
                ]
            }
        }
        publisher.remove_legacy_pending_threads(client, [legacy])
        self.assertEqual(client.calls[1][0:2], ("DELETE", "/pulls/comments/99"))

    def test_anchor_budget_exhaustion_is_visible(self):
        patch = "@@ -1,1 +1,1 @@\n" + " context\n" * 50_001
        with io.StringIO() as output, redirect_stdout(output):
            _right, _left, _anchor, truncated = publisher.diff_anchors(
                [{"filename": "large.txt", "patch": patch}]
            )
            message = output.getvalue()
        self.assertTrue(truncated)
        self.assertIn("50,000-line limit", message)

    def test_path_beyond_anchor_budget_uses_general_review(self):
        patch = "@@ -1,1 +1,1 @@\n" + " context\n" * 50_001
        with redirect_stdout(io.StringIO()):
            right, _left, fallback, truncated = publisher.diff_anchors(
                [
                    {"filename": "large.txt", "patch": patch},
                    {"filename": "later.py", "patch": "@@ -0,0 +1 @@\n+new"},
                ]
            )
            if truncated:
                fallback = None
            anchor = publisher.finding_anchor(
                {"path": "later.py", "line": 1}, right, fallback
            )

        class Client:
            def __init__(self):
                self.calls = []

            def rest(self, method, path, payload=None):
                self.calls.append((method, path, payload))
                return {}

        client = Client()
        publisher.create_thread_or_review(client, 4, "a" * 40, anchor, "body")
        self.assertTrue(truncated)
        self.assertIsNone(anchor)
        self.assertEqual(client.calls[0][1], "/pulls/4/reviews")


if __name__ == "__main__":
    unittest.main()
