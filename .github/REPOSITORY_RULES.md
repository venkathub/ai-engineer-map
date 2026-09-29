# Repository settings

Expected GitHub configuration for `main`:

- pull request required before merging;
- `curriculum-and-labs` and `claude-review` status checks required and branch must be current;
- conversation resolution required;
- linear history required;
- force pushes and branch deletion blocked;
- administrators included;
- squash merge enabled; merge commits and rebase merges disabled;
- merged branches automatically deleted;
- vulnerability alerts enabled.

The project does not require a human approving-review count so a solo maintainer is not permanently blocked. The required `claude-review` check fails closed unless Claude approves the current head commit with zero CRITICAL, HIGH, or MEDIUM findings; LOW notes are non-blocking. CODEOWNERS still makes ownership visible and can be upgraded to a required human review when another maintainer is available.

Read the live state with:

```bash
gh api repos/venkathub/ai-engineer-map/branches/main/protection
gh api repos/venkathub/ai-engineer-map
```
