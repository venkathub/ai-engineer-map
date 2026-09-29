# Claude pull-request review gate

Every non-draft pull request is reviewed at its current head commit by the `Claude PR Review` workflow. The workflow publishes one persistent report on the pull request and exposes the `claude-review` required check.

The workflow runs trusted code from the base branch through `pull_request_target`. It fetches the pull-request diff as untrusted text through GitHub's API and sends that text to Anthropic's Messages API. It never checks out or executes pull-request code with a secret present. Claude receives no tools and cannot edit files, execute code, push commits, or merge. A deterministic repository script validates its schema-constrained result. The check passes only when Claude returns `APPROVED` with zero actionable findings.

## Authentication

The gate tries a Claude Pro/Max subscription OAuth token first, then falls back to a metered Anthropic API key only when the subscription route is missing or fails. Configure both as encrypted GitHub Actions repository secrets:

```bash
claude setup-token
gh secret set CLAUDE_CODE_OAUTH_TOKEN
gh secret set ANTHROPIC_API_KEY
```

Generate the OAuth token from the intended Pro or Max account and paste each credential at its hidden `gh` prompt. Successful subscription reviews avoid metered API usage. If OAuth is unavailable, expired, rejected, or the Claude Code Action fails before producing a structured result, the fallback defaults to `claude-sonnet-5`. API usage is then billed separately from the web subscription. The fallback uses adaptive thinking at high effort with a hard 32,000-output-token ceiling; a truncated response fails closed. Override its model with the non-secret Actions variable `CLAUDE_REVIEW_MODEL`, then verify its thinking configuration remains compatible.

Local credentials may remain in the ignored `.env` for hands-on exercises, but the workflow reads encrypted Actions secrets. Never place either value in workflow YAML, pull-request text, logs, or repository variables. Rotate them according to the provider's policy. Each report identifies whether subscription OAuth or the API fallback produced its verdict without exposing credential details.

## Review and merge lifecycle

1. Open or update a non-draft pull request.
2. Wait for `curriculum-and-labs` and `claude-review`.
3. When Claude reports `CHANGES_REQUESTED`, address every listed finding ID in the branch.
4. Push the fixes. The previous report is replaced, and Claude reviews the complete updated diff.
5. Repeat until the current head commit is `APPROVED` with zero findings.
6. Resolve any human review conversations and squash-merge only while all required checks are green.

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

For public repositories, ensure the repository or organization Actions policy explicitly permits `pull_request_target`. GitHub has announced enforcement of its default blocking policy for that event beginning November 2, 2026; the review gate must fail closed rather than silently bypass review if policy blocks the workflow.

## Official references

- [Anthropic Messages API](https://platform.claude.com/docs/en/api/http/messages)
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [GitHub guidance for secure `pull_request_target` use](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)
