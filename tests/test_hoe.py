import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hoe", ROOT / "scripts" / "hoe.py")
assert SPEC and SPEC.loader
hoe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hoe)


class HoeConfigurationTests(unittest.TestCase):
    def test_env_file_does_not_override_exported_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "# ignored\nOPENAI_API_KEY=file-secret\nOPENAI_MODEL='test-model'\n",
                encoding="utf-8",
            )
            environ = {"OPENAI_API_KEY": "exported-secret"}
            hoe.load_env(path, environ)
            self.assertEqual(environ["OPENAI_API_KEY"], "exported-secret")
            self.assertEqual(environ["OPENAI_MODEL"], "test-model")

    def test_missing_provider_variables_are_named(self):
        report = hoe.configuration_report("anthropic", "none", {}, which=lambda _: None)
        self.assertFalse(report["safe_to_start"])
        self.assertEqual(
            report["provider"]["missing"],
            ["ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"],
        )

    def test_report_never_contains_secret_value(self):
        secret = "sk-do-not-print-this"
        report = hoe.configuration_report(
            "openai",
            "none",
            {"OPENAI_API_KEY": secret, "OPENAI_MODEL": "example-model"},
            which=lambda _: "/bin/example",
        )
        rendered = hoe.render_human(report)
        self.assertTrue(report["safe_to_start"])
        self.assertNotIn(secret, rendered)
        self.assertNotIn(secret, json_text(report))

    def test_jarvislabs_cli_is_required_but_api_key_is_not(self):
        report = hoe.configuration_report("none", "jarvislabs", {}, which=lambda _: "/usr/bin/jl")
        self.assertTrue(report["safe_to_start"])
        self.assertTrue(report["gpu"]["notes"])


def json_text(value):
    import json

    return json.dumps(value)


if __name__ == "__main__":
    unittest.main()
