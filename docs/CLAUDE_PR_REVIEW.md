# Claude pull-request review gate

Every non-draft pull request is reviewed at its current head commit by the `Claude PR Review` workflow. The workflow publishes one persistent report on the pull request and exposes the `claude-review` required check.

Claude receives read-only tools (`Read`, `Glob`, and `Grep`). It cannot edit files, execute pull-request code, push commits, merge, or reveal full model output in the Actions log. A deterministic repository script validates its structured result. The check passes only when Claude returns `APPROVED` with zero actionable findings.

## Authentication: choose one

Configure exactly one GitHub Actions repository secret:

### Anthropic API billing

```bash
gh secret set ANTHROPIC_API_KEY
```

Paste an Anthropic Console API key at the hidden prompt. API usage is billed by Anthropic separately from a Claude web subscription.

### Claude Pro or Max subscription

Install Claude Code locally, authenticate the intended Pro or Max account, and generate the long-lived automation token supported by Claude Code:

```bash
claude setup-token
gh secret set CLAUDE_CODE_OAUTH_TOKEN
```

Paste the generated token at the hidden `gh` prompt. Never put the automation token in `.env`, workflow YAML, pull-request text, logs, or repository variables. A local Anthropic API key may remain in the ignored `.env` for hands-on exercises, but the workflow reads its own encrypted Actions secret. Rotate the selected credential according to the provider's policy.

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

To switch authentication methods, add the replacement secret, verify a review, and then remove the old secret:

```bash
gh secret delete ANTHROPIC_API_KEY
# or: gh secret delete CLAUDE_CODE_OAUTH_TOKEN
```

The action is pinned to an immutable commit. Update it only after reviewing the official action release and rerunning this gate on its own pull request.

## Official references

- [Claude Code Action setup](https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md)
- [Claude Code Action configuration](https://github.com/anthropics/claude-code-action/blob/main/docs/configuration.md)
- [Claude Code Action security guidance](https://github.com/anthropics/claude-code-action/blob/main/base-action/README.md)
