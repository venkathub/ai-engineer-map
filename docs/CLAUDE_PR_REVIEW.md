# Claude pull-request review gate

Every non-draft pull request is reviewed at its current head commit by the `Claude PR Review` workflow. The workflow publishes a persistent audit report, maintains a separate compact resolvable review thread, and exposes the `claude-review` required check.

The workflow runs trusted code from the base branch through `pull_request_target`. It fetches the pull-request diff as untrusted text and never checks out or executes pull-request code with a secret present. Claude receives only read tools on the subscription route and no tools on the API route; neither route can edit files, execute PR code, push, or merge. Analysis runs with read-only GitHub permissions, its sanitized report crosses jobs as a one-day artifact, and only an isolated publisher job receives `pull-requests: write`. A tested route-decision script requires exactly one valid result. The final `claude-review` job passes only when the selected route returns `APPROVED` with zero actionable findings and report publication succeeds.

## Authentication

The gate tries a Claude Pro/Max subscription OAuth token first, then falls back to a metered Anthropic API key only when the subscription route is missing or fails. Configure both as encrypted GitHub Actions repository secrets:

```bash
claude setup-token
gh secret set CLAUDE_CODE_OAUTH_TOKEN
gh secret set ANTHROPIC_API_KEY
```

Generate the OAuth token from the intended Pro or Max account and paste each credential at its hidden `gh` prompt. Successful subscription reviews avoid metered API usage. If OAuth is unavailable, expired, rejected, or the Claude Code Action fails before producing a structured result, the fallback defaults to `claude-sonnet-5`. API usage is then billed separately from the web subscription. To bound latency and cost, the fallback disables thinking and uses a hard 8,000-output-token ceiling; a truncated response fails closed. Override its model with the non-secret Actions variable `CLAUDE_REVIEW_MODEL` only after confirming that model accepts `thinking: {type: "disabled"}` and structured outputs.

The API fallback accepts at most 300,000 bytes of diff text. Split larger changes into smaller pull requests; exceeding the limit produces a fail-closed review-unavailable report instead of an unbounded model request.

The runtime model check is the source of truth: before every fallback review, the script retrieves the configured ID through Anthropic's `/v1/models/{model_id}` endpoint and fails closed unless Anthropic confirms it. The script currently defaults to `claude-sonnet-5`; an Actions variable overrides it only when non-empty.

Local credentials may remain in the ignored `.env` for hands-on exercises, but the workflow reads encrypted Actions secrets. Never place either value in workflow YAML, pull-request text, logs, or repository variables. Rotate them according to the provider's policy. Each report identifies whether subscription OAuth or the API fallback produced its verdict without exposing credential details.

## Review and merge lifecycle

1. Open or update a non-draft pull request.
2. Wait for `curriculum-and-labs` and `claude-review`.
3. Read the persistent audit comment and its compact inline review thread. When Claude reports `CHANGES_REQUESTED`, address every listed finding ID in the branch.
4. Push the fixes. The audit report and compact thread are updated, and Claude reviews the complete updated diff.
5. Repeat until the current head commit is `APPROVED` with zero findings. The publisher then resolves the compact Claude thread; a later regression reopens it. For a binary/rename-only diff with no commentable line, GitHub receives a compact general PR review instead because its API cannot create a resolvable inline thread without an anchor.
6. Resolve any human review conversations and squash-merge only while all required checks are green and the Claude thread is resolved.

A stale Claude result cannot approve a newer commit because each push starts a new check, cancels the obsolete run, and records the exact reviewed SHA in the report. Authentication errors, malformed output, model failures, or missing credentials fail closed.

## Maintainer operations

Inspect the current state without exposing credentials:

```bash
gh secret list --app actions
gh pr checks PR_NUMBER
gh pr view PR_NUMBER --comments
```

Rotate either authentication secret with:

```bash
gh secret set ANTHROPIC_API_KEY
gh secret set CLAUDE_CODE_OAUTH_TOKEN
```

The workflow deliberately does not use or execute code from the pull-request head. Do not change the trusted-base checkout to the head SHA and do not run downloaded PR artifacts in this privileged workflow.

The pinned Claude Code Action receives a job-scoped `GITHUB_TOKEN` limited by GitHub to `contents: read` and `pull-requests: read`. It can obtain repository/PR context for review, but GitHub denies comment creation, branch updates, merges, workflow-log reads, and other write operations regardless of action behavior. The separate publisher receives `pull-requests: write` but receives neither Anthropic credential and executes no PR-authored code.

Every workflow action is pinned to a full commit SHA. The Claude action remains the most privileged supply-chain dependency because it receives the OAuth secret and network access. Dependabot checks GitHub Actions weekly, but every proposed SHA rotation requires manual source/changelog review before merge. If an upstream pin is suspected of compromise, disable the affected workflow, rotate exposed credentials, inspect recent runs, and adopt a reviewed replacement SHA; a tag update alone is never trusted.

The separate `Claude Model Freshness` workflow runs weekly and on demand. It uses the non-billing model metadata endpoint to confirm the configured/default API model before normal pull-request traffic depends on it.

For public repositories, ensure the repository or organization Actions policy explicitly permits `pull_request_target`. GitHub has announced enforcement of its default blocking policy for that event beginning November 2, 2026; the review gate must fail closed rather than silently bypass review if policy blocks the workflow.

## Official references

- [Anthropic Messages API](https://platform.claude.com/docs/en/api/http/messages)
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Claude Sonnet 5 model and migration behavior](https://platform.claude.com/docs/en/models/sonnet-5/whats-new-sonnet-5)
- [Pinned Claude Code Action source](https://github.com/anthropics/claude-code-action/tree/8ce9314fa9a404564fa7e954cd84f25bcba2b829)
- [GitHub guidance for secure `pull_request_target` use](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)
