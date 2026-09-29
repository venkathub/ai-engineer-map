# Claude repository instructions

Read and follow [`AGENTS.md`](AGENTS.md) as the authoritative repository guide before making changes.

## Claude-specific working notes

- Begin by inspecting the affected files and `git status`; do not assume a framework or package manager exists.
- Use `curriculum/concepts.json` rather than duplicating curriculum content in page files.
- Keep changes small and evidence-backed. For current AI protocols, models, security guidance, or vendor behavior, verify primary sources before updating claims.
- Use `./run.sh check` as the completion gate. For interface changes, also use `./run.sh` and inspect the rendered result.
- Report the learner-facing outcome, files changed, verification performed, and any content whose freshness still needs review.
