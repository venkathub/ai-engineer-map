# Lexical retrieval and reciprocal rank fusion

## Why it matters

A support query containing E42 should preserve that exact identifier. A semantic system may be useful for paraphrases, while lexical search offers a simple exact-token baseline. Combining two rankings requires a rule that does not assume their raw scores share a scale.

## Mental model

Reciprocal rank fusion adds 1/(constant + rank) for each list containing a candidate. Ranks begin at one. The baseline uses constant=60, treats each retriever equally, counts a document at most once per list, and breaks ties by ID. Its two retrievers are token overlap and bag-of-words cosine, so neither demonstrates learned semantic recall.

## Worked example

For rankings [A, B] and [B, C], B receives 1/62 + 1/61; A receives only 1/61. B wins because two lists support it. Multiplying one retriever's raw scores by 100 would not change fusion because fusion uses positions.

~~~python
from labs.rag_path import corpus, rrf
a, b, c = corpus()[:3]
assert rrf([[a, b], [b, c]])[0] == b
~~~

## Guided experiment

~~~sh
./run.sh hoe run hybrid-search
./run.sh hoe verify hybrid-search
~~~

Inspect lexical, vector, and fused IDs for E42. Confirm its source ranks first. Change the query to "refund receipt" and compare rankings. Try constants of one and sixty. Add a duplicate result to one list and verify it cannot obtain an extra vote.

## Production trade-offs and failure cases

Fusion improves candidate combination only when its inputs bring useful information. Highly correlated rankers can reinforce the same mistakes. RRF scores are not probabilities and should not be used as calibrated abstention thresholds. Truncated candidate lists affect fusion; measure their depth. Authorization must be applied consistently to each retriever, not only the final combined response.

## Independent challenge

Add a hand-labeled query where exact identifiers matter and another where synonyms matter. Use a manually specified synonym expansion as a controlled experiment, not a claim of semantic modeling. Compare lexical-only, vector-only, and fused recall@k. Save the ranked IDs and parameters with your explanation.

## Knowledge check

Why avoid adding raw lexical and vector scores? Their scales and distributions may differ.

Can fusion retrieve a document missing from every input list? No. Candidate recall is the upper bound.

## References

- [Elasticsearch reciprocal rank fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
