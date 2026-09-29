# Chunking and provenance

## Why it matters

The answer "refunds require a receipt" is useless if splitting removes the word "require." Chunking determines the evidence units available to retrieval. A larger retrieval score cannot compensate for a boundary that drops the condition needed to answer correctly.

## Mental model

A chunk is a source span plus identity, version, tenant, and offsets. Its text should equal source.text[start:end]. In this lab offsets are Python string character positions, not UTF-8 byte offsets. Fixed windows bound size, overlapping windows repeat context, and paragraph boundaries preserve complete fixture facts. The paragraph splitter is deliberately line-based and does not parse headings, tables, or PDFs.

## Worked example

The fixture begins with "Refunds require the original receipt." A width of 32 characters splits that sentence. Paragraph splitting preserves it. An eight-character overlap still cannot fit a sentence longer than the window.

~~~python
from labs.rag_path import Source, chunk
source = Source("policy", 2, "acme", "Refunds require the original receipt.")
for part in chunk(source, "overlap", width=32, overlap=8):
    assert part.text == source.text[part.start:part.end]
    print(part.start, part.end, part.text)
~~~

The stable chunk ID includes tenant, source, version, and span. It is not safe to reuse it if a producer changes bytes without increasing the version; the ingestion digest must detect that contract violation.

## Guided experiment

~~~sh
./run.sh hoe run chunking
./run.sh hoe verify chunking
~~~

Inspect the fixed, overlap, and paragraph reports. Expected: intact_receipt_fact is false for the first two and true for paragraph splitting. Increase width to 40, then reduce it to 16. Count chunks, repeated characters, and complete answer-bearing facts. Do not choose a policy using chunk count alone.

## Production trade-offs and failure cases

Overlap spends index space and context budget on duplicated text. Paragraph chunks can become too large, so real parsers need size limits and structure-aware subdivision. A table row without its header can be misleading even if offsets are correct. Permission metadata must survive every split; applying authorization only to the original file leaves a dangerous gap downstream.

## Independent challenge

Implement a paragraph-first splitter with a maximum size and a documented fallback for long paragraphs. Add tests for empty text, a long paragraph, non-ASCII text, and complete source reconstruction. Measure boundary failures on at least three new questions. Preserve your policy parameters with the result.

## Knowledge check

Does increasing overlap guarantee intact facts? No; facts longer than a window still cannot fit.

Why retain offsets instead of only chunk text? Offsets permit source verification and precise citations, provided source version and offset convention are also recorded.

## References

- [Unstructured chunking strategies](https://docs.unstructured.io/open-source/core-functionality/chunking)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
