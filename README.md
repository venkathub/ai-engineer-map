# AI Engineer Map

An open, source-backed learning map for production AI engineering. It connects concepts through explicit prerequisites and pairs each topic with an exercise, failure modes, and a next step.

## What is included

- A visual, searchable curriculum graph
- Track and completion filters
- Local progress tracking (no account required)
- Machine-readable curriculum metadata
- A first end-to-end RAG learning slice
- A dependency-free retrieval lab with automated tests
- CI validation for curriculum links and prerequisites

## Run locally

```bash
python3 -m http.server 8000
```

Open <http://localhost:8000>.

## Run the first lab

```bash
python3 labs/rag-retrieval/exercise.py
python3 -m unittest discover -s tests -v
python3 scripts/validate_curriculum.py
```

## Learning philosophy

Every concept should answer:

1. Why does this matter?
2. What must I know first?
3. What is the smallest correct mental model?
4. How is it used in production?
5. What commonly fails?
6. What exercise proves understanding?
7. What should I learn next?

See [PLAN.md](PLAN.md) for the implementation roadmap and [CONTRIBUTING.md](CONTRIBUTING.md) for the content contract.

## Status

The repository is in its first vertical-slice milestone. The RAG path is usable; remaining tracks are mapped and will gain lessons and labs incrementally.

## License

Code is MIT licensed. Original educational content is licensed under CC BY 4.0. Third-party references retain their respective licenses.
