# Product and implementation plan

## Goal

Create a free, open-source curriculum that combines a connected concept map with runnable exercises for engineers building reliable AI products. The curriculum is a learning sequence, not a bookmark directory.

## Audience

- Software engineers moving into AI engineering
- ML engineers moving toward LLM applications and production systems
- Self-directed learners who need sequencing and proof-of-work projects

## Curriculum

1. Software engineering foundations
2. AI and LLM foundations
3. Model APIs and open models
4. Prompt and context engineering
5. Embeddings and retrieval
6. Production RAG
7. Agents, workflows, and MCP
8. Evaluation and testing
9. Safety and security
10. LLMOps, observability, deployment, and scaling
11. Fine-tuning and inference engineering (advanced)
12. Portfolio projects

## Lesson contract

Every completed lesson contains:

- Why it matters
- Explicit prerequisites
- Mental model
- Mechanism and minimal implementation
- Production pattern
- Trade-offs and failure modes
- Security notes where relevant
- Guided exercise and independent challenge
- Knowledge check
- Primary references and technical-review date

## Exercise levels

- **Inspect:** observe tokens, embeddings, retrieval results, traces, or model output.
- **Modify:** complete or improve a partially implemented component.
- **Build:** deliver an independently tested engineering artifact.

## Portfolio projects

1. Provider-neutral model gateway with streaming, retries, fallback, and cost tracking
2. Production RAG system with hybrid retrieval, reranking, citations, and evaluation
3. Recoverable tool-using agent with approval gates and an audit trail
4. AI evaluation platform with regression datasets and experiment comparison
5. Production capstone with authentication, jobs, monitoring, security, and CI/CD

## Milestones

### M1 — Foundation

- Repository, licensing, contribution rules
- Static learning application
- Curriculum schema and validation
- GitHub Actions checks

### M2 — RAG vertical slice

- 12–15 connected concepts
- 8–10 exercises
- Tested production-RAG project
- References and review dates

### M3 — Learning experience

- [x] Search, track filters, dependency state, and local progress
- [x] Concept, lesson, and hands-on lab page designs
- [x] Recommended next concepts, estimated time, and difficulty labels
- [ ] Visual dependency edges and a11y-tested keyboard graph navigation

### M4 — Core tracks

- [x] LLM foundations, transformer mechanics, and model APIs
- [x] Prompt, memory, long-context, and context engineering
- [x] RAG, agents, MCP 2026-07-28, and A2A v0.3
- [x] Multimodal, realtime voice, evaluation, observability, and safety
- [x] PEFT, quantization, serving, distributed inference, and AI operations
- [x] Data/MLOps, applied ML domains, reasoning models, agent skills, asynchronous MCP tasks, system TEVV, agentic security, provenance, compliance, benchmarking, and edge inference

The current role-coverage audit contains 104 concepts across 12 tracks. See `docs/CURRICULUM_AUDIT_2026.md` for scope, gaps corrected, hands-on evidence rules, and primary sources.

### M5 — Hands-on execution

- [x] Versioned execution schema and one-to-one profile assignment for all concepts
- [x] Unified list, inspect, run, verify, and environment-check CLI
- [x] Explicit guided, automated, and setup-ready states
- [x] Shell-free command validation and paid API/GPU acknowledgement gate
- [ ] Automate the remaining guided exercises track by track
- [ ] Surface execution readiness, cost, artifacts, and cleanup in the browser lab

### M6 — Portfolio and community

- Five end-to-end projects with review rubrics
- Contributor preview workflow
- Versioned curriculum releases
- Public backlog and discussion templates

## MVP acceptance criteria

- A learner can follow one coherent RAG path from documents to evaluated answers.
- Every published concept passes metadata and dependency validation.
- Every exercise runs without a paid API unless explicitly marked optional.
- Progress works locally without an account.
- The application remains usable on mobile and with keyboard navigation.

## Technical approach

The MVP deliberately uses browser-native HTML, CSS, and JavaScript plus Python standard-library validation. This minimizes setup and makes GitHub Pages deployment straightforward. A framework migration should happen only when authoring, routing, or interactive-graph requirements justify the added build system.

## Content quality rules

- Prefer primary documentation and original papers.
- Separate durable concepts from framework-specific adapters.
- Show failure paths, not only happy-path demos.
- Never require a paid model for a core exercise.
- Record `reviewedAt` for every published lesson.
- Do not publish a concept as complete without a runnable proof-of-understanding task.
