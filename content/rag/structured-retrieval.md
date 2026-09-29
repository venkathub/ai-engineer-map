# Structured retrieval through constrained intents

## Why it matters

A question asking for the current numeric refund window is often better served by a database row than vector similarity. Translating language into unrestricted SQL would give the interpretation layer too much authority.

## Mental model

Choose the retrieval substrate by the required operation: text search for passages, relational queries for filtered rows and aggregation, graph traversal for explicit relationships. The runnable example implements a single allowlisted intent, refund-days, mapped to a trusted SQL template with a bound tenant parameter. It is the safe execution boundary for a text-to-SQL system, not a natural-language parser or graph engine.

## Worked example

~~~python
from labs.rag_path import structured_lookup
assert structured_lookup("refund-days", "acme") == [(30,)]
assert structured_lookup("refund-days", "acme' OR 1=1 --") == []
~~~

A fresh in-memory SQLite fixture is created, then query_only is enabled before retrieval. The hostile-looking tenant remains one bound string; it cannot change the SQL structure. An unknown intent raises ValueError rather than executing the supplied text.

## Guided experiment

~~~sh
./run.sh hoe run structured-retrieval
./run.sh hoe verify structured-retrieval
~~~

The JSON result should contain 30 for acme and an empty list for the injected tenant. Attempt an intent such as DROP TABLE policies and verify rejection. The database fixture is temporary and contains no user data. Run from a Python installation with the standard sqlite3 module.

## Production trade-offs and failure cases

Intent allowlists reduce expressiveness but make permissions and expected query shapes testable. Read-only access alone does not prevent unauthorized reads, expensive joins, or data exfiltration. Add row-level policy, bounded results, query timeouts, and restricted connections where appropriate. In production, tenant identity comes from authentication, never from the model or user-controlled SQL. Parameter binding protects values; it does not authorize arbitrary table names or columns.

## Independent challenge

Add a second intent that returns receipt requirements from a new fixture table. Keep query templates separate from model output. Add tests for unknown intents, missing tenants, and attempts to smuggle SQL through each value. Explain when a graph representation would offer an advantage over your relational schema.

## Knowledge check

Does a parameterized query make any SQL safe? No; it protects bound values, while the chosen query and access policy still need enforcement.

Why not validate generated SQL with a substring check for SELECT? Comments, nested expressions, multiple statements, and sensitive read operations make such checks inadequate.

## References

- [Python sqlite3 parameter binding](https://docs.python.org/3/library/sqlite3.html)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
