---
goal: Implement reusable GitHub Actions workflows for the private asma-app family
version: 1.0
date_created: 2026-03-09
last_updated: 2026-03-09
owner: Platform Engineering
status: Planned
tags:
  [github-actions, app-family, workflows, infrastructure, release, s3, hasura]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan defines how to implement GitHub Actions support for the private `asma-app-*` family using three reusable release workflows: master, pull request, and hotpatch. The plan preserves the current Bitbucket release semantics first, while separating generic release logic into `asma-workflows` and app-family-specific S3 and Hasura side effects into `asma-infrastructure`.

## 1. Requirements & Constraints

- **REQ-001**: Implement three reusable release workflows for app-family repositories: stable release from `master`, preview release for pull requests, and hotpatch release from `releases/v*.*.*`.
- **REQ-002**: Preserve current Bitbucket runtime behavior described in `/Users/igor/carasent/asma-modules/shared/asma-workflows/_docs/asma-app-family-workflow-behavior.md` before introducing intentional semantic changes.
- **REQ-003**: Keep caller workflows in `asma-app-*` repositories thin. Repository workflows must primarily forward inputs, permissions, and secrets into reusable workflows.
- **REQ-004**: Reuse shared git-tagging and release-gate primitives from `/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts` instead of reimplementing version planning.
- **REQ-005**: Place app-family-specific S3 publication and directory Hasura update logic in `asma-infrastructure`, not in each app repository.
- **REQ-006**: Support PR preview asset versions in the form `pr<number>`.
- **REQ-007**: Support stable tags in the form `vX.Y.Z`.
- **REQ-008**: Support hotpatch tags in the form `vX.Y.Z-N`.
- **REQ-009**: Preserve replacement semantics for repeated uploads to the same S3 target folder.
- **REQ-010**: Preserve directory Hasura updates to `web.dev`, `web.stage`, and `web`.
- **REQ-011**: Preserve the stable-release-only journal updates for `customer_user_app_version` in `web.dev`.
- **REQ-012**: Make branch and trigger rules explicit. Do not rely on auto-detection inside shared scripts.
- **REQ-013**: Provide an implementation path that can be rolled out incrementally repo by repo.
- **SEC-001**: Secrets for S3 and Hasura must remain in GitHub Actions secrets and must never be hardcoded in repositories or scripts.
- **SEC-002**: Cross-repo access between private repositories must use supported GitHub authentication flows already used in the workspace, such as `actions/create-github-app-token` or repository checkout with scoped tokens.
- **CON-001**: GitHub only discovers workflow YAML files directly under `.github/workflows`. Nested folders such as `.github/workflows/apps-workflows/...` are not valid locations for executable workflow files.
- **CON-002**: Dedicated subfolders are valid for scripts and docs, for example `.github/scripts/apps_workflows/` and `_docs/apps-workflows/`.
- **CON-003**: Reusable workflows that are intended to be called cross-repo must expose a stable `workflow_call` contract with explicit inputs and secrets.
- **CON-004**: The current shared `release_gate.py` behavior is commit-message-driven because path-based gating is intentionally disabled. Any app-family workflow that needs path filtering must implement that intentionally.
- **GUD-001**: Preserve current behavior first. Normalize legacy commit-type semantics only after parity is achieved and documented.
- **GUD-002**: Keep generic release planning in `asma-workflows` and keep deployment side effects in `asma-infrastructure`.
- **PAT-001**: Follow the existing workspace pattern where reusable workflows checkout scripts from another repository into `.github/_<repo-name>`.
- **PAT-002**: Use Python entrypoints for orchestrating deploy logic when behavior spans multiple steps, environments, and APIs.

## 2. Implementation Steps

### Implementation Phase 1

- **GOAL-001**: Finalize architecture boundaries, workflow naming, and repository responsibilities.

| Task     | Description                             | Completed | Date |
| -------- | --------------------------------------- | --------- | ---- |
| TASK-001 | Confirm repo split.                     |           |      |
| TASK-002 | Approve three reusable workflow names.  |           |      |
| TASK-003 | Approve app script package location.    |           |      |
| TASK-004 | Define private cross-repo call pattern. |           |      |
| TASK-005 | Define common workflow input contract.  |           |      |

### Implementation Phase 2

- **GOAL-002**: Align shared version-planning semantics with legacy app-family behavior.

| Task     | Description                                 | Completed | Date |
| -------- | ------------------------------------------- | --------- | ---- |
| TASK-006 | Compare shared gate with legacy parser.     |           |      |
| TASK-007 | Decide patch-worthy commit parity scope.    |           |      |
| TASK-008 | Decide whether to add file-change gating.   |           |      |
| TASK-009 | Implement approved parity changes.          |           |      |
| TASK-010 | Add tests for app-family release semantics. |           |      |

### Implementation Phase 3

- **GOAL-003**: Implement app-family-specific infrastructure scripts in `asma-infrastructure`.

| Task     | Description                                       | Completed | Date |
| -------- | ------------------------------------------------- | --------- | ---- |
| TASK-011 | Create app-workflow script package.               |           |      |
| TASK-012 | Implement `app_release.py` entrypoint.            |           |      |
| TASK-013 | Implement S3 replace-and-publish helpers.         |           |      |
| TASK-014 | Implement Hasura app-version helpers.             |           |      |
| TASK-015 | Implement stable journal update helper.           |           |      |
| TASK-016 | Implement preview, stable, and hotpatch payloads. |           |      |
| TASK-017 | Add tests and CI for app-workflow scripts.        |           |      |

### Implementation Phase 4

- **GOAL-004**: Implement reusable workflows in `asma-workflows` for the three app-family release modes.

| Task     | Description                              | Completed | Date |
| -------- | ---------------------------------------- | --------- | ---- |
| TASK-018 | Create master reusable workflow.         |           |      |
| TASK-019 | Implement stable release execution path. |           |      |
| TASK-020 | Create PR preview reusable workflow.     |           |      |
| TASK-021 | Implement PR preview execution path.     |           |      |
| TASK-022 | Create hotpatch reusable workflow.       |           |      |
| TASK-023 | Implement hotpatch execution path.       |           |      |
| TASK-024 | Add shared workflow summaries.           |           |      |

### Implementation Phase 5

- **GOAL-005**: Add thin caller workflows to each `asma-app-*` repository.

| Task     | Description                                   | Completed | Date |
| -------- | --------------------------------------------- | --------- | ---- |
| TASK-025 | Add master caller workflows to pilot repos.   |           |      |
| TASK-026 | Add PR caller workflows to pilot repos.       |           |      |
| TASK-027 | Add hotpatch caller workflows to pilot repos. |           |      |
| TASK-028 | Standardize per-repo override inputs.         |           |      |
| TASK-029 | Add preflight secrets and access checks.      |           |      |

### Implementation Phase 6

- **GOAL-006**: Validate parity, roll out incrementally, and document the new workflow family.

| Task     | Description                               | Completed | Date |
| -------- | ----------------------------------------- | --------- | ---- |
| TASK-030 | Run pilot on `asma-app-shell`.            |           |      |
| TASK-031 | Verify S3, Hasura, and git-tag outputs.   |           |      |
| TASK-032 | Document intentional behavior deviations. |           |      |
| TASK-033 | Roll out to `asma-app-advoca`.            |           |      |
| TASK-034 | Define Bitbucket decommission criteria.   |           |      |

## 3. Alternatives

- **ALT-001**: Put all app-family workflow logic directly into each `asma-app-*` repository. Rejected because it duplicates release logic, S3 logic, Hasura logic, and future fixes across every app repository.
- **ALT-002**: Put all app-family logic, including Hasura and S3 side effects, into `asma-workflows`. Rejected because those behaviors are infrastructure-specific and fit the existing pattern already used by `asma-infrastructure` reusable workflows and script packages.
- **ALT-003**: Create nested workflow folders such as `asma-infrastructure/.github/workflows/apps-workflows/`. Rejected because GitHub does not discover workflow YAML files in nested directories under `.github/workflows`.
- **ALT-004**: Use one monolithic reusable workflow with mode switches for `master`, `pr`, and `hotpatch`. Rejected for the initial rollout because branch rules, event payloads, and tag side effects differ enough that three caller-facing reusable workflows are clearer and lower risk.
- **ALT-005**: Keep the legacy shell scripts and invoke them from GitHub Actions unchanged. Rejected for the initial target architecture because the logic is currently distributed through S3-hosted script bundles and is harder to test, version, and evolve safely in GitHub.

## 4. Dependencies

- **DEP-001**: Existing shared tagging and release-gate helpers in `/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts`.
- **DEP-002**: Existing cross-repo checkout pattern already used by `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-backend-deploy.yml` and `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-hasura-migration.yml`.
- **DEP-003**: GitHub secrets for S3 credentials, Hasura endpoints, and Hasura admin secrets for all required environments.
- **DEP-004**: Agreement on whether app-family workflows must preserve legacy commit-type semantics exactly or may adopt the current shared release-gate semantics.
- **DEP-005**: Agreement on which GitHub authentication method will be standard for cross-repo reusable workflow and script checkout in private repositories.

## 5. Files

- **FILE-001**: `/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/workflows/reusable-app-master-release.yml`.
- **FILE-002**: `/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/workflows/reusable-app-pr-preview.yml`.
- **FILE-003**: `/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/workflows/reusable-app-hotpatch-release.yml`.
- **FILE-004**: `/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/release_gate.py` or `/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/git_tagging_shared.py` if parity changes are approved.
- **FILE-005**: `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/scripts/apps_workflows/app_release.py`.
- **FILE-006**: `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/scripts/apps_workflows/__init__.py`.
- **FILE-007**: `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/scripts/apps_workflows/tests/`.
- **FILE-008**: `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/ci-app-workflow-scripts.yml`.
- **FILE-009**: `/Users/igor/carasent/asma-modules/shell/asma-app-shell/.github/workflows/app-master-release.yml`.
- **FILE-010**: `/Users/igor/carasent/asma-modules/shell/asma-app-shell/.github/workflows/app-pr-preview.yml`.
- **FILE-011**: `/Users/igor/carasent/asma-modules/shell/asma-app-shell/.github/workflows/app-hotpatch-release.yml`.
- **FILE-012**: Equivalent caller workflows in `/Users/igor/carasent/asma-modules/shell/asma-app-advoca/.github/workflows/`.
- **FILE-013**: `/Users/igor/carasent/asma-modules/shared/asma-workflows/_docs/asma-app-family-workflow-behavior.md` for parity notes and post-implementation updates.

## 6. Testing

- **TEST-001**: Unit-test release-gate and tagging behavior for stable, PR, and hotpatch version resolution.
- **TEST-002**: Unit-test infrastructure app-release helpers for S3 target resolution and Hasura payload generation.
- **TEST-003**: Validate that the master reusable workflow does not push tags before S3 and Hasura steps complete successfully.
- **TEST-004**: Validate that the PR reusable workflow publishes preview assets under `pr<number>/` and does not create stable tags.
- **TEST-005**: Validate that the hotpatch reusable workflow rejects invalid branch names and only allocates `vX.Y.Z-N` from valid `releases/v*.*.*` branches.
- **TEST-006**: Validate secret resolution and environment mapping for Hasura endpoints and admin secrets.
- **TEST-007**: Perform an end-to-end pilot run in one app repository and compare outputs against a known-good Bitbucket release.

## 7. Risks & Assumptions

- **RISK-001**: The current shared release gate does not exactly match legacy app-family commit parsing, which can change release/no-release outcomes if not addressed deliberately.
- **RISK-002**: Cross-repo reusable workflow access for private repositories may require GitHub App token setup beyond the default `GITHUB_TOKEN` depending on repository policy.
- **RISK-003**: Reproducing Hasura mutation behavior exactly may expose undocumented assumptions from the legacy shell scripts.
- **RISK-004**: PR preview workflows depend on reliable extraction of the PR number from GitHub event payloads and not from merge commit messages, which is a semantic shift from the legacy Bitbucket implementation.
- **RISK-005**: S3 replacement semantics can delete working preview or release assets if version resolution is wrong.
- **ASSUMPTION-001**: `asma-app-shell` and `asma-app-advoca` remain representative pilot repositories for the broader `asma-app-*` family.
- **ASSUMPTION-002**: App-family repositories can use a common build contract such as `pnpm install` followed by `pnpm run build`, with limited overrides.
- **ASSUMPTION-003**: The existing `asma-infrastructure` repository is the correct long-term home for app-family Hasura and S3 release scripts.
- **ASSUMPTION-004**: The rollout will start with parity and will postpone functional improvements until after the new workflows are stable.

## 8. Related Specifications / Further Reading

/Users/igor/carasent/asma-modules/shared/asma-workflows/\_docs/asma-app-family-workflow-behavior.md

/Users/igor/carasent/asma-modules/shared/asma-workflows/\_docs/git-tagging-script-flow.md

/Users/igor/carasent/asma-modules/shared/asma-workflows/\_docs/reusable-git-tagging-extraction-plan-completed.md

/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-backend-deploy.yml

/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-hasura-migration.yml
