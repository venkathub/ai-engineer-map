"""Executable RAG teaching baselines. Standard library only; no model or network calls.

Run from the repository root: python3 labs/rag_path.py <topic-id>
Modify a function, then use the topic's HOE verify command to test the change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from contextlib import closing
from dataclasses import asdict, dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class Source:
    id: str
    version: int
    tenant: str
    text: str
    deleted: bool = False


@dataclass(frozen=True)
class Chunk:
    id: str
    source: str
    version: int
    tenant: str
    start: int
    end: int
    text: str


SOURCES = [
    Source("refund", 1, "acme", "Refund window is 14 days."),
    Source("refund", 2, "acme", "Refund window is 30 days.\n\nRefund requests require a receipt."),
    Source("retry", 1, "acme", "Retry transient failures with exponential backoff and jitter."),
    Source("e42", 1, "acme", "Error E42 indicates an embedding version mismatch."),
    Source("private", 1, "other", "Refund window is 365 days. Internal contract."),
    Source("retired", 1, "acme", "Refund window is 90 days."),
    Source("retired", 2, "acme", "", deleted=True),
]


def tokens(text):
    return re.findall(r"[a-z0-9][a-z0-9_-]*", text.lower())


def ingest(sources, previous=None):
    """Versioned manifest; valid entries are reusable only when all input metadata matches."""
    previous = previous or {}
    manifest = {}
    for source in sources:
        key = f"{source.tenant}/{source.id}/{source.version}"
        digest = hashlib.sha256(source.text.encode()).hexdigest()
        valid = bool(source.text.strip()) or source.deleted
        entry = {"digest": digest, "deleted": source.deleted, "status": "ready" if valid else "parse-error"}
        entry["reused"] = valid and all(previous.get(key, {}).get(k) == v for k, v in entry.items())
        manifest[key] = entry
    return manifest


def authorized_current(sources, tenant):
    """Tenant comes from trusted authentication, never retrieved text or model output."""
    latest = {}
    for source in sources:
        if source.tenant != tenant:
            continue
        if source.id not in latest or source.version > latest[source.id].version:
            latest[source.id] = source
    return [s for s in latest.values() if not s.deleted and s.text.strip()]


def chunk(source, policy="paragraph", width=32, overlap=8):
    if width < 1 or overlap < 0 or overlap >= width:
        raise ValueError("require width > overlap >= 0")
    if policy == "paragraph":
        spans = [(m.start(), m.end()) for m in re.finditer(r"[^\n]+", source.text)]
    elif policy in {"fixed", "overlap"}:
        step = width - overlap if policy == "overlap" else width
        spans = [(start, min(start + width, len(source.text))) for start in range(0, len(source.text), step)]
    else:
        raise ValueError("unknown chunk policy")
    return [Chunk(f"{source.tenant}/{source.id}/v{source.version}:{start}-{end}", source.id,
                  source.version, source.tenant, start, end, source.text[start:end])
            for start, end in spans if source.text[start:end].strip()]


def cosine(left, right):
    if len(left) != len(right):
        raise ValueError("incompatible dimensions")
    norm = math.sqrt(sum(x*x for x in left) * sum(x*x for x in right))
    return sum(a*b for a, b in zip(left, right)) / norm if norm else 0.0


def encode(text, vocabulary):
    counts = Counter(tokens(text))
    return [counts[word] for word in vocabulary]


def vector_rank(query, chunks, budget=None):
    """Exact bag-of-words cosine; optional prefix candidate pruning is a toy ANN surrogate."""
    if budget is not None and budget < 1:
        raise ValueError("candidate budget must be positive")
    vocabulary = sorted({word for c in chunks for word in tokens(c.text)} | set(tokens(query)))
    candidates = chunks if budget is None else chunks[:budget]
    return sorted(candidates, key=lambda c: (-cosine(encode(query, vocabulary), encode(c.text, vocabulary)), c.id))


def lexical_rank(query, chunks):
    words = set(tokens(query))
    return sorted(chunks, key=lambda c: (-len(words & set(tokens(c.text))), c.id))


def rrf(rankings, constant=60):
    if constant < 1:
        raise ValueError("constant must be positive")
    scores, records = {}, {}
    for ranking in rankings:
        seen = set()
        for rank, item in enumerate(ranking, 1):
            if item.id in seen:
                continue
            seen.add(item.id)
            records[item.id] = item
            scores[item.id] = scores.get(item.id, 0) + 1 / (constant + rank)
    return [records[key] for key in sorted(scores, key=lambda key: (-scores[key], key))]


def rewrite(query):
    """Deterministic alias expansion preserves all original tokens, especially error codes."""
    return [query, query + " refund"] if "reimbursement" in tokens(query) else [query]


def route(query):
    return "runbooks" if any(re.fullmatch(r"e\d+", word) for word in tokens(query)) else "policies"


def rerank(query, candidates):
    # A transparent lexical coverage reranker, not a neural cross-encoder.
    ranked = lexical_rank(query, candidates)
    seen, result = set(), []
    for item in ranked:
        fingerprint = tuple(tokens(item.text))
        if fingerprint not in seen:
            seen.add(fingerprint)
            result.append(item)
    return result


def recall(ranking, relevant, k):
    return len(set(ranking[:k]) & set(relevant)) / len(set(relevant)) if relevant else 0.0


def ndcg(ranking, grades, k):
    def dcg(values):
        return sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(values))
    ideal = dcg(sorted(grades.values(), reverse=True)[:k])
    seen = set()
    values = []
    for key in ranking[:k]:
        values.append(0 if key in seen else grades.get(key, 0))
        seen.add(key)
    return dcg(values) / ideal if ideal else 0.0


def answer(query, candidates, min_coverage=0.5):
    """Extractive baseline: cite exact spans, abstain on insufficient token overlap.

    Token overlap is only a teaching heuristic, not a factual-support classifier.
    Callers must pass authorized, current chunks.
    """
    words = set(tokens(query))
    ranked = rerank(query, candidates)
    if not words or not ranked:
        return {"status": "insufficient-evidence", "claims": []}
    best = ranked[0]
    coverage = len(words & set(tokens(best.text))) / len(words)
    if coverage < min_coverage:
        return {"status": "insufficient-evidence", "claims": []}
    return {"status": "answered", "claims": [{"text": best.text, "citation": asdict(best)}]}


def valid_citations(result, sources, tenant):
    allowed = {(s.id, s.version): s for s in authorized_current(sources, tenant)}
    try:
        if result["status"] == "insufficient-evidence":
            return result["claims"] == []
        if result["status"] != "answered" or not isinstance(result["claims"], list) or not result["claims"]:
            return False
        for claim in result["claims"]:
            c = claim["citation"]
            source = allowed.get((c["source"], c["version"]))
            if not source or c["tenant"] != tenant or not 0 <= c["start"] < c["end"] <= len(source.text):
                return False
            expected_id = f"{tenant}/{source.id}/v{source.version}:{c['start']}-{c['end']}"
            if c["id"] != expected_id or claim["text"] != c["text"] or claim["text"] != source.text[c["start"]:c["end"]]:
                return False
        return True
    except (KeyError, TypeError):
        return False


def structured_lookup(intent, tenant):
    """Allowlisted intent to parameterized SQL; never execute generated SQL strings."""
    if intent != "refund-days":
        raise ValueError("unsupported query intent")
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE policies (tenant TEXT, days INTEGER)")
        db.executemany("INSERT INTO policies VALUES (?, ?)", [("acme", 30), ("other", 365)])
        db.execute("PRAGMA query_only = ON")
        return db.execute("SELECT days FROM policies WHERE tenant = ?", (tenant,)).fetchall()


def corpus(tenant="acme", sources=None):
    return [c for s in authorized_current(SOURCES if sources is None else sources, tenant) for c in chunk(s)]


def pipeline(query, tenant="acme", sources=None):
    candidates = corpus(tenant, sources)
    rankings = []
    for variant in rewrite(query):
        rankings.extend([lexical_rank(variant, candidates), vector_rank(variant, candidates)])
    return answer(query, rerank(query, rrf(rankings)))


def experiment(topic):
    chunks = corpus()
    ids = lambda rows: [row.id for row in rows]
    if topic == "document-ingestion":
        first = ingest(SOURCES + [Source("broken", 1, "acme", "")])
        return {"first": first, "resumed": ingest(SOURCES, first)}
    if topic == "chunking":
        source = Source("boundary", 1, "acme", "Refunds require the original receipt.\n\nThe deadline is 30 days.")
        return {policy: {"chunks": [asdict(c) for c in chunk(source, policy)],
                         "intact_receipt_fact": any("Refunds require the original receipt." in c.text for c in chunk(source, policy))}
                for policy in ["fixed", "overlap", "paragraph"]}
    if topic == "embeddings":
        return {"identical": cosine([1, 0], [1, 0]), "orthogonal": cosine([1, 0], [0, 1]),
                "scaled": cosine([1, 0], [3, 0]), "zero": cosine([0, 0], [1, 0]),
                "representation": "bag-of-words; coordinate vocabulary must match"}
    if topic == "vector-indexes":
        exact = ids(vector_rank("E42", chunks))[:1]
        return {"exact_top1": exact, "candidate_budget_sweep": [
            {"budget": budget, "recall_at_1": recall(ids(vector_rank("E42", chunks, budget)), exact, 1)}
            for budget in range(1, len(chunks) + 1)], "limitation": "prefix pruning surrogate; not a production ANN index"}
    if topic == "hybrid-search":
        lexical, vector = lexical_rank("E42", chunks), vector_rank("E42", chunks)
        return {"lexical": ids(lexical), "vector": ids(vector), "fused": ids(rrf([lexical, vector]))}
    if topic == "query-transform":
        query = "reimbursement"
        return {"queries": rewrite(query), "route_e42": route("E42"),
                "before": ids(lexical_rank(query, chunks))[:1],
                "after": ids(rrf([lexical_rank(q, chunks) for q in rewrite(query)]))[:3]}
    if topic == "reranking":
        relevant = next(c for c in chunks if c.source == "e42")
        candidates = [c for c in chunks if c.id != relevant.id] + [relevant, replace(relevant, id="duplicate")]
        grades = {relevant.id: 3}
        reranked = rerank("E42", candidates)
        return {"before_ndcg": ndcg(ids(candidates), grades, 3), "after_ndcg": ndcg(ids(reranked), grades, 3), "ranking": ids(reranked)}
    if topic == "grounded-generation":
        return {"supported": pipeline("refund window"), "unsupported": pipeline("lunar telescope")}
    if topic == "structured-retrieval":
        return {"intent": "refund-days", "acme": structured_lookup("refund-days", "acme"),
                "injected_tenant": structured_lookup("refund-days", "acme' OR 1=1 --")}
    if topic == "rag-quality":
        result = pipeline("refund window")
        return {"authorized_current_sources": sorted({c.source for c in chunks}),
                "citation_valid": valid_citations(result, SOURCES, "acme"), "answer": result}
    if topic == "rag-evals":
        gold = [("E42", "e42"), ("refund window", "refund"), ("lunar telescope", None)]
        rows = []
        for query, expected in gold:
            result = pipeline(query)
            found = [c["citation"]["source"] for c in result["claims"]]
            rows.append({"query": query, "expected_source": expected, "sources": found,
                         "correct": expected in found if expected else result["status"] == "insufficient-evidence",
                         "citation_valid": valid_citations(result, SOURCES, "acme")})
        return {"cases": rows, "correct_rate": sum(r["correct"] for r in rows) / len(rows),
                "limitation": "three synthetic cases are a regression fixture, not a general quality estimate"}
    raise ValueError("unknown topic")


TOPICS = ("document-ingestion", "chunking", "embeddings", "vector-indexes", "hybrid-search", "query-transform",
          "reranking", "grounded-generation", "structured-retrieval", "rag-quality", "rag-evals")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", choices=TOPICS)
    args = parser.parse_args()
    fixture_hash = hashlib.sha256(json.dumps([asdict(s) for s in SOURCES], sort_keys=True).encode()).hexdigest()
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(json.dumps({"topic": args.topic, "fixture_sha256": fixture_hash,
                      "code_sha256": code_hash, "result": experiment(args.topic)}, indent=2))


if __name__ == "__main__":
    main()
