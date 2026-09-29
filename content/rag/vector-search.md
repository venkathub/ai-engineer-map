# Vector and hybrid search

## Why it matters

Semantic retrieval finds related language even when exact words differ. Lexical retrieval is often stronger for identifiers, error codes, names, and precise phrases. Production systems commonly need both.

## Minimal mechanism

1. Encode the query with the compatible embedding model.
2. Compare it with indexed vectors.
3. Retrieve the top candidates.
4. Optionally retrieve a lexical candidate set.
5. Fuse or rerank candidates.
6. Apply authorization and metadata filters in the trusted application layer.

Reciprocal rank fusion is a simple way to combine rankings without pretending scores from different systems are directly comparable:

```text
RRF(d) = Σ 1 / (k + rank_i(d))
```

## Failure modes

- Comparing raw lexical and vector scores as if calibrated equally
- Filtering after retrieval and leaving too few authorized results
- Evaluating only easy paraphrase queries
- Missing exact identifiers that semantic search smooths away
- Returning redundant chunks instead of diverse evidence

## Exercise

Implement cosine similarity and ranked retrieval in [`labs/rag-retrieval`](../../labs/rag-retrieval/README.md). Add one lexical query where exact matching should beat semantic similarity.

## References

- [pgvector](https://github.com/pgvector/pgvector)
- [Elasticsearch: Reciprocal rank fusion](https://www.elastic.co/guide/en/elasticsearch/reference/current/rrf.html)

Last technically reviewed: 2026-09-29.
