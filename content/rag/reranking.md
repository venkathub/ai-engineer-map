# Reranking and evidence diversity

## Why it matters

Retrieval can find the right source but place it below irrelevant or repeated passages. A smaller reranking stage can improve which candidates reach the answer context, provided the relevant evidence was retrieved in the first place.

## Mental model

Separate candidate recall from final ordering. The lab reranker scores exact query-token coverage and removes duplicate normalized text. It is a transparent local heuristic, not a trained cross-encoder. nDCG compares discounted relevance gains against the ideal ordering; moving a highly relevant result toward the top should increase it.

## Worked example

The fixture deliberately puts the E42 answer late and appends a duplicate with another ID. The reranker brings the original answer first and suppresses the repeated text.

~~~python
from labs.rag_path import experiment
report = experiment("reranking")
assert report["after_ndcg"] == 1
assert report["after_ndcg"] > report["before_ndcg"]
~~~

The grade for the relevant source is three. A perfect score on this manufactured example proves a narrow regression contract; it does not establish usefulness across real users or domains.

## Guided experiment

~~~sh
./run.sh hoe run reranking
./run.sh hoe verify reranking
~~~

Inspect before_ndcg, after_ndcg, and the resulting IDs. Remove the relevant source before reranking and observe that it cannot be recovered. Add a near-duplicate differing by a single token: the exact normalization rule no longer removes it. Record that limitation.

## Production trade-offs and failure cases

Neural rerankers jointly score query and candidate text and can cost more than first-stage retrieval. Restricting candidate count bounds cost but can cap achievable quality. Exact text deduplication is cheap, yet semantically redundant passages may remain. Deduplicating solely by source can remove complementary facts. Diversity should preserve distinct evidence needed to answer the question.

## Independent challenge

Add a token-Jaccard duplicate threshold, then evaluate a pair of near-duplicates and two similar passages with different refund deadlines. Prove that your policy preserves conflicting evidence instead of silently dropping it. Compare nDCG and the number of unique source spans, and explain the trade-off.

## Knowledge check

Can reranking fix failed ingestion? No; it can only reorder available candidates.

Is duplicate removal always an improvement? No; superficially similar passages may contain materially different conditions or versions.

## References

- [Sentence Transformers retrieve and rerank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
- [Ranked retrieval evaluation](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
