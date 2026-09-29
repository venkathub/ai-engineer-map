# AI contributor kit

This directory contains task-ready context for AI coding assistants. Repository policy lives in `../AGENTS.md`; tool-specific root files point to that source.

## Before a change

- Read `AGENTS.md`, `README.md`, and `CONTRIBUTING.md`.
- Read `.ai/BRANCHING.md` and `.ai/PHASES.md`; create or reuse a compliant branch.
- Inspect `git status` and the relevant implementation files.
- Decide whether the work changes durable behavior, time-sensitive curriculum claims, or both.
- If claims are current or versioned, collect primary-source evidence first.
- For multi-step work, copy `.ai/templates/IMPLEMENTATION_PLAN.md` to the ignored `.ai/work/implementation-plan.yaml` and keep its current phase accurate.

## Operating contracts

- [`BRANCHING.md`](BRANCHING.md) defines branch, commit, pull-request, and merge formats.
- [`PHASES.md`](PHASES.md) defines phase inputs, actions, artifacts, and exit gates.
- [`config.json`](config.json) exposes the same contracts to tooling.
- [`../docs/BYO_LLM_AND_GPU.md`](../docs/BYO_LLM_AND_GPU.md) defines safe optional API and GPU execution for hands-on exercises.

## Task recipes

### Add a curriculum concept

1. Choose the correct track and unique order.
2. Add the required metadata and valid prerequisite IDs to `curriculum/concepts.json`.
3. Confirm the track references directly support the topic; otherwise add a primary reference.
4. Add or update exercises and tests when the concept needs runnable behavior.
5. Run `./run.sh check` and inspect the concept, lesson, and lab routes.

### Change the interface

1. Reuse existing page shells and tokens.
2. Test the data-driven state: empty search, locked prerequisite, selected concept, completed concept, and progress persistence.
3. Check desktop, narrow mobile, keyboard focus, contrast, and reduced motion.
4. Run `./run.sh check`.

### Review freshness

1. Identify version-sensitive statements and URLs.
2. Verify official specifications, vendor documentation, standards bodies, or original papers.
3. Update only affected claims and references.
4. Advance `reviewedAt` only after the review is complete.
5. State the exact review date and sources in the handoff.

## Completion checklist

- The requested learner or contributor outcome works end to end.
- No duplicated curriculum source was introduced.
- No secrets or personal data were added.
- All prerequisites resolve and remain acyclic.
- Exercises have observable success criteria.
- `./run.sh check` passes.
- UI changes were visually inspected when applicable.
