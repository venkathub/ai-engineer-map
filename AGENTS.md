# AI Engineer Map agent guide

This file is the authoritative operating guide for coding agents in this repository. Tool-specific files should point here and add no conflicting rules.

## Mission

Build a free, source-backed, hands-on curriculum for engineers who need to understand and ship production AI systems. Prefer durable engineering mechanisms over framework promotion. A topic is useful only when the learner can demonstrate understanding with observable evidence.

## Architecture

- `index.html`, `roadmap.html`, `concept.html`, `lesson.html`, `lab.html`: browser entry points.
- `assets/app.js`: shared client-side data loading, rendering, routing, progress, and lab behavior.
- `assets/styles.css`: shared design tokens and responsive page system.
- `curriculum/concepts.json`: single source of truth for tracks, concepts, dependencies, exercises, references, and review date.
- `curriculum/hoe.json`: execution profiles and the required one-to-one topic assignment; `hoe.schema.json` documents its versioned shape.
- `content/tutorials.json`: authored lesson/path manifest; unmapped lessons explicitly remain outlines.
- `content/rag/`: Markdown tutorials loaded by the lesson reader through the safe subset renderer in `assets/tutorials.js`.
- `labs/`: runnable, dependency-free learning exercises.
- `scripts/validate_curriculum.py`: schema, coverage, freshness, reference, and graph validation.
- `tests/`: Python unit and curriculum coverage tests.

The application deliberately has no JavaScript build step and no runtime dependency installation. Preserve that constraint unless a documented product requirement justifies changing it.

## Required workflow

1. Read `README.md`, `CONTRIBUTING.md`, `.ai/BRANCHING.md`, `.ai/PHASES.md`, and the files directly affected by the task.
2. Work on a correctly named feature branch; never push directly to `main`.
3. Move through Discover, Specify, Implement, Verify, and Deliver with the evidence required by `.ai/PHASES.md`.
4. Preserve unrelated user changes and avoid broad rewrites.
5. For curriculum claims that may have changed, verify current primary sources before editing.
6. Update `reviewedAt` only when the affected current claims and references were actually reviewed.
7. Run `./run.sh check` before handing off changes.
8. For UI changes, serve with `./run.sh` and inspect desktop and mobile layouts, keyboard focus, and reduced-motion behavior.
9. On a Claude-reviewed pull request, address every open blocking finding and reply in its thread with the changed commit and verification evidence. Implementers must not resolve Claude-owned threads or apply approval labels; only the reviewer publisher does that.

## Curriculum contract

Every concept needs a stable kebab-case ID, track, unique order within its track, difficulty, positive time estimate, concise summary, valid prerequisite IDs, at least two measurable outcomes, and an observable exercise. Dependencies must remain acyclic. Each track must resolve to maintained primary references.

Do not claim the field is permanently complete. “Complete” means broad role coverage as of the repository review date. Separate durable mechanisms from provider-specific or version-specific details.

## UI contract

Keep the established visual language: near-black shell, warm ivory reading surface, acid-lime primary action, editorial hierarchy, monospace technical metadata, restrained corners, and visible focus. All pages must remain usable at 320px width. Escape curriculum strings before inserting them into HTML.

## Safety and quality

- Never place credentials, API keys, personal data, or proprietary prompts in examples or fixtures.
- Read provider credentials only from environment variables or a local ignored `.env`; never expose them to the browser bundle, logs, commits, or screenshots.
- Prefer deterministic local exercises; external paid services must be optional and clearly labeled.
- Do not provision paid API or GPU resources automatically. Show the command, region/GPU choice, persistence behavior, and shutdown or pause step before the learner runs it.
- Keep authorization, irreversible effects, validation, and policy enforcement outside model-generated decisions.
- Prefer official specifications, documentation, original papers, and maintained source repositories.

## Useful commands

```bash
./run.sh                  # validate and serve on 127.0.0.1:8000
./run.sh --port 9000      # choose another port
./run.sh check            # complete local validation
./run.sh lab              # run the retrieval teaching lab
./run.sh hoe list         # list every topic and its execution status
./run.sh hoe inspect ID   # inspect one resolved exercise contract
./run.sh hoe run ID       # run a declared free command or show guided steps
./run.sh hoe check --gpu jarvislabs --live  # read-only auth and availability audit
./run.sh gpu-check        # run the CUDA smoke test on a GPU host
```
