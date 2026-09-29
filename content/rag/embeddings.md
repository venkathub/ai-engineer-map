# Embeddings

## Why they matter

Embeddings map an input to a fixed-width vector. In retrieval systems, nearby vectors are treated as candidates for semantic relevance. The vector is useful evidence for ranking; it is not a human-readable explanation and does not prove that two texts make the same claim.

## Mental model

An embedding model is a learned coordinate system. The coordinates have meaning only in relation to other outputs from the same compatible model and configuration. Changing models is therefore a data migration, not a harmless dependency update.

Cosine similarity compares direction:

```text
cos(a, b) = (a · b) / (||a|| ||b||)
```

## Production considerations

- Store the embedding model and version beside every vector.
- Normalize consistently if the selected similarity function expects it.
- Re-embed the comparison corpus when moving to an incompatible model.
- Evaluate retrieval on representative queries; geometric closeness is not product relevance.
- Never use similarity as an authorization decision.

## Failure modes

- Mixed embedding versions in one index
- Truncated or poorly parsed source text
- Domain language missing from the evaluation set
- Nearly identical boilerplate dominating results
- Treating a similarity score as calibrated confidence

## Exercise

Complete the cosine-similarity implementation in [`labs/rag-retrieval`](../../labs/rag-retrieval/README.md), then explain why the highest-scoring result can still be unsuitable evidence.

## Knowledge check

1. Why must a model change be treated as a migration?
2. What does cosine similarity ignore?
3. Which product metric would show whether embeddings help retrieval?

## References

- [Sentence Transformers: Semantic Textual Similarity](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html)
- [pgvector distance functions](https://github.com/pgvector/pgvector)

Last technically reviewed: 2026-09-29.
