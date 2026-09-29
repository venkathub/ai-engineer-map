# Query rewriting, routing and drift

## Why it matters

Users say "reimbursement" while a policy says "refund." A useful transformation broadens retrieval without silently changing the question or dropping an identifier that determines the answer.

## Mental model

Keep the original query as one retrieval branch and add explicit expansions as additional branches. Route only when the routing contract is testable. The baseline expands reimbursement with refund and classifies E42-style identifiers as runbook queries. The route function is demonstrated separately; the end-to-end pipeline searches its full authorized corpus rather than claiming source routing is already integrated.

## Worked example

~~~python
from labs.rag_path import rewrite, route
assert rewrite("reimbursement") == ["reimbursement", "reimbursement refund"]
assert route("E42 reimbursement") == "runbooks"
assert all("E42" in q for q in rewrite("E42 reimbursement"))
~~~

The original remains unchanged. Expansion adds one token; it never asks a model to replace an opaque code with a guess. With no matching term, the lexical baseline breaks ties by ID and can rank E42 first for reimbursement. The expanded branch brings refund evidence into the fused top three.

## Guided experiment

~~~sh
./run.sh hoe run query-transform
./run.sh hoe verify query-transform
~~~

Compare queries, before, and after in the report. Check both retrieval improvement and preservation of constraints. Add "E42" to the query and verify that every expansion retains it. Inspect a query with no alias: it should produce one branch, avoiding redundant work.

## Production trade-offs and failure cases

More branches increase retrieval cost, context duplication, and the risk of introducing an unrelated interpretation. Keep transformations traceable to the original and cap branch count. Routing to the wrong source can lose all relevant evidence. A learned rewriter also needs tests for negation, dates, IDs, tenant scope, and prompt injection. It must not determine authorization.

## Independent challenge

Integrate explicit source routing with a fallback when the selected source returns no evidence. Test one correct route, one deliberate misroute, and a query spanning policies and runbooks. Compare recall and candidate volume against searching all sources. Preserve the route decision in the experiment output.

## Knowledge check

Why keep the original query? It preserves exact terms and provides a baseline when expansion drifts.

Does a higher fused score prove the rewrite is faithful? No; check constraints and labeled relevance separately.

## References

- [RAG paper](https://arxiv.org/abs/2005.11401)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
