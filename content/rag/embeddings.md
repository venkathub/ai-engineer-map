# Embeddings and coordinate compatibility

## Why it matters

A vector comparison is meaningful only when both vectors use compatible coordinates. Mixing representations can silently degrade retrieval even when their dimensions match. This lesson makes that failure visible without downloading a model.

## Mental model

The local encoder counts words against a shared ordered vocabulary. It is a bag-of-words teaching representation, not a learned semantic embedding. Cosine measures the angle between vectors: the dot product divided by the product of their lengths. Scaling a nonzero vector changes its magnitude but not its cosine with the original.

## Worked example

~~~python
from labs.rag_path import encode, cosine
old = encode("refund", ["refund", "receipt"])
new = encode("refund", ["receipt", "refund"])
assert cosine(old, new) == 0
assert cosine(new, new) == 1
~~~

Both vectors describe exactly the same word and both have two dimensions. Their cosine is zero because their coordinate meanings differ. Re-encoding both sides with the new vocabulary restores comparability. Learned embedding migrations have the same compatibility concern even though coordinates are not named words.

## Guided experiment

~~~sh
./run.sh hoe run embeddings
./run.sh hoe verify embeddings
~~~

Expect identical=1, orthogonal=0, scaled=1, and zero=0. The zero result is this implementation's explicit convention because cosine is undefined when either norm is zero. Inspect the dimension-mismatch test and the same-length coordinate-migration test. Add repeated words and observe the effect on direction.

## Production trade-offs and failure cases

A bag-of-words encoder misses synonyms and word order; this is useful for debugging but limits recall. A learned encoder may retrieve paraphrases, yet similarity remains a ranking signal rather than proof of support. Store model identifier, tokenizer/configuration, dimensions, and normalization with an index. During migration, rebuild documents and queries together or maintain two separately evaluated indexes. Never use similarity to decide authorization.

## Independent challenge

Add a versioned vocabulary wrapper that rejects comparisons across vocabulary hashes, including equal-dimensional vectors. Compare raw counts with binary word presence on three queries. Record whether the result changes and explain which failure the representation cannot fix.

## Knowledge check

Does matching dimension imply compatibility? No; the coordinate-migration example is a counterexample.

Does cosine one mean two passages assert the same fact? No; bag-of-words can ignore negation and word order, and learned similarity is not entailment.

## References

- [Sentence Transformers retrieval and reranking](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
