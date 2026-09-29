# Claude pull-request review gate

Every non-draft pull request is reviewed at its current head commit by the `Claude PR Review` workflow. The workflow follows the Kaasu reviewer-daemon pattern: it opens a standalone pending-state comment immediately, waits for validation on the exact head, publishes one unresolved inline thread per blocking finding, records each compact round summary once as a native GitHub review, and exposes the `claude-review` required check. Lifecycle state is never attached to an arbitrary diff line; inline threads are reserved for actionable findings.

The workflow runs trusted code from the base branch through `pull_request_target`. It fetches the pull-request diff as untrusted text and never checks out or executes pull-request code with a secret present. Claude receives only read tools on the subscription route and no tools on the API route; neither route can edit files, execute PR code, push, merge, label, or resolve threads. Analysis runs with read-only GitHub permissions. A validated machine-readable verdict and a sanitized report cross jobs as one-day artifacts; only the isolated publisher receives `issues: write` and `pull-requests: write`. A tested route-decision script requires exactly one valid result. The final `claude-review` job passes only when the selected route returns `APPROVED` with zero CRITICAL, HIGH, or MEDIUM findings and publication succeeds; LOW notes are non-blocking.

Pull requests expose four purposeful checks: `curriculum-and-labs`, `claude-prepare`, `claude-analyze`, and the required `claude-review`. Preparation combines exact-head validation with stale-label revocation and pending-state publication. Analysis remains a separate read-only job because it receives an Anthropic credential. The final job combines publication with gate enforcement and receives a short-lived, narrowly scoped App token but no Anthropic credential. Combining these three Claude jobs further would give one job both provider secrets and repository write access. Validation runs once for a PR head; branch `push` validation is limited to `main`, avoiding duplicate checks for the same pull-request commit. Feature branches without an open PR use `./run.sh check` locally and begin CI validation when their pull request opens.

## Dedicated review bot

Review state is published through a repository-installed GitHub App, so GitHub attributes comments, reviews, labels, and thread resolution to `<app-slug>[bot]` instead of a maintainer. Register an app named for the reviewer (for example, `AI Engineer Map Claude Review`) with webhooks disabled and only these repository permissions:

- Issues: Read and write
- Pull requests: Read and write
- Metadata: Read-only (automatically granted by GitHub)

Install it only on `venkathub/ai-engineer-map`. Store its client ID as the Actions variable `CLAUDE_REVIEW_APP_CLIENT_ID`, and store the complete generated PEM private key as the encrypted Actions secret `CLAUDE_REVIEW_APP_PRIVATE_KEY`. Do not store the private key in `.env`, the repository, workflow text, logs, artifacts, or a pull-request comment.

The `claude-prepare` and `claude-review` jobs use the GitHub-owned `actions/create-github-app-token` action pinned to the verified `v3.2.0` commit. Each job requests a short-lived, current-repository installation token narrowed to Issues and Pull requests write access; the action revokes it when the job finishes. The credential-bearing `claude-analyze` job never receives the App private key, installation token, or repository write scope. Missing or invalid App configuration fails closed before any review-state mutation.

Publisher failures emit a structured `Claude review publisher` annotation in the affected job. The message distinguishes policy holds such as `needs-human` from API or inventory failures without exposing response bodies or credentials; all such failures keep the required gate red and retry on the next authorized event.

Configure the repository after installing the App:

```bash
gh variable set CLAUDE_REVIEW_APP_CLIENT_ID --body 'Iv1.example'
gh secret set CLAUDE_REVIEW_APP_PRIVATE_KEY < path/to/downloaded-app.private-key.pem
```

GitHub does not allow changing the author of existing comments. Bootstrap comments created with a maintainer token remain attributed to that maintainer; subsequent workflow publications use the App bot identity.

## Authentication

The gate tries a Claude Pro/Max subscription OAuth token first, then falls back to a metered Anthropic API key only when the subscription route is missing or fails. Configure both as encrypted GitHub Actions repository secrets:

```bash
claude setup-token
gh secret set CLAUDE_CODE_OAUTH_TOKEN
gh secret set ANTHROPIC_API_KEY
```

Generate the OAuth token from the intended Pro or Max account and paste each credential at its hidden `gh` prompt. Successful subscription reviews avoid metered API usage. If OAuth is unavailable, expired, rejected, or the Claude Code Action fails before producing a structured result, the fallback defaults to the dated model ID `claude-sonnet-4-5-20250929`. API usage is then billed separately from the web subscription. To bound latency and cost, the fallback disables thinking and uses a hard 8,000-output-token ceiling; a truncated response fails closed. The 100-finding validation limit is a defensive input ceiling, not a promise that 100 maximally verbose findings fit in 8,000 tokens: the model should consolidate related defects, and any response that reaches the token ceiling is rejected instead of partially published. Override its model with the non-secret Actions variable `CLAUDE_REVIEW_MODEL` only after confirming that model accepts `thinking: {type: "disabled"}` and structured outputs.

The API fallback accepts at most 300,000 bytes of diff text. Split larger changes into smaller pull requests; exceeding the limit produces a fail-closed review-unavailable report instead of an unbounded model request.

The runtime model check is the source of truth: before every fallback review, the script retrieves the configured ID through Anthropic's `/v1/models/{model_id}` endpoint and fails closed unless Anthropic confirms both the exact ID and a model record. The script currently defaults to the dated ID `claude-sonnet-4-5-20250929`; it is reconfirmed on every fallback invocation, and the workflow log is the auditable source for the latest confirmation timestamp. An Actions variable overrides it only when non-empty. No static pre-merge verification timestamp is treated as authoritative.

Model verification makes one bounded provider request and deliberately does not retry. A transient timeout or provider 5xx therefore fails the freshness workflow or PR review closed; a later scheduled run or a maintainer-triggered rerun performs the next attempt. This avoids multiplying API traffic inside a security gate while keeping temporary provider failures visible.

Local credentials may remain in the ignored `.env` for hands-on exercises, but the workflow reads encrypted Actions secrets. Never place either value in workflow YAML, pull-request text, logs, or repository variables. Rotate them according to the provider's policy. Each report identifies whether subscription OAuth or the API fallback produced its verdict without exposing credential details.

## Review and merge lifecycle

1. Open or update a non-draft pull request.
2. A read-only job asks GitHub whether the event SHA is still the PR's current head. Only after that succeeds does the separately write-scoped job remove any `claude:approved` label as its first mutation, then create or update the standalone pending-state comment. The publisher repeats the same head check as its first API operation before every mutation. Claude then waits until `curriculum-and-labs` succeeds for that same head SHA, so a stale green result never starts review.
3. Read the persistent audit comment and the single compact round summary in GitHub's Reviews timeline. Each current CRITICAL, HIGH, or MEDIUM finding has its own unresolved review thread. On every new round, the reviewer resolves prior-round or cleared finding threads, updates/reopens matching current threads, and creates only missing current blockers. LOW findings appear only as non-blocking notes in the native review. The native review is a `COMMENT` event because the workflow token does not impersonate a human approver; the required exact-head check remains the approval authority. Legacy Conversation round comments remain as historical records but are still considered when assigning the next round number; new runs do not create them.
4. Address every blocking thread, then reply in that same thread with the fix commit and verification evidence. Do not resolve the thread; it belongs to the Claude reviewer.
5. Push the fixes. Approval is revoked and the pending-state comment is updated before validation or review of the new head begins.
6. Repeat until the current head commit is `APPROVED` with no blocking findings. The publisher then updates the pending-state comment body to approved, resolves all Claude-owned finding threads, adds `claude:approved`, and removes both `claude:changes-requested` and `needs-human`; LOW notes may remain in the round summary. After two unsuccessful rounds it keeps `claude:changes-requested` and adds `needs-human`, while automatic review of the unchanged head remains paused.
7. Human escalation: a maintainer reads every open thread and manually starts Codex (or performs the work directly). Codex fixes every blocker, runs the required tests, commits, and pushes a new revision to the same PR. That `synchronize` event is the human-authorized handoff and starts one forced Claude re-review; no manual label removal is required. `needs-human` remains in place as a merge hold while the review runs. If blockers remain, the publisher retains `claude:changes-requested` and `needs-human`. If the exact head is approved, it removes both and adds `claude:approved`. Removing a label by hand never starts a review. A trusted local operator may equivalently set process-local `CLAUDE_HUMAN_REREVIEW=true` for one publisher invocation. The required check—not labels alone—remains the authoritative merge gate.
8. Resolve any separate human review conversations and squash-merge only while all required checks are green and every blocking conversation is resolved.

GitHub requires an inline diff anchor to create a resolvable conversation. A path-only finding is anchored to the first changed line in that same file; it is never attached to an unrelated file. For binary, rename-only, or otherwise unanchorable changes, the publisher falls back to a general PR review while the required `claude-review` check remains the fail-closed merge gate.

A stale Claude result cannot approve a newer commit because each push validates the event head and then removes `claude:approved` as the first write, before comment or thread inventory, updates the pending-state comment, starts a new check, cancels the obsolete run, and records the exact reviewed SHA in both artifacts. Authentication errors, malformed output, publication failures, model failures, missing credentials, or non-green exact-head validation fail closed. The label is a human-readable state hint; the app-bound `claude-review` check on the exact commit is the merge authority.

The publisher re-reads `needs-human` before every mutation group, but GitHub does not offer an atomic "check label and mutate comment/thread/label" transaction. A label can therefore change in the milliseconds between a read and its following write. This narrow residual TOCTOU window is accepted: the exact-head `claude-review` required check remains the authoritative merge gate, and later mutation groups re-check the hold and fail closed.

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

GitHub Actions installation tokens do not expose a reliable GraphQL repository role: `viewerPermission` can be `READ`, another non-write value, or absent even when a job grants specific write endpoints. The publisher therefore uses repository-role probing only for PAT/local execution. In `GITHUB_ACTIONS`, after exact-head validation has authenticated the token and the trusted job has declared explicit `issues: write` and `pull-requests: write` scopes, it validates write capability through the actual endpoint mutations; every REST or GraphQL mutation fails closed if its endpoint permission is unavailable.

Native review visibility is part of successful publication, not best-effort decoration. A failed native-review query or mutation propagates, keeps the `claude-review` check red, and remains retryable because no exact-head native marker was recorded.

Every workflow action is pinned to a full commit SHA. The Claude action remains the most privileged supply-chain dependency because it receives the OAuth secret and network access. Dependabot checks GitHub Actions weekly, but every proposed SHA rotation requires manual source/changelog review before merge. If an upstream pin is suspected of compromise, disable the affected workflow, rotate exposed credentials, inspect recent runs, and adopt a reviewed replacement SHA; a tag update alone is never trusted.

The coordinated workflow upgrade was verified on September 30, 2026 against each action's official Git tag endpoint. Every tag directly targets the commit pinned in the workflows:

| Action | Official tag | Pinned commit |
| --- | --- | --- |
| `actions/checkout` | [`v7.0.1`](https://github.com/actions/checkout/releases/tag/v7.0.1) | [`3d3c42e5aac5ba805825da76410c181273ba90b1`](https://github.com/actions/checkout/commit/3d3c42e5aac5ba805825da76410c181273ba90b1) |
| `actions/setup-python` | [`v7.0.0`](https://github.com/actions/setup-python/releases/tag/v7.0.0) | [`5fda3b95a4ea91299a34e894583c3862153e4b97`](https://github.com/actions/setup-python/commit/5fda3b95a4ea91299a34e894583c3862153e4b97) |
| `actions/upload-artifact` | [`v7.0.1`](https://github.com/actions/upload-artifact/releases/tag/v7.0.1) | [`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`](https://github.com/actions/upload-artifact/commit/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a) |
| `actions/download-artifact` | [`v8.0.1`](https://github.com/actions/download-artifact/releases/tag/v8.0.1) | [`3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`](https://github.com/actions/download-artifact/commit/3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c) |

Pin verification record: Anthropic's official annotated [`v1.0.236` tag](https://github.com/anthropics/claude-code-action/releases/tag/v1.0.236) peels to commit [`8ce9314fa9a404564fa7e954cd84f25bcba2b829`](https://github.com/anthropics/claude-code-action/commit/8ce9314fa9a404564fa7e954cd84f25bcba2b829), which is the workflow pin. GitHub reports the tag and commit as unsigned, so this is provenance evidence, not cryptographic identity proof; maintainers must review upstream source/history and Dependabot-proposed replacements before rotating it.

The separate `Claude Model Freshness` workflow runs weekly and on demand. It uses the non-billing model metadata endpoint to confirm the configured/default API model before normal pull-request traffic depends on it.

For public repositories, ensure the repository or organization Actions policy explicitly permits `pull_request_target`. GitHub has announced enforcement of its default blocking policy for that event beginning November 2, 2026; the review gate must fail closed rather than silently bypass review if policy blocks the workflow.

## Official references

- [Anthropic Messages API](https://platform.claude.com/docs/en/api/http/messages)
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Claude Sonnet 5 model and migration behavior](https://platform.claude.com/docs/en/models/sonnet-5/whats-new-sonnet-5)
- [Pinned Claude Code Action source](https://github.com/anthropics/claude-code-action/tree/8ce9314fa9a404564fa7e954cd84f25bcba2b829)
- [GitHub guidance for secure `pull_request_target` use](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)
