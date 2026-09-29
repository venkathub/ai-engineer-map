# Phase-gated AI implementation workflow

Every implementation follows five explicit phases. An agent may combine small phases in one work session, but it must satisfy each exit gate and report the final phase reached.

## Phase 0 — Discover

Goal: establish the real repository and user context.

Required work:

- read `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, and affected files;
- inspect Git status and preserve unrelated changes;
- identify current behavior, constraints, security impact, and whether web research is required;
- record assumptions and unresolved decisions.

Exit gate: problem and scope can be stated without guessing about the codebase.

## Phase 1 — Specify

Goal: define an acceptance contract before implementation.

Required work:

- write the learner or product outcome;
- list in-scope and out-of-scope work;
- identify files, data/schema changes, risks, and rollback;
- define tests, visual checks, and evidence;
- select local, BYO API, or GPU execution mode for every affected HOE.

Exit gate: the plan matches `.ai/templates/IMPLEMENTATION_PLAN.md` and its acceptance checks are observable.

## Phase 2 — Implement

Goal: make the smallest cohesive change that satisfies the specification.

Required work:

- work on a branch that follows `.ai/BRANCHING.md`;
- keep curriculum data in `curriculum/concepts.json` and shared behavior in existing modules;
- keep secrets out of source, browser JavaScript, logs, fixtures, and Git history;
- add or update tests with the behavior.

Exit gate: implementation is complete, reviewable, and contains no known placeholder in the requested path.

## Phase 3 — Verify

Goal: gather evidence, not confidence language.

Required work:

- run `./run.sh check`;
- run the relevant HOE locally, with mocked/BYO API mode, or on an explicitly authorized GPU;
- inspect UI changes in a served browser when applicable;
- verify negative paths, secret handling, cost controls, and cleanup behavior;
- retain only non-sensitive evidence under `outputs/` locally; it is ignored by Git.

Exit gate: acceptance checks pass or every failure is documented with exact evidence.

## Phase 4 — Deliver

Goal: make the change safely consumable.

Required work:

- review the diff and confirm no secret or unrelated change is present;
- use Conventional Commits and the PR template;
- wait for required checks, resolve review threads, and squash merge;
- report the outcome, tests, sources, risks, and follow-up work;
- pause or delete paid GPU compute and report retained storage.

Exit gate: protected `main` is green and the branch is deleted after merge.

## Machine-readable phase record

For multi-turn or substantial work, create `.ai/work/implementation-plan.yaml` from the template. `.ai/work/` is working state and should not be committed unless the user explicitly requests the plan as a project artifact.
