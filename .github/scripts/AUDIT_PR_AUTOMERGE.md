## Audit: Auto PR Creation & Automerge Logic (Pointer Update & ArgoCD Update)

### Scope
This audit covers the automation for protected-branch PR creation and automerge in:
- `shared/asma-workflows/.github/scripts/update_submodule_pointer.py` (pointer update)
- `infrastructure/asma-infrastructure/.github/scripts/deploy/argocd_deploy.py` (ArgoCD update)
- `shared/asma-workflows/.github/scripts/github_pr_shared.py` (shared PR helpers)

---

### 1. Overlap & Duplication

- **Shared Logic**: Most low-level PR, automerge, and branch rules logic is now centralized in `github_pr_shared.py`.
- This includes: branch name sanitization, PR creation/reuse, auto-merge enablement, immediate merge, and protected-branch sync orchestration.
- **Pointer Update**: Calls shared helpers for all PR/automerge mechanics, but still wraps some types (e.g., its own `PullRequestInfo`) and has pointer-specific branch naming and commit logic.
- **ArgoCD Update**: Now delegates all PR/automerge mechanics to the shared `sync_current_head_to_protected_branch_via_pull_request` function. Only ArgoCD-specific orchestration and logging remain local.
- **Duplication**: Minimal remaining duplication. Both pointer and ArgoCD flows have their own branch-naming helpers, but both use the shared branch sanitizer. Each has a thin wrapper for domain-specific PR title/body.

---

### 2. Verbosity & Anti-patterns

- **Dynamic Module Loading**: Both pointer and ArgoCD flows use dynamic import logic to load the shared helper. This is necessary for sparse-checkout CI, but adds boilerplate and makes type-checking harder.
- **Type Wrapping**: Pointer update re-wraps the shared `PullRequestInfo` and `PullRequestMergeAttempt` types, which is unnecessary now that the shared helper is stable. This adds verbosity and can be error-prone.
- **Branch Name Construction**: Both flows have their own branch-naming helpers, but the logic is nearly identical except for the prefix. This could be unified with a shared helper that takes a prefix argument.
- **Commit/PR Message Construction**: Each flow builds its own PR title/body, which is appropriate, but could be further parameterized if more flows are added.

---

### 3. Opportunities for Refactor

**A. Remove Redundant Type Wrapping**
- Pointer update should use the shared `PullRequestInfo` and `PullRequestMergeAttempt` types directly, not re-wrap them.

**B. Unify Branch Name Construction**
- Move branch name construction to a single shared helper in `github_pr_shared.py` that takes a prefix (e.g., `bot/pointer/`, `bot/argocd-sync/`) and a fallback.
- Both pointer and ArgoCD flows can call this with their desired prefix.

**C. Reduce Dynamic Import Boilerplate**
- Consider a thin shared loader utility for dynamic imports to reduce repeated code.
- (Note: Full static import is not possible due to sparse-checkout constraints.)

**D. Parameterize PR Message Construction (Optional)**
- If more flows are added, consider a shared PR message builder that takes domain-specific fields.

---

## Refactor Implementation Plan

### 1. Remove Redundant Type Wrapping in Pointer Update
- Change `update_submodule_pointer.py` to use `github_pr_shared.PullRequestInfo` and `PullRequestMergeAttempt` directly.
- Update all references and tests accordingly.

### 2. Unify Branch Name Construction
- Add a shared `build_bot_branch_name(prefix: str, name_component: str, sha: str, fallback: str)` helper to `github_pr_shared.py`.
- Refactor both pointer and ArgoCD flows to use this for branch naming.

### 3. (Optional) Add Shared Dynamic Import Loader
- If dynamic import logic is repeated in more than two places, add a shared loader utility.

### 4. (Optional) Parameterize PR Message Construction
- If more flows are added, consider a shared PR message builder.

---

**These changes will further reduce duplication, improve maintainability, and make the automation more robust.**