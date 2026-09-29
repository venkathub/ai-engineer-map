# Claude repository instructions

Read and follow [`AGENTS.md`](AGENTS.md) as the authoritative repository guide before making changes.

## Claude-specific working notes

- Begin by inspecting the affected files and `git status`; do not assume a framework or package manager exists.
- Follow `.ai/BRANCHING.md` and complete the Discover, Specify, Implement, Verify, and Deliver gates in `.ai/PHASES.md`.
- Use `curriculum/concepts.json` rather than duplicating curriculum content in page files.
- Keep changes small and evidence-backed. For current AI protocols, models, security guidance, or vendor behavior, verify primary sources before updating claims.
- Use `./run.sh check` as the completion gate. For interface changes, also use `./run.sh` and inspect the rendered result.
- For optional model/GPU exercises, follow `docs/BYO_LLM_AND_GPU.md`; keep credentials terminal-only and never provision paid compute implicitly.
- Report the learner-facing outcome, files changed, verification performed, and any content whose freshness still needs review.
- For automated pull-request review, report only actionable defects introduced by the current diff. Approve only the exact current head commit when no findings remain; follow `docs/CLAUDE_PR_REVIEW.md`.
