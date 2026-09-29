import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "labs" / "rag-retrieval" / "exercise.py"
SPEC = importlib.util.spec_from_file_location("retrieval_exercise", MODULE_PATH)
retrieval = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = retrieval
SPEC.loader.exec_module(retrieval)


class RetrievalTest(unittest.TestCase):
    def test_tokenizer_preserves_identifiers(self):
        self.assertEqual(retrieval.tokenize("Error E42: model-v2"), ["error", "e42", "model-v2"])

    def test_cosine_identity(self):
        self.assertAlmostEqual(retrieval.cosine_similarity([1, 2], [1, 2]), 1.0)

    def test_cosine_empty_vector(self):
        self.assertEqual(retrieval.cosine_similarity([0, 0], [1, 2]), 0.0)

    def test_cosine_rejects_dimension_mismatch(self):
        with self.assertRaises(ValueError):
            retrieval.cosine_similarity([1], [1, 2])

    def test_search_finds_permission_document(self):
        result = retrieval.search("retrieval authorization evidence", retrieval.DOCUMENTS, limit=1)[0]
        self.assertEqual(result.document.id, "auth")

    def test_search_is_deterministic(self):
        first = retrieval.search("embedding index", retrieval.DOCUMENTS)
        second = retrieval.search("embedding index", retrieval.DOCUMENTS)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
