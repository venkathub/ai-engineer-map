import importlib.util
import json
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
        with mock.patch.object(api_review, "_request", return_value=b"diff --git a/x b/x") as request:
            diff = api_review.fetch_pull_request_diff("owner/repo", 4, "hidden-token")
        self.assertEqual(diff, "diff --git a/x b/x")
        headers = dict(request.call_args.args[0].header_items())
        self.assertEqual(headers["Accept"], "application/vnd.github.v3.diff")
        self.assertEqual(headers["Authorization"], "Bearer hidden-token")

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
        self.assertEqual(json.loads(raw)["verdict"], "APPROVED")
        self.assertEqual(usage["output_tokens"], 5)

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


def urllib_error(status, body):
    from io import BytesIO
    from urllib.error import HTTPError

    return HTTPError("https://example.test", status, "error", {}, BytesIO(json.dumps(body).encode()))


if __name__ == "__main__":
    unittest.main()
