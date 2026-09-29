# Ingestion, parsing and source identity

## Why it matters

A retrieval system cannot repair a missing page, an obsolete policy, or a document assigned to the wrong tenant. Ingestion establishes the identity and extraction status that every downstream stage must retain. This lesson builds a resumable manifest over a synthetic support knowledge base; it does not implement PDF parsing or OCR.

## Mental model

Treat ingestion as a versioned transaction: identify the source, extract text, record its digest and status, then publish only usable records. The key in this lab is tenant/source/version. A content digest detects changes even if an upstream producer incorrectly reuses a version. An empty extraction is a parse failure unless the record is an explicit deletion.

## Worked example

The corpus contains an old 14-day refund policy, a new 30-day policy, another tenant's contract, and a deletion marker. Inspect SOURCES and ingest in the baseline.

~~~python
from labs.rag_path import Source, ingest
source = Source("manual", 1, "acme", "Refunds require a receipt.")
first = ingest([source])
second = ingest([source], first)
assert second["acme/manual/1"]["reused"]
~~~

The first manifest reports reused=false; a second pass over unchanged inputs reports true. An empty non-deleted source reports parse-error. This manifest is in memory: a production worker would persist it atomically and acknowledge its queue message only after commit.

## Guided experiment

Run the commands from the repository root:

~~~sh
./run.sh hoe run document-ingestion
./run.sh hoe verify document-ingestion
~~~

Compare first and resumed entries. Change one source's text without changing its version and predict whether it is reusable. Then create a source with the same ID in another tenant. Confirm both manifest keys exist. Finally, simulate an OCR failure by supplying empty text and confirm it is quarantined rather than indexed.

## Production trade-offs and failure cases

Digest calculation costs I/O but catches silent input changes. Version-only caching is cheaper and relies on a stronger source contract. Persist the parser version and extraction options alongside content digests in a production manifest; the small baseline does not track those. Preserve page or region coordinates for OCR, record partial extraction explicitly, and distinguish a failed download from an authorized deletion. Never derive tenant identity from a document's own text.

## Independent challenge

Add a parser-version field to the manifest reuse contract. Write a test showing that changing parser version invalidates reuse even when bytes match, and a test showing that a failed parse is retried. Save the before/after JSON, test output, and a note explaining the cost of reprocessing.

## Knowledge check

Why is a source URL insufficient identity? A URL can serve new bytes, move between owners, or return different content under authentication.

Should an empty extraction delete a previously indexed document? No. Only an explicit source deletion event should trigger removal; extraction failure requires retry or quarantine.

## References

- [Unstructured chunking and document elements](https://docs.unstructured.io/open-source/core-functionality/chunking)
- [Runnable baseline](../../labs/rag_path.py)

Technical review: 2026-09-30.
