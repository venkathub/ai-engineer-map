"""Topic-specific behavioral checks for the RAG teaching path."""
import copy
import unittest
from dataclasses import replace
from labs import rag_path as rag


class IngestionTests(unittest.TestCase):
    def test_resume_and_content_change(self):
        source = rag.Source("a", 1, "acme", "first")
        first = rag.ingest([source])
        self.assertFalse(first["acme/a/1"]["reused"])
        self.assertTrue(rag.ingest([source], first)["acme/a/1"]["reused"])
        self.assertFalse(rag.ingest([replace(source, text="changed")], first)["acme/a/1"]["reused"])

    def test_parse_failure_and_tenant_identity(self):
        result = rag.ingest([rag.Source("a", 1, "acme", ""), rag.Source("a", 1, "other", "valid")])
        self.assertEqual(result["acme/a/1"]["status"], "parse-error")
        self.assertEqual(result["other/a/1"]["status"], "ready")


class ChunkingTests(unittest.TestCase):
    def test_boundaries_and_provenance(self):
        source = rag.Source("a", 2, "acme", "Refunds require the original receipt.\n\nThe deadline is 30 days.")
        fixed = rag.chunk(source, "fixed")
        self.assertFalse(any("Refunds require the original receipt." in c.text for c in fixed))
        self.assertTrue(any("Refunds require the original receipt." in c.text for c in rag.chunk(source)))
        for policy in ("fixed", "overlap", "paragraph"):
            for c in rag.chunk(source, policy):
                self.assertEqual(c.text, source.text[c.start:c.end])
                self.assertEqual((c.tenant, c.version), ("acme", 2))

    def test_overlap_validation_and_determinism(self):
        with self.assertRaises(ValueError):
            rag.chunk(rag.SOURCES[1], "overlap", width=4, overlap=4)
        self.assertEqual(rag.chunk(rag.SOURCES[1]), rag.chunk(rag.SOURCES[1]))


class EmbeddingTests(unittest.TestCase):
    def test_cosine_and_incompatible_dimensions(self):
        self.assertAlmostEqual(rag.cosine([1, 1], [3, 3]), 1)
        self.assertEqual(rag.cosine([1, 0], [0, 1]), 0)
        self.assertEqual(rag.cosine([0, 0], [1, 0]), 0)
        with self.assertRaises(ValueError):
            rag.cosine([1], [1, 2])

    def test_coordinate_migration(self):
        old = rag.encode("refund", ["refund", "receipt"])
        new = rag.encode("refund", ["receipt", "refund"])
        self.assertEqual(rag.cosine(old, new), 0)
        self.assertEqual(rag.cosine(new, new), 1)


class VectorIndexTests(unittest.TestCase):
    def test_invalid_candidate_budget(self):
        with self.assertRaises(ValueError):
            rag.vector_rank("E42", rag.corpus(), -1)

    def test_candidate_budget_recall(self):
        report = rag.experiment("vector-indexes")
        self.assertEqual(report["candidate_budget_sweep"][0]["recall_at_1"], 0)
        self.assertEqual(report["candidate_budget_sweep"][-1]["recall_at_1"], 1)

    def test_exact_identifier_and_determinism(self):
        ranked = rag.vector_rank("E42", rag.corpus())
        self.assertEqual(ranked[0].source, "e42")
        self.assertEqual(ranked, rag.vector_rank("E42", list(reversed(rag.corpus()))))


class HybridTests(unittest.TestCase):
    def test_fusion_and_duplicate_votes(self):
        a, b, c = rag.corpus()[:3]
        self.assertEqual(rag.rrf([[a, b], [b, c]])[0], b)
        self.assertEqual(rag.rrf([[a, a], [b]])[0].id, min(a.id, b.id))
        with self.assertRaises(ValueError):
            rag.rrf([[a]], 0)

    def test_identifier_preserved(self):
        self.assertEqual(rag.lexical_rank("E42", rag.corpus())[0].source, "e42")


class QueryTests(unittest.TestCase):
    def test_rewrite_preserves_identifiers(self):
        for variant in rag.rewrite("E42 reimbursement"):
            self.assertIn("e42", rag.tokens(variant))
        self.assertEqual(rag.route("E42"), "runbooks")
        self.assertEqual(rag.route("refund"), "policies")

    def test_multi_query_recovers_alias(self):
        report = rag.experiment("query-transform")
        self.assertNotIn("/refund/", report["before"][0])
        self.assertTrue(any("/refund/" in key for key in report["after"]))


class RerankingTests(unittest.TestCase):
    def test_lift_and_redundancy(self):
        report = rag.experiment("reranking")
        self.assertGreater(report["after_ndcg"], report["before_ndcg"])
        self.assertEqual(report["after_ndcg"], 1)
        self.assertNotIn("duplicate", report["ranking"])

    def test_cannot_recover_missing_candidate(self):
        without = [c for c in rag.corpus() if c.source != "e42"]
        self.assertFalse(any(c.source == "e42" for c in rag.rerank("E42", without)))


class GroundingTests(unittest.TestCase):
    def test_malformed_citations_fail_closed(self):
        for result in ({}, {"status": "answered", "claims": []}, {"status": "unknown", "claims": []},
                       {"status": "answered", "claims": [{}]}, {"status": "insufficient-evidence", "claims": [{}]}):
            self.assertFalse(rag.valid_citations(result, rag.SOURCES, "acme"))
        result = rag.pipeline("refund window")
        result["claims"][0]["citation"]["id"] = "invented"
        self.assertFalse(rag.valid_citations(result, rag.SOURCES, "acme"))

    def test_cited_answer_and_abstention(self):
        answer = rag.pipeline("refund window")
        self.assertEqual(answer["status"], "answered")
        self.assertIn("30 days", answer["claims"][0]["text"])
        self.assertTrue(rag.valid_citations(answer, rag.SOURCES, "acme"))
        self.assertEqual(rag.pipeline("lunar telescope")["status"], "insufficient-evidence")
        self.assertEqual(rag.pipeline("")["status"], "insufficient-evidence")

    def test_reject_tampered_claim_and_offset(self):
        result = rag.pipeline("refund window")
        for field, value in [("text", "Refund window is 99 days."), ("start", -1)]:
            changed = copy.deepcopy(result)
            if field == "text":
                changed["claims"][0][field] = value
            else:
                changed["claims"][0]["citation"][field] = value
            self.assertFalse(rag.valid_citations(changed, rag.SOURCES, "acme"))


class StructuredTests(unittest.TestCase):
    def test_allowlist_and_bound_parameters(self):
        self.assertEqual(rag.structured_lookup("refund-days", "acme"), [(30,)])
        self.assertEqual(rag.structured_lookup("refund-days", "acme' OR 1=1 --"), [])
        with self.assertRaises(ValueError):
            rag.structured_lookup("DROP TABLE policies", "acme")


class QualityTests(unittest.TestCase):
    def test_filter_before_rank_and_tombstone(self):
        candidates = rag.corpus()
        self.assertTrue(all(c.tenant == "acme" for c in candidates))
        self.assertNotIn("retired", {c.source for c in candidates})
        self.assertTrue(all(c.version == 2 for c in candidates if c.source == "refund"))
        self.assertEqual(rag.pipeline("refund window", "unknown")["status"], "insufficient-evidence")

    def test_delete_and_revoke_old_citation(self):
        answer = rag.pipeline("refund window")
        deleted = rag.SOURCES + [rag.Source("refund", 3, "acme", "", True)]
        self.assertFalse(rag.valid_citations(answer, deleted, "acme"))
        self.assertFalse(rag.valid_citations(answer, rag.SOURCES, "other"))


class EvaluationTests(unittest.TestCase):
    def test_metrics_hand_calculation(self):
        self.assertEqual(rag.recall(["a", "a"], {"a", "b"}, 2), 0.5)
        self.assertEqual(rag.recall([], set(), 1), 0)
        self.assertEqual(rag.ndcg(["b", "a"], {"a": 1}, 2), 1 / rag.math.log2(3))
        self.assertLessEqual(rag.ndcg(["a", "a"], {"a": 1}, 2), 1)

    def test_gold_cases_pass(self):
        report = rag.experiment("rag-evals")
        self.assertEqual(report["correct_rate"], 1)
        self.assertTrue(all(row["citation_valid"] for row in report["cases"]))


if __name__ == "__main__":
    unittest.main()
