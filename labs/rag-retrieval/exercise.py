"""A transparent retrieval baseline using only Python's standard library."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Iterable


TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    source: str


@dataclass(frozen=True)
class SearchResult:
    document: Document
    score: float


def tokenize(text: str) -> list[str]:
    """Return normalized tokens while preserving useful identifiers."""

    return TOKEN_PATTERN.findall(text.lower())


def hashed_vector(text: str, dimensions: int = 64) -> list[float]:
    """Create a deterministic signed bag-of-words vector.

    This is an inspectable teaching representation, not a semantic embedding.
    """

    if dimensions <= 0:
        raise ValueError("dimensions must be positive")

    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    return vector


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    """Return cosine similarity, using 0 for an empty-vector comparison."""

    left_values = list(left)
    right_values = list(right)
    if len(left_values) != len(right_values):
        raise ValueError("vectors must have the same dimensions")

    dot = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def search(query: str, documents: Iterable[Document], limit: int = 3) -> list[SearchResult]:
    """Rank documents against a query with deterministic tie-breaking."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    query_vector = hashed_vector(query)
    scored = [
        SearchResult(document=document, score=cosine_similarity(query_vector, hashed_vector(document.text)))
        for document in documents
    ]
    return sorted(scored, key=lambda result: (-result.score, result.document.id))[:limit]


DOCUMENTS = [
    Document("retry", "Retry transient model errors with exponential backoff and jitter.", "operations.md"),
    Document("auth", "Authorization filters must be applied before returning retrieved evidence.", "security.md"),
    Document("chunk", "Chunk documents along semantic boundaries and preserve source metadata.", "retrieval.md"),
    Document("error-e42", "Error E42 means the embedding index version does not match the query model.", "runbook.md"),
]


def main() -> None:
    query = "retrieval authorization evidence"
    print(f"Query: {query}\n")
    for result in search(query, DOCUMENTS):
        print(f"{result.score: .3f}  {result.document.id:10}  {result.document.text}")


if __name__ == "__main__":
    main()
