import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "curriculum" / "concepts.json").read_text(encoding="utf-8"))


class CurriculumCoverageTest(unittest.TestCase):
    def test_complete_track_coverage(self):
        self.assertGreaterEqual(len(DATA["tracks"]), 10)
        self.assertGreaterEqual(len(DATA["concepts"]), 70)

    def test_each_topic_has_proof_of_work(self):
        for topic in DATA["concepts"]:
            with self.subTest(topic=topic["id"]):
                self.assertTrue(topic["exercise"])
                self.assertGreaterEqual(len(topic["outcomes"]), 2)

    def test_current_topics_exist(self):
        ids = {topic["id"] for topic in DATA["concepts"]}
        required = {"mcp", "a2a", "realtime-voice", "prompt-injection", "agent-evals", "peft", "quantization", "capstone"}
        self.assertTrue(required.issubset(ids))

    def test_every_track_has_live_references(self):
        references = DATA["references"]
        for track in DATA["tracks"]:
            with self.subTest(track=track["id"]):
                self.assertTrue(track["refs"])
                self.assertTrue(all(references[key]["url"].startswith("https://") for key in track["refs"]))


if __name__ == "__main__":
    unittest.main()
