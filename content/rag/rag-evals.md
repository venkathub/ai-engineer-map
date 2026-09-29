# A diagnostic RAG scorecard

## Why it matters

A single answer score cannot tell you whether to fix ingestion, retrieval, reranking, context assembly, or answer support. Evaluation should expose the stage where evidence was lost or corrupted.

## Mental model

Use separate labels for relevant sources, ranking relevance, valid citations, and correct abstention. Recall@k measures the fraction of relevant items retrieved in the first k. nDCG rewards higher-ranked relevant items relative to an ideal ranking. Empty relevance sets need an explicit policy; this implementation returns zero for recall and evaluates unanswerable questions with an abstention check.

## Worked example

~~~python
from labs.rag_path import recall, ndcg, experiment
assert recall(["a", "a"], {"a", "b"}, 2) == 0.5
report = experiment("rag-evals")
assert report["correct_rate"] == 1
~~~

Repeated IDs cannot inflate recall or nDCG in the baseline. The scorecard has three synthetic cases: E42, refund window, and lunar telescope. A correct_rate of one means all three fixture expectations passed. It is not a statistical estimate of production accuracy or proof of semantic faithfulness.

## Guided experiment

~~~sh
./run.sh hoe run rag-evals
./run.sh hoe verify rag-evals
~~~

Inspect expected_source, sources, correct, and citation_valid per case. Remove E42 from the candidate corpus to create a retrieval miss. Separately alter a cited claim to create a provenance failure. Preserve each case's output so the aggregate does not hide different failure causes.

## Production trade-offs and failure cases

A gold set should include ordinary traffic, hard paraphrases, exact identifiers, permission boundaries, stale data, and unanswerable questions. Keep tuning and held-out evaluation queries separate. Human judgments can disagree; record an annotation rubric and adjudication process. Model judges can help at scale but require calibration and checks for bias. This path deliberately uses deterministic assertions and makes no model-judge quality claim.

## Independent challenge

Expand to at least ten labeled cases and add a per-stage scorecard: eligible-source recall, candidate recall, final ranking, citation integrity, and abstention. Include the tenant and source version in each case. Run a controlled broken variant and explain exactly which metric detects it. Save the fixture hash, code revision, commands, outcomes, and a production trade-off.

## Knowledge check

Can perfect citation integrity coexist with a wrong answer? Yes; the cited text can be real but irrelevant or insufficient.

Why retain per-case results? Averages can hide security failures, empty-query mistakes, and regressions in rare query classes.

## References

- [Stanford ranked retrieval evaluation](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)
- [Runnable scorecard](../../labs/rag_path.py)

Technical review: 2026-09-30.
