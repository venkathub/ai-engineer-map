# Git branching and change formats

## Protected branch

`main` is always releasable and protected. Do not commit or push directly to it. All changes use a short-lived branch, a pull request, and the required `curriculum-and-labs` and `claude-review` status checks. Force-pushes and deletion of `main` are blocked.

## Branch format

Use lowercase kebab-case:

```text
<type>/<short-purpose>
```

Allowed types:

| Type | Use |
|---|---|
| `feat/` | Product behavior or curriculum capability |
| `fix/` | Defect correction |
| `content/` | Lessons, topics, exercises, or references |
| `research/` | Source review or curriculum audit |
| `docs/` | Documentation only |
| `test/` | Test or validation coverage |
| `chore/` | Tooling, CI, settings, or maintenance |
| `codex/` | Codex-authored implementation branch |

Examples: `content/realtime-voice-lab`, `fix/roadmap-filter-state`, `codex/ai-kit-phases-byo`.

Rules:

- Start from the latest `main`.
- Keep one cohesive outcome per branch.
- Never reuse a merged branch.
- Never include issue titles, usernames, secrets, or dates that reveal private information.
- Delete the remote branch after merge; repository settings do this automatically.

## Commit format

Use Conventional Commits:

```text
<type>(optional-scope): <imperative summary>
```

Allowed commit types: `feat`, `fix`, `content`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`, `revert`.

Examples:

```text
feat(labs): add provider-neutral HOE runner
content(agents): add asynchronous MCP task exercise
fix(roadmap): keep inspector inside active track
```

Keep the subject under 72 characters. Use a body when the reason, migration, evidence, or trade-off is not obvious. Add `BREAKING CHANGE:` in the footer only when existing consumers must change.

## Pull request format

Titles use the same Conventional Commit format. Complete every section of `.github/pull_request_template.md`. A PR must state:

- learner or contributor outcome;
- implementation phase reached;
- files and behavior changed;
- verification commands and visual checks;
- research sources for time-sensitive claims;
- security, cost, compatibility, and rollback considerations.

Prefer squash merge. The squash commit title must preserve the PR's Conventional Commit title.

Every non-draft PR must also follow [`docs/CLAUDE_PR_REVIEW.md`](../docs/CLAUDE_PR_REVIEW.md). Address every blocking Claude finding, reply in each finding thread with the fix commit and verification evidence, push the fix, and wait for Claude to approve the new head commit with no CRITICAL, HIGH, or MEDIUM findings before merging. Do not resolve Claude-owned threads or apply Claude gate labels as an implementer. LOW notes are non-blocking, and a prior approval never applies to a newer commit.
