# Grounded answer pipeline

## Why it matters

A RAG system should make a narrower promise than “the model knows the documents.” It retrieves candidate evidence, constructs a bounded context, produces an answer, and exposes where supported claims came from.

## Pipeline

```text
Question → query processing → retrieval → reranking → context assembly
         → answer generation → citation verification → response
```

Log each boundary separately. Retrieval failure and generation failure require different fixes.

## Production contract

- Answer only from supplied evidence for knowledge-bound tasks.
- Represent “insufficient evidence” as a valid outcome.
- Link citations to immutable source identity and offsets.
- Preserve tenant and document permissions throughout retrieval.
- Measure retrieval recall before tuning answer style.
- Evaluate claim support rather than merely checking that citations exist.

## Failure modes

- Correct source exists but is never retrieved
- Correct chunk is retrieved but omitted from context
- Answer contradicts the evidence
- Citation points to a relevant document but not the supporting passage
- Prompt injection in a retrieved document changes system behavior

## Independent challenge

Build an answer function over the local retrieval lab. It must return selected evidence IDs and explicitly decline when no result crosses a justified threshold. Add tests for both paths.

## References

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)

Last technically reviewed: 2026-09-29.
