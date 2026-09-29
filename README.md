# AI Engineer Map

An open, source-backed learning environment for production AI engineering. The 2026 curriculum connects 104 concepts across 12 tracks, with explicit prerequisites, outcomes, exercises, primary references, and a technical-review date.

## What is included

- Implemented landing page, roadmap explorer, concept overview, lesson reader, and lab workspace
- A visual, searchable curriculum with 104 dependency-linked concepts
- Track and completion filters
- Local progress tracking (no account required)
- Directed dependency view for the selected topic, with keyboard navigation and text relationship labels
- Machine-readable curriculum metadata
- Coverage from software, data, MLOps, classic ML and transformers through RAG, agents, MCP, A2A, applied ML domains, multimodal/realtime systems, evaluation, safety, fine-tuning, inference, and production
- An exercise brief and evidence checklist for every topic; working baselines for the authored RAG path and scaffolds elsewhere
- A dependency-free retrieval lab with automated tests
- Validation for coverage, references, prerequisites, dependency cycles, and review freshness

## Course content status

The 104-topic map is curriculum coverage, not 104 finished tutorials. Eleven topics now have authored Markdown tutorials wired into the lesson reader, working local experiments, and topic-specific automated verification: ingestion, chunking, embeddings, vector search, hybrid retrieval, query transformation, reranking, grounded answers, structured retrieval, quality/permissions, and RAG evaluation. The remaining 93 lesson pages explicitly show an outline status. Execution profiles currently cover 11 automated topics, 87 guided topics, and 6 setup-ready API/GPU topics.

Start at `lesson.html?id=document-ingestion`. The reader provides prerequisites, worked examples, guided modifications, failure cases, independent challenges, knowledge checks, and primary references. `content/tutorials.json` defines the path, authored files, baseline, and test mapping. The lab loads the real `labs/rag_path.py` baseline and lets you save an edited artifact; save it into your checkout's `labs/` directory before running commands. Browser edits are not automatically persisted or executed.

```bash
./run.sh hoe run document-ingestion
./run.sh hoe verify document-ingestion
./run.sh hoe run rag-evals
./run.sh hoe verify rag-evals
```

These are transparent, deterministic teaching experiments. Bag-of-words vectors are not semantic embeddings, prefix candidate pruning is not a production ANN implementation, and extractive answers are not an LLM. The three-case scorecard is a regression fixture, not a production quality estimate. Independent challenges require learners to extend the working baseline and preserve evidence.

Optional reader regression: `node tests/tutorial-browser.cjs` with the site running and the same existing Playwright/Chrome setup used by the other browser tests.

## Run locally

```bash
./run.sh
```

Open <http://127.0.0.1:8000>. The runner validates the project before serving it. Use `./run.sh --port 9000`, `./run.sh --no-check`, or `./run.sh help` for other modes. The site is browser-native and does not require a package install or build step.

## Run the first lab

```bash
./run.sh lab
./run.sh check
```

## Optional BYO APIs and GPU labs

The core curriculum remains free and dependency-free. Labs that need a hosted model or accelerator use an explicit bring-your-own configuration:

```bash
cp .env.example .env
# Edit .env locally; it is ignored by Git.
./run.sh hoe check --provider openai --gpu jarvislabs
./run.sh hoe check --provider openai --gpu jarvislabs --live
```

The default checker reports only whether required variables and tools exist. `--live` adds read-only JarvisLabs authentication, account-readiness, and exact GPU/region/workload availability queries. Neither mode prints credential values, provisions compute, or makes a model request. GPU provisioning and billable API calls always remain manual. See [`docs/BYO_LLM_AND_GPU.md`](docs/BYO_LLM_AND_GPU.md) for providers, local OpenAI-compatible endpoints, JarvisLabs execution, storage, and shutdown guidance.

Every curriculum topic has a versioned execution profile:

```bash
./run.sh hoe list
./run.sh hoe list --status automated
./run.sh hoe inspect embeddings
./run.sh hoe run embeddings
./run.sh hoe verify embeddings
```

`guided` topics open in the browser lab, `automated` topics have declared shell-free run and verification commands, and `setup-ready` topics expose environment/cost requirements without claiming the topic lab is automated.

Each browser lab loads its execution guide from `curriculum/hoe.json`: status, mode, estimated time and cost, prerequisites, environment requirements, setup/run/verify commands, artifacts, and cleanup. Commands are terminal instructions; the page does not inspect your machine or execute code. For setup-ready GPU topics, the verification command checks the environment only. Credentials stay in your terminal environment or ignored `.env`, never in the browser editor. The browser's Review checklist button does not verify an artifact or mark a topic complete.

Optional lab UI regression: with the site running and an existing Playwright/Chrome installation, run `node tests/lab-browser.cjs` (the same `NODE_PATH`, `CHROME_PATH`, and `BASE_URL` overrides as the roadmap regression apply).

## AI contributor kit

- [`AGENTS.md`](AGENTS.md) — authoritative repository instructions for coding agents
- [`CLAUDE.md`](CLAUDE.md) — Claude-specific entry point
- [`GEMINI.md`](GEMINI.md) — Gemini-specific entry point
- [`.github/copilot-instructions.md`](.github/copilot-instructions.md) — GitHub Copilot context
- [`.ai/README.md`](.ai/README.md) — task recipes and completion checklist
- [`.ai/BRANCHING.md`](.ai/BRANCHING.md) — branch, commit, pull-request, and merge rules
- [`.ai/PHASES.md`](.ai/PHASES.md) — Discover-to-Deliver implementation gates
- [`docs/CLAUDE_PR_REVIEW.md`](docs/CLAUDE_PR_REVIEW.md) — required Claude review, authentication, remediation, and merge gate

All tool-specific guidance defers to `AGENTS.md` so repository rules have one source of truth.

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
The evidence and gap analysis behind the current scope is recorded in [docs/CURRICULUM_AUDIT_2026.md](docs/CURRICULUM_AUDIT_2026.md).

## Curriculum freshness

The curriculum metadata records review on **2026-09-29**; the authored RAG tutorials record their own **2026-09-30** review. A review date on the topic map does not mean a full tutorial exists. Durable concepts are separated from provider-specific details, and each track links to primary specifications or official documentation.

## Pages

On the roadmap, the dependency view shows prerequisites → selected topic → immediate dependents. Tab enters the graph; Left/Right moves between columns, Up/Down moves within a column, and Home/End moves to the first/last graph topic. Enter or Space selects a topic. Tab leaves the graph normally. Selecting a related topic outside the current results clears the filters and announces the change. On narrow screens, the graph scrolls horizontally and keeps keyboard focus in view.

Optional browser regression checks use an existing Node.js, Playwright, and Chrome installation: serve the site with `./run.sh`, then run `node tests/roadmap-browser.cjs`. Set `NODE_PATH` if Playwright is installed outside the repository, `CHROME_PATH` for another Chrome binary, or `BASE_URL` for another local port. The site and `./run.sh check` remain dependency-free.

- `index.html` — curriculum landing page
- `roadmap.html` — search, filtering, dependency state, and concept inspector
- `concept.html?id=mcp` — concept outcomes, prerequisites, proof of understanding, and sources
- `lesson.html?id=mcp` — focused lesson reader with production rules and knowledge checks
- `lab.html?id=vector-indexes` — guided code, acceptance tests, and evidence panel

## License

Code is MIT licensed. Original educational content is licensed under CC BY 4.0. Third-party references retain their respective licenses.
