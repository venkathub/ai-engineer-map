import importlib.util
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock


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
        rendered = hoe.render_configuration(report)
        self.assertTrue(report["safe_to_start"])
        self.assertNotIn(secret, rendered)
        self.assertNotIn(secret, json_text(report))

    def test_jarvislabs_cli_is_required_but_api_key_is_not(self):
        report = hoe.configuration_report("none", "jarvislabs", {}, which=lambda _: "/usr/bin/jl")
        self.assertTrue(report["safe_to_start"])
        self.assertTrue(report["gpu"]["notes"])

    def test_live_jarvislabs_audit_matches_region_and_workload(self):
        payloads = {
            "status": {
                "balance": {"balance": 10.0},
                "currency": "INR",
                "resources": {"running_instances": 0},
            },
            "list": [],
            "gpus": [
                {
                    "gpu_type": "L4",
                    "region": "IN2",
                    "workload_type": "vm",
                    "num_free_devices": 0,
                    "price_per_hour": 40.0,
                    "spot_price": 20.0,
                    "vram": "24",
                },
                {
                    "gpu_type": "L4",
                    "region": "IN2",
                    "workload_type": "container",
                    "num_free_devices": 5,
                    "price_per_hour": 40.0,
                    "spot_price": 20.0,
                    "vram": "24",
                },
            ],
        }

        def runner(command, **_kwargs):
            return mock.Mock(returncode=0, stdout=json_text(payloads[command[1]]), stderr="")

        report = hoe.jarvislabs_live_report(
            {
                "JL_API_KEY": "never-print",
                "JARVISLABS_GPU": "L4",
                "JARVISLABS_REGION": "IN2",
                "JARVISLABS_WORKLOAD": "container",
                "JARVISLABS_STORAGE_GB": "100",
            },
            runner=runner,
        )
        self.assertTrue(report["authenticated"])
        self.assertTrue(report["configured_gpu_available"])
        self.assertEqual(report["matching_offers"][0]["free_devices"], 5)
        self.assertNotIn("never-print", json_text(report))

    def test_live_jarvislabs_audit_reports_auth_failure_safely(self):
        def runner(_command, **_kwargs):
            return mock.Mock(returncode=1, stdout="", stderr="invalid never-print")

        report = hoe.jarvislabs_live_report({"JL_API_KEY": "never-print"}, runner=runner)
        self.assertFalse(report["authenticated"])
        self.assertNotIn("never-print", json_text(report))


class HoeExecutionTests(unittest.TestCase):
    def test_every_topic_resolves_with_acceptance_evidence(self):
        concepts, catalog = hoe.load_catalog()
        self.assertEqual(set(concepts), set(catalog["topics"]))
        for topic_id in concepts:
            with self.subTest(topic=topic_id):
                topic = hoe.resolve_topic(topic_id)
                self.assertTrue(topic["acceptance"])
                self.assertTrue(topic["artifacts"])

    def test_local_run_executes_declared_argv_without_shell(self):
        topic = hoe.resolve_topic("embeddings")
        completed = mock.Mock(returncode=0)
        with mock.patch.object(hoe.subprocess, "run", return_value=completed) as run:
            with contextlib.redirect_stdout(io.StringIO()):
                result = hoe.execute_topic(topic, "run", allow_billable=False)
        self.assertEqual(result, 0)
        run.assert_called_once_with(
            ["python3", "labs/rag_path.py", "embeddings"],
            cwd=ROOT,
            check=False,
        )

    def test_external_cost_mode_requires_explicit_acknowledgement(self):
        topic = hoe.resolve_topic("peft")
        with mock.patch.object(hoe.subprocess, "run") as run:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = hoe.execute_topic(topic, "verify", allow_billable=False)
        self.assertEqual(result, 2)
        run.assert_not_called()

    def test_guided_run_returns_route_without_subprocess(self):
        topic = hoe.resolve_topic("python-ai")
        with mock.patch.object(hoe.subprocess, "run") as run:
            with contextlib.redirect_stdout(io.StringIO()):
                result = hoe.execute_topic(topic, "run", allow_billable=False)
        self.assertEqual(result, 0)
        run.assert_not_called()


def json_text(value):
    import json

    return json.dumps(value)


if __name__ == "__main__":
    unittest.main()
