# Freshness, tenancy and retrieval quality

## Why it matters

A perfectly ranked obsolete or unauthorized passage is still a retrieval failure. Quality gates must cover identity, deletion, authorization, and support as well as ranking metrics.

## Mental model

Construct the eligible corpus before scoring. For the authenticated tenant, select each source's newest version and then apply deletion markers. Selecting the newest non-deleted version would resurrect an older document after deletion. The baseline uses integer versions and assumes each tenant/source/version identifies immutable content.

## Worked example

~~~python
from labs.rag_path import corpus, pipeline
chunks = corpus("acme")
assert all(c.tenant == "acme" for c in chunks)
assert "retired" not in {c.source for c in chunks}
assert pipeline("refund window", "unknown")["status"] == "insufficient-evidence"
~~~

The fixture includes another tenant's generous 365-day policy, an obsolete 14-day policy, and a retired 90-day policy. None belongs in acme's current result. The answer should cite the 30-day policy. These deliberately attractive distractors make a missing filter visible.

## Guided experiment

~~~sh
./run.sh hoe run rag-quality
./run.sh hoe verify rag-quality
~~~

Read authorized_current_sources and citation_valid. Add a third-version tombstone for refund and verify that the prior answer's citation becomes invalid. Query with another tenant and with an unknown tenant. Record eligible source IDs before ranking, not only the final answer.

## Production trade-offs and failure cases

Pre-filtering can cost query planning work but preserves the candidate budget for permitted data. Post-filtering can both leak information into intermediate processing and reduce recall. Distributed ingestion introduces update lag; choose and document a freshness contract. Cache entries must include policy context and invalidate on source or permission changes. This local fixture has no authentication server or distributed consistency mechanism.

## Independent challenge

Extend the fixture with group-based access and a permission revocation event. Build a small gold set containing stale, deleted, foreign-tenant, and authorized sources. Test that revocation invalidates previously accepted citations. Document whether your application promises immediate or bounded-delay revocation, and what must change to enforce it.

## Knowledge check

Why choose the latest version before filtering tombstones? Otherwise an old live version can reappear.

Should an unknown tenant fall back to a default tenant? No. The safe result is no eligible evidence.

## References

- [Runnable policy and citation checks](../../labs/rag_path.py)
- [RAG paper for retrieval context](https://arxiv.org/abs/2005.11401)

Technical review: 2026-09-30.
