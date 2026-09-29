# Claude pull-request review gate

Every non-draft pull request is reviewed at its current head commit by the `Claude PR Review` workflow. The workflow publishes one persistent report on the pull request and exposes the `claude-review` required check.

The workflow runs trusted code from the base branch through `pull_request_target`. It fetches the pull-request diff as untrusted text through GitHub's API and sends that text to Anthropic's Messages API. It never checks out or executes pull-request code with a secret present. Claude receives no tools and cannot edit files, execute code, push commits, or merge. A deterministic repository script validates its schema-constrained result. The check passes only when Claude returns `APPROVED` with zero actionable findings.

## Authentication

Configure the Anthropic API key as an encrypted GitHub Actions repository secret:

```bash
gh secret set ANTHROPIC_API_KEY
```

Paste an Anthropic Console API key at the hidden prompt. API usage is billed by Anthropic separately from a Claude web subscription. The review defaults to `claude-sonnet-5`, which supports structured outputs. Override it without changing the workflow by setting the non-secret Actions variable `CLAUDE_REVIEW_MODEL` to another compatible model.

A local Anthropic API key may remain in the ignored `.env` for hands-on exercises, but the workflow reads its own encrypted Actions secret. Never place the key in workflow YAML, pull-request text, logs, or repository variables. Rotate it according to the provider's policy.

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

Rotate the authentication secret with:

```bash
gh secret set ANTHROPIC_API_KEY
```

The workflow deliberately does not use or execute code from the pull-request head. Do not change the trusted-base checkout to the head SHA and do not run downloaded PR artifacts in this privileged workflow.

For public repositories, ensure the repository or organization Actions policy explicitly permits `pull_request_target`. GitHub has announced enforcement of its default blocking policy for that event beginning November 2, 2026; the review gate must fail closed rather than silently bypass review if policy blocks the workflow.

## Official references

- [Anthropic Messages API](https://platform.claude.com/docs/en/api/http/messages)
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [GitHub guidance for secure `pull_request_target` use](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)
