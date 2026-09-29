import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validator", ROOT / "scripts/validate_curriculum.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
CATALOG = json.loads((ROOT / "content/tutorials.json").read_text())
KNOWN = {c["id"] for c in json.loads((ROOT / "curriculum/concepts.json").read_text())["concepts"]}


class TutorialTests(unittest.TestCase):
    def test_authored_contract_and_executable_tests(self):
        self.assertEqual(validator.validate_tutorials(KNOWN), [])
        self.assertEqual(len(CATALOG["lessons"]), 11)
        for entry in CATALOG["lessons"].values():
            suite = unittest.defaultTestLoader.loadTestsFromName(entry["verifyTest"])
            self.assertGreater(suite.countTestCases(), 0)
            result = unittest.TestResult()
            suite.run(result)
            self.assertTrue(result.wasSuccessful(), (result.errors, result.failures))

    def test_rejects_missing_and_traversal_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "content").mkdir()
            for bad_path in ("../../secrets.md", "content/rag/missing.md"):
                data = {"schemaVersion": 1, "path": ["embeddings"], "lessons": {
                    "embeddings": {"path": bad_path, "starter": "labs/rag_path.py", "reviewedAt": "2026-09-30"}}}
                (root / "content/tutorials.json").write_text(json.dumps(data))
                with patch.object(validator, "ROOT", root):
                    self.assertTrue(validator.validate_tutorials(KNOWN))

    def test_rejects_duplicate_path_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "content").mkdir()
            data = dict(CATALOG, path=CATALOG["path"] + [CATALOG["path"][0]])
            (root / "content/tutorials.json").write_text(json.dumps(data))
            with patch.object(validator, "ROOT", root):
                self.assertIn("exactly once", validator.validate_tutorials(KNOWN)[0])
