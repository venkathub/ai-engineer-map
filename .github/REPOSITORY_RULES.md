# Repository settings

Expected GitHub configuration for `main`:

- pull request required before merging;
- `curriculum-and-labs` status check required and branch must be current;
- conversation resolution required;
- linear history required;
- force pushes and branch deletion blocked;
- administrators included;
- squash merge enabled; merge commits and rebase merges disabled;
- merged branches automatically deleted;
- vulnerability alerts enabled.

The project does not require an approving review count so a solo maintainer is not permanently blocked. CODEOWNERS still makes ownership visible and can be upgraded to a required review when another maintainer is available.

Read the live state with:

```bash
gh api repos/venkathub/ai-engineer-map/branches/main/protection
gh api repos/venkathub/ai-engineer-map
```
