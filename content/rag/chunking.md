# Chunking

## Why it matters

Retrieval returns evidence units, not whole knowledge bases. Chunking decides what those units contain. A chunk that is too small can lose the condition that makes a statement true; one that is too large can bury the useful passage and consume the context budget.

## Mental model

Chunking is an information-boundary decision. Optimize for the smallest unit that remains independently useful for the target questions. Preserve source identity, section hierarchy, ordering, permissions, and offsets so the original evidence can be reconstructed.

## Strategies

- **Fixed windows:** simple and predictable, but may split semantic units.
- **Structure-aware:** follows headings, paragraphs, tables, or code symbols.
- **Recursive:** splits large sections through progressively smaller boundaries.
- **Semantic:** uses model signals to detect topic changes; more complex to debug.
- **Parent-child:** retrieves small units but returns a larger parent context.

## Failure modes

- Answers require facts split across different chunks
- Navigation and boilerplate are embedded repeatedly
- Tables lose headers or row relationships
- Overlap creates duplicate results
- Access-control metadata is dropped during splitting

## Exercise

Extend the fixture in [`labs/rag-retrieval`](../../labs/rag-retrieval/README.md) with a structure-aware splitter. Add a test for a fact that crosses a naïve fixed-window boundary.

## Knowledge check

1. Why is maximum retrieval similarity not a sufficient chunking metric?
2. When does parent-child retrieval help?
3. Which metadata must survive chunking in a multi-tenant product?

## References

- [Unstructured: Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)

Last technically reviewed: 2026-09-29.
