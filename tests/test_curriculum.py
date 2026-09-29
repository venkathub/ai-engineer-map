import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "curriculum" / "concepts.json").read_text(encoding="utf-8"))
HOE = json.loads((ROOT / "curriculum" / "hoe.json").read_text(encoding="utf-8"))


class CurriculumCoverageTest(unittest.TestCase):
    def test_complete_track_coverage(self):
        self.assertGreaterEqual(len(DATA["tracks"]), 12)
        self.assertGreaterEqual(len(DATA["concepts"]), 100)

    def test_each_topic_has_proof_of_work(self):
        exercises = []
        for topic in DATA["concepts"]:
            with self.subTest(topic=topic["id"]):
                self.assertTrue(topic["exercise"])
                self.assertGreaterEqual(len(topic["outcomes"]), 2)
                exercises.append(topic["exercise"])
        self.assertEqual(len(exercises), len(set(exercises)))
        self.assertEqual(set(DATA["exerciseFramework"]), {"inspect", "modify", "build"})

    def test_current_topics_exist(self):
        ids = {topic["id"] for topic in DATA["concepts"]}
        required = {
            "reasoning-models", "mcp", "mcp-tasks", "a2a", "agent-skills-hooks",
            "realtime-voice", "prompt-injection", "agentic-security", "content-provenance",
            "ai-regulation", "training-pipelines", "model-registry", "synthetic-data",
            "reinforcement-learning", "system-tevv", "performance-benchmarking",
            "peft", "quantization", "speculative-decoding", "edge-inference", "capstone",
        }
        self.assertTrue(required.issubset(ids))

    def test_every_track_has_live_references(self):
        references = DATA["references"]
        for track in DATA["tracks"]:
            with self.subTest(track=track["id"]):
                self.assertTrue(track["refs"])
                self.assertTrue(all(references[key]["url"].startswith("https://") for key in track["refs"]))

    def test_every_topic_has_an_execution_profile(self):
        topic_ids = {topic["id"] for topic in DATA["concepts"]}
        self.assertEqual(topic_ids, set(HOE["topics"]))
        self.assertTrue(set(HOE["topics"].values()).issubset(HOE["profiles"]))

    def test_paid_profiles_are_never_implicitly_automated(self):
        for profile_id, profile in HOE["profiles"].items():
            with self.subTest(profile=profile_id):
                if profile["mode"] in {"byo-api", "gpu"}:
                    self.assertNotEqual(profile["status"], "automated")


if __name__ == "__main__":
    unittest.main()
