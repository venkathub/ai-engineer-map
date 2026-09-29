# Retrieval fundamentals lab

Build and inspect a small, dependency-free semantic retriever before introducing vector databases or model APIs.

## Objectives

- Trace text from tokenization to a vector representation
- Calculate cosine similarity
- Rank documents for a query
- Observe a case where lexical identity matters more than broad semantic overlap
- Add a refusal threshold rather than always returning an answer

## Run

From the repository root:

```bash
python3 labs/rag-retrieval/exercise.py
python3 -m unittest discover -s tests -v
```

The lab uses a deterministic hashed bag-of-words encoder. It is deliberately not a production embedding model: the point is to expose the retrieval mechanism and its tests without an account, network call, or hidden model behavior.

## Challenges

1. Add bigrams to the encoder and identify a query it improves.
2. Add document metadata and filter candidates before ranking.
3. Implement reciprocal rank fusion over semantic and exact-token rankings.
4. Add a minimum-score policy that returns `insufficient_evidence`.
5. Add a regression fixture where the correct answer spans a chunk boundary.

## Reflection

- Which words dominated the result?
- Which query failed even though a human could find the answer?
- What would a learned embedding improve?
- What could it make harder to debug?
