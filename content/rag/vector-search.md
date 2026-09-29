# Exact search and approximate candidate budgets

## Why it matters

An approximate index trades work for the chance of missing a neighbor. You need a trustworthy exact baseline before deciding whether a faster retrieval method preserves enough useful evidence.

## Mental model

The baseline compares a query against every authorized chunk using cosine and resolves ties by stable ID. Its optional budget restricts scoring to a prefix of the candidate list. This is a deliberately crude approximation surrogate: it illustrates candidate loss, but is not HNSW, IVF, FAISS, or a performance benchmark of those systems.

## Worked example

The E42 document comes after refund and retry chunks in the fixture. A budget of one cannot see it; the full candidate budget can.

~~~python
from labs.rag_path import corpus, vector_rank, recall
chunks = corpus()
gold = [vector_rank("E42", chunks)[0].id]
limited = [c.id for c in vector_rank("E42", chunks, budget=1)]
print(recall(limited, gold, 1))
~~~

Expected recall@1 is zero for that budget and one with all candidates. This measures agreement with exact search, not whether a human would consider the result relevant. Human relevance labels are a separate evaluation target.

## Guided experiment

~~~sh
./run.sh hoe run vector-indexes
./run.sh hoe verify vector-indexes
~~~

Read candidate_budget_sweep. Record the smallest budget that recovers E42. Reverse source ordering and repeat: the prefix surrogate is intentionally order-sensitive, whereas the exact result should remain stable. Explain why those observations rule out treating this experiment as a production latency claim.

## Production trade-offs and failure cases

Exact scoring is simple but scales with corpus size and vector dimension. Approximate systems add index construction, memory, update, and tuning costs. Choose using measured recall, latency, and memory on representative data. Filtering after a small candidate set can leave no authorized results; this path filters current tenant sources before ranking. Always compare like-for-like representations and filters.

## Independent challenge

Replace prefix pruning with a documented coarse bucket rule and measure recall for multiple budgets on at least ten generated vectors with known exact neighbors. Keep the exact implementation as the oracle. Record candidate counts and elapsed time separately; tiny fixture timings are noisy.

## Knowledge check

Can an index have perfect neighbor recall but poor answers? Yes; exact neighbors can still be irrelevant to the task.

Why can reordering this fixture change approximate recall? Prefix pruning selects by position, exposing the limitation of this teaching surrogate.

## References

- [FAISS getting started and exact search](https://github.com/facebookresearch/faiss/wiki/Getting-started)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
