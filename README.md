# AI Engineer Map

An open, source-backed learning environment for production AI engineering. The 2026 curriculum connects 76 concepts across 10 tracks, with explicit prerequisites, outcomes, exercises, primary references, and a technical-review date.

## What is included

- A complete landing page, roadmap explorer, concept overview, lesson reader, and lab workspace
- A visual, searchable curriculum with 76 dependency-linked concepts
- Track and completion filters
- Local progress tracking (no account required)
- Machine-readable curriculum metadata
- Coverage from ML and transformer foundations through RAG, agents, MCP, A2A, multimodal/realtime systems, evaluation, safety, fine-tuning, inference, and production
- A dependency-free retrieval lab with automated tests
- Validation for coverage, references, prerequisites, dependency cycles, and review freshness

## Run locally

```bash
python3 -m http.server 8000
```

Open <http://localhost:8000>. The site is browser-native and does not require a package install or build step.

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

## Curriculum freshness

The curriculum was technically reviewed on **2026-09-29**. Durable concepts are separated from provider-specific details, current protocol versions are named where relevant, and each track links to primary specifications or official documentation. “Complete” means complete role coverage for an AI engineer; the repository does not claim that a fast-moving research field can ever be permanently finished.

## Pages

- `index.html` — curriculum landing page
- `roadmap.html` — search, filtering, dependency state, and concept inspector
- `concept.html?id=mcp` — concept outcomes, prerequisites, proof of understanding, and sources
- `lesson.html?id=mcp` — focused lesson reader with production rules and knowledge checks
- `lab.html?id=vector-indexes` — guided code, acceptance tests, and evidence panel

## License

Code is MIT licensed. Original educational content is licensed under CC BY 4.0. Third-party references retain their respective licenses.
