import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "claude_api_review.py"
SPEC = importlib.util.spec_from_file_location("claude_api_review", MODULE_PATH)
api_review = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(api_review)


class ClaudeApiReviewTests(unittest.TestCase):
    def test_prompt_marks_diff_as_untrusted(self):
        prompt = api_review.build_prompt("diff --git a/x b/x", "trusted rules", "abc123")
        self.assertIn("untrusted data", prompt)
        self.assertIn("exact head commit abc123", prompt)
        self.assertIn("<pull_request_diff>", prompt)

    def test_fetch_diff_uses_github_diff_media_type(self):
        head_sha = "a" * 40
        base_sha = "b" * 40
        metadata = {"head": {"sha": head_sha}, "base": {"sha": base_sha}}
        with mock.patch.object(
            api_review,
            "_request",
            side_effect=[json.dumps(metadata).encode(), b"diff --git a/x b/x"],
        ) as request:
            diff = api_review.fetch_pull_request_diff("owner/repo", 4, head_sha, "hidden-token")
        self.assertEqual(diff, "diff --git a/x b/x")
        self.assertEqual(request.call_count, 2)
        headers = dict(request.call_args_list[1].args[0].header_items())
        self.assertEqual(headers["Accept"], "application/vnd.github.v3.diff")
        self.assertEqual(headers["Authorization"], "Bearer hidden-token")
        self.assertIn(f"/compare/{base_sha}...{head_sha}", request.call_args_list[1].args[0].full_url)
        self.assertEqual(
            request.call_args_list[1].kwargs["max_bytes"], api_review.MAX_DIFF_BYTES
        )

    def test_fetch_diff_rejects_head_changed_after_event(self):
        expected_sha = "a" * 40
        metadata = {"head": {"sha": "b" * 40}, "base": {"sha": "c" * 40}}
        with mock.patch.object(
            api_review, "_request", return_value=json.dumps(metadata).encode()
        ) as request:
            with self.assertRaises(api_review.ProviderError) as raised:
                api_review.fetch_pull_request_diff("owner/repo", 4, expected_sha, "hidden-token")
        self.assertEqual(request.call_count, 1)
        self.assertIn("head changed", str(raised.exception))

    def test_verify_model_accepts_exact_live_catalog_id(self):
        model_record = {"id": "claude-sonnet-5", "type": "model"}
        with mock.patch.object(
            api_review, "_request", return_value=json.dumps(model_record).encode()
        ) as request:
            api_review.verify_model("hidden-key", "claude-sonnet-5")
        self.assertTrue(request.call_args.args[0].full_url.endswith("/v1/models/claude-sonnet-5"))

    def test_verify_model_rejects_unlisted_id(self):
        model_record = {"id": "different-model", "type": "model"}
        with mock.patch.object(
            api_review, "_request", return_value=json.dumps(model_record).encode()
        ):
            with self.assertRaises(api_review.ProviderError) as raised:
                api_review.verify_model("hidden-key", "not-a-model")
        self.assertNotIn("not-a-model", str(raised.exception))

    def test_empty_model_override_uses_verified_default(self):
        self.assertEqual(api_review.resolve_model(""), api_review.DEFAULT_MODEL)
        self.assertEqual(api_review.resolve_model("   "), api_review.DEFAULT_MODEL)
        self.assertEqual(api_review.resolve_model(None), api_review.DEFAULT_MODEL)
        self.assertEqual(api_review.resolve_model(" model-id "), "model-id")
        for invalid in ("../model", "MODEL", "https://example.test", "x" * 129):
            with self.assertRaises(api_review.ProviderError):
                api_review.resolve_model(invalid)

    def test_reviewed_sha_requires_full_lowercase_commit_id(self):
        valid = "a" * 40
        self.assertEqual(api_review.validate_reviewed_sha(valid), valid)
        for invalid in ("abc123", "A" * 40, "a" * 41, "../main"):
            with self.assertRaises(api_review.ProviderError):
                api_review.validate_reviewed_sha(invalid)

    def test_claude_request_uses_structured_output(self):
        response = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "verdict": "APPROVED",
                            "summary": "No defects found.",
                            "findings": [],
                            "tests_reviewed": [],
                            "residual_risks": [],
                        }
                    ),
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        with mock.patch.object(api_review, "_request", return_value=json.dumps(response).encode()) as request:
            raw, usage = api_review.call_claude("hidden-key", "claude-sonnet-5", "review this")
        payload = json.loads(request.call_args.args[0].data.decode())
        self.assertEqual(payload["output_config"]["format"]["type"], "json_schema")
        self.assertNotIn("effort", payload["output_config"])
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(json.loads(raw)["verdict"], "APPROVED")
        self.assertEqual(usage["output_tokens"], 5)

    def test_max_token_response_is_rejected(self):
        response = {
            "content": [{"type": "thinking", "thinking": ""}],
            "stop_reason": "max_tokens",
            "usage": {"output_tokens": 8_000},
        }
        with mock.patch.object(api_review, "_request", return_value=json.dumps(response).encode()):
            with self.assertRaises(api_review.ProviderError) as raised:
                api_review.call_claude("hidden-key", "claude-sonnet-5", "review this")
        self.assertIn("token limit", str(raised.exception))

    def test_claude_request_combines_split_text_blocks(self):
        response = {
            "content": [
                {"type": "text", "text": '{"verdict":"APP'},
                {"type": "text", "text": 'ROVED"}'},
            ],
            "usage": {},
        }
        with mock.patch.object(api_review, "_request", return_value=json.dumps(response).encode()):
            raw, _ = api_review.call_claude("hidden-key", "claude-sonnet-5", "review this")
        self.assertEqual(json.loads(raw)["verdict"], "APPROVED")

    def test_provider_error_does_not_include_response_message(self):
        request = mock.Mock()
        error = urllib_error(401, {"error": {"type": "authentication_error", "message": "private"}})
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(api_review.ProviderError) as raised:
                api_review._request(request)
        self.assertIn("authentication_error", str(raised.exception))
        self.assertNotIn("private", str(raised.exception))

    def test_request_caps_untrusted_response_before_buffering(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"1234"
        with mock.patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(api_review.ProviderError) as raised:
                api_review._request(mock.Mock(), max_bytes=3)
        response.__enter__.return_value.read.assert_called_once_with(4)
        self.assertIn("3-byte limit", str(raised.exception))

    def test_verify_model_only_mode_skips_review_request(self):
        with (
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "hidden-key"}, clear=True),
            mock.patch.object(sys, "argv", ["claude_api_review.py", "--verify-model-only"]),
            mock.patch.object(api_review, "verify_model") as verify,
            mock.patch.object(api_review, "call_claude") as review,
        ):
            self.assertEqual(api_review.main(), 0)
        verify.assert_called_once_with("hidden-key", api_review.DEFAULT_MODEL)
        review.assert_not_called()


def urllib_error(status, body):
    from io import BytesIO
    from urllib.error import HTTPError

    return HTTPError("https://example.test", status, "error", {}, BytesIO(json.dumps(body).encode()))


if __name__ == "__main__":
    unittest.main()
