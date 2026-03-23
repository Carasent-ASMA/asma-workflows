# Audit: Auto PR Creation and Automerge Logic

## Scope

This audit covers the automation for protected-branch PR creation and automerge in:

- `shared/asma-workflows/.github/scripts/update_submodule_pointer.py` for pointer updates
- `infrastructure/asma-infrastructure/.github/scripts/deploy/argocd_deploy.py` for ArgoCD updates
- `shared/asma-workflows/.github/scripts/github_pr_shared.py` for shared PR helpers

## Status

- Completed: remove redundant PR type wrapping in the pointer updater
- Completed: unify bot branch name construction in shared PR helpers
- Completed: centralize PR metadata-body construction in shared PR helpers
- Deferred: consolidate dynamic module-loader bootstrapping as a broader deploy bootstrap refactor

## 1. Overlap and Duplication

- Shared logic is now centralized in `github_pr_shared.py`.
- Shared logic includes branch-name sanitization, deterministic bot branch naming, PR creation and reuse, immediate merge attempts, auto-merge enablement, protected-branch rule checks, protected-branch sync orchestration, and markdown metadata-body formatting.
- Pointer update keeps only pointer-specific concerns: submodule mapping, gitlink mutation, pointer commit creation, and pointer-specific PR summary text.
- ArgoCD update keeps only ArgoCD-specific concerns: repository preparation, image tag updates, remote sync handling, and ArgoCD-specific PR summary text.
- Remaining duplication is low and is mostly limited to runtime bootstrap code for dynamically loading helper modules.

## 2. Verbosity and Anti-Patterns

- Dynamic module loading is still verbose. This is a real issue, but it is broader than the PR/automerge feature because the same bootstrap pattern exists across several deploy scripts.
- Pointer type wrapping has been removed.
- Branch-name construction duplication has been removed.
- PR body construction duplication has been removed for the current scope by introducing a shared metadata-body helper.

## 3. Refactor Opportunities

### A. Pointer PR Types

- Completed. The pointer updater now uses shared PR types directly.

### B. Bot Branch Naming

- Completed. Both pointer and ArgoCD flows now use the shared bot-branch helper.

### C. Dynamic Module Loader Consolidation

- Still worth doing.
- This should be executed as a broader deploy bootstrap refactor because the duplication appears across multiple deploy scripts, not only in ArgoCD.
- Full static imports are still not viable because sparse-checkout bootstrapping remains a runtime constraint.

### D. PR Metadata Body Construction

- Completed for the current scope.
- The shared metadata-body helper can be reused by future protected-branch PR flows without expanding orchestration code.

## Implementation Status

### Phase 1. Remove Redundant Type Wrapping

- Completed.

### Phase 2. Unify Branch Name Construction

- Completed.

### Phase 3. Add Shared Dynamic Import Loader

- Deferred to a broader deploy bootstrap refactor.
- Recommended scope:
- consolidate repeated sibling-module loading across deploy scripts
- keep external shared-helper resolution explicit for sparse-checkout compatibility
- validate all deploy command entrypoints after consolidation

### Phase 4. Parameterize PR Message Construction

- Completed.

## Recommendation

The PR/automerge implementation is now compact and maintainable for the pointer and ArgoCD flows. The next meaningful refactor is no longer feature-specific PR logic; it is bootstrap consolidation across the deploy script family.
