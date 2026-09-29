# Grounded answers, citations and abstention

## Why it matters

An answer needs a narrower contract than sounding plausible. A learner should be able to locate the source span behind a claim, detect unsupported output, and explain whether failure occurred in retrieval or answer construction.

## Mental model

This path uses an extractive answer baseline. It copies the best authorized current chunk, attaches its source/version/offsets, and abstains when query-token coverage is below 0.5. There is no LLM call. Token overlap is only a teaching heuristic: it cannot establish semantic support, handle all paraphrases, or resolve conflicting statements.

## Worked example

~~~python
from labs.rag_path import pipeline, valid_citations, SOURCES
result = pipeline("refund window")
assert "30 days" in result["claims"][0]["text"]
assert valid_citations(result, SOURCES, "acme")
assert pipeline("lunar telescope")["status"] == "insufficient-evidence"
~~~

The refund answer cites version two rather than the obsolete 14-day text. Citation validation rechecks tenant, current version, bounds, and exact source substring. A real source does not make an altered claim valid: changing 30 to 99 must fail validation.

## Guided experiment

~~~sh
./run.sh hoe run grounded-generation
./run.sh hoe verify grounded-generation
~~~

Inspect supported and unsupported outputs. Change a cited claim and then an offset; confirm both are rejected. Raise min_coverage in answer and compare abstention. Try a paraphrase lacking shared words to observe a false abstention. Keep retrieval IDs so you can separate missed evidence from an answer threshold problem.

## Production trade-offs and failure cases

Exact extraction is auditable but not fluent synthesis. If you add a generator, retain source identity, attribute each claim, and evaluate support rather than checking only that a citation exists. Retrieved instructions are untrusted data. The deterministic baseline never follows instructions inside evidence; a model-based extension needs a separate policy boundary. A high score must never override authorization or justify an unsupported answer.

## Independent challenge

Support a two-part question requiring two distinct source spans. Return one citation per extracted claim and reject any fabricated or stale citation. Add tests for an empty corpus, contradictory source versions, and an answer containing an uncited extra sentence. Explain which cases require human review.

## Knowledge check

Does a valid citation prove relevance? No. This validator proves exact source provenance, not that the passage answers the question.

Why is abstention useful? It exposes insufficient evidence instead of converting uncertainty into a confident unsupported answer.

## References

- [Retrieval-Augmented Generation paper](https://arxiv.org/abs/2005.11401)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
