---
goal: Implement reusable GitHub Actions workflows for the private asma-app family
version: 2.0
date_created: 2026-03-09
last_updated: 2026-03-10
owner: Platform Engineering
status: Planned
tags:
  [github-actions, app-family, workflows, infrastructure, release, s3, hasura]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan defines the implementation path for GitHub Actions support for the private `asma-app-*` family.

The target design uses three reusable release workflows:

- stable release from `master`
- preview release for pull requests
- hotpatch release from `releases/v*.*.*`

The implementation must preserve current Bitbucket release behavior first, while splitting responsibilities cleanly across repositories:

- `asma-workflows` owns shared release-planning logic and shared documentation
- `asma-infrastructure` owns app-family reusable workflows and deployment side effects such as S3 publication and directory Hasura updates
- each `asma-app-*` repository owns only thin caller workflows and repository-local build inputs

The plan is intentionally phased so each phase can end in a clean, reviewable, shippable state before the next phase starts.

## 1. Decision Summary

The implementation will follow these decisions.

- Use three caller-facing reusable workflows instead of one mode-switched workflow.
- Keep executable workflow files directly under `.github/workflows/` because GitHub does not discover nested workflow directories.
- Keep app-family-specific Python orchestration in `asma-infrastructure/.github/scripts/apps_workflows/`.
- Reuse the existing split between `release_gate.py`, `git_tagging_plan.py`, and `git_tagging_ops.py`.
- Delay tag push until after build, S3 publish, and Hasura updates succeed.
- Keep caller workflows in app repositories thin and explicit.
- Preserve current Bitbucket semantics first, then document and apply intentional improvements later.
- Roll out on `asma-app-shell` first, then `asma-app-advoca`, then the rest of the app family.

## 2. Target Architecture

### Repository Responsibilities

| Repository                           | Responsibility                                                                                                                                            | Must Not Own                                                                |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `shared/asma-workflows`              | shared release gate, shared git-tag planning, shared git-tag operations, shared documentation                                                             | app-family reusable workflow YAML, S3 mutation logic, Hasura mutation logic |
| `infrastructure/asma-infrastructure` | app-family reusable workflow YAML, Python scripts for S3 upload/replace, directory Hasura updates, journal updates, environment mapping, infra-side tests | generic semantic version decision logic, reusable git primitives            |
| `shell/asma-app-*`                   | thin caller workflows, repo-local build command overrides, repo-specific secrets wiring if needed                                                         | duplicated release logic, duplicated infra orchestration                    |

### Workflow Topology

Executable reusable workflows will live here:

- `infrastructure/asma-infrastructure/.github/workflows/reusable-app-master-release.yml`
- `infrastructure/asma-infrastructure/.github/workflows/reusable-app-pr-preview.yml`
- `infrastructure/asma-infrastructure/.github/workflows/reusable-app-hotpatch-release.yml`

App-family infra scripts will live here:

- `infrastructure/asma-infrastructure/.github/scripts/apps_workflows/app_release.py`
- `infrastructure/asma-infrastructure/.github/scripts/apps_workflows/app_release_shared.py`
- `infrastructure/asma-infrastructure/.github/scripts/apps_workflows/tests/`

Thin caller workflows will live here in each app repository:

- `.github/workflows/app-master-release.yml`
- `.github/workflows/app-pr-preview.yml`
- `.github/workflows/app-hotpatch-release.yml`

### Shared Execution Pattern

Each reusable workflow should follow the same high-level shape.

1. Checkout the caller repository with full git history.
2. Acquire a token for cross-repo private checkout.
3. Checkout shared scripts from `asma-workflows` into `.github/_asma-workflows`.
4. Checkout infra scripts from `asma-infrastructure` into `.github/_asma-infrastructure`.
5. Run release gating and release planning in `asma-workflows`.
6. Build the app in the caller repository.
7. Run S3 and Hasura side effects through `app_release.py` in `asma-infrastructure`.
8. Push the resolved tag only after all release side effects succeed.
9. Publish a workflow summary with version, target paths, and mutation results.

This matches the existing reusable workflow pattern already used by `reusable-npm-publish.yml` and the existing cross-repo checkout pattern used by infrastructure reusable workflows.

## 3. Trigger Matrix

| Flow       | Caller Trigger | Branch Rule          | Version Form | Tag Created   | S3 Target               | Hasura Update |
| ---------- | -------------- | -------------------- | ------------ | ------------- | ----------------------- | ------------- |
| Stable     | `push`         | `master`             | `X.Y.Z`      | `vX.Y.Z`      | `<service>/<X.Y.Z>/`    | yes           |
| PR Preview | `pull_request` | any active PR branch | `pr<number>` | no stable tag | `<service>/pr<number>/` | yes           |
| Hotpatch   | `push`         | `releases/v*.*.*`    | `X.Y.Z-N`    | `vX.Y.Z-N`    | `<service>/<X.Y.Z-N>/`  | yes           |

## 4. Workflow Contracts

The reusable workflows need explicit `workflow_call` contracts so app repositories can stay minimal and the implementation stays stable across repos.

### 4.1 Stable Release Contract

Workflow file:

- `infrastructure/asma-infrastructure/.github/workflows/reusable-app-master-release.yml`

Required inputs:

- `service_name`
- `build_command`
- `artifact_path`
- `node_version`
- `pnpm_version`

Optional inputs:

- `working_directory`
- `release_gate_patterns`
- `install_command`
- `python_version`
- `aws_region`
- `directory_service_name_override`
- `enable_release_gate`
- `debug`

Required secrets:

- GitHub App or equivalent token inputs required to checkout `asma-workflows` and `asma-infrastructure`
- AWS credentials for app asset publication
- directory Hasura endpoints and admin secrets for `web.dev`, `web.stage`, and `web`

Expected outputs:

- `version`
- `tag`
- `bump_type`
- `s3_prefix`
- `service_name`

### 4.2 PR Preview Contract

Workflow file:

- `infrastructure/asma-infrastructure/.github/workflows/reusable-app-pr-preview.yml`

Required inputs:

- `service_name`
- `build_command`
- `artifact_path`
- `node_version`
- `pnpm_version`

Optional inputs:

- `working_directory`
- `release_gate_patterns`
- `install_command`
- `python_version`
- `aws_region`
- `directory_service_name_override`
- `allowed_branch_prefixes`
- `debug`

Required secrets:

- the same cross-repo token and infra secrets used by stable release

Expected outputs:

- `version` with `pr<number>` form
- `pr_number`
- `s3_prefix`
- `service_name`

### 4.3 Hotpatch Contract

Workflow file:

- `infrastructure/asma-infrastructure/.github/workflows/reusable-app-hotpatch-release.yml`

Required inputs:

- `service_name`
- `build_command`
- `artifact_path`
- `node_version`
- `pnpm_version`

Optional inputs:

- `working_directory`
- `install_command`
- `python_version`
- `aws_region`
- `directory_service_name_override`
- `debug`

Required secrets:

- the same cross-repo token and infra secrets used by stable release

Expected outputs:

- `version` with `X.Y.Z-N` form
- `tag`
- `base_tag`
- `s3_prefix`
- `service_name`

## 5. Phase Plan

Each phase ends with a reviewable artifact set and explicit exit criteria. If a phase needs to be paused or reset, it can do so without leaving the overall rollout in an ambiguous state.

### Phase 1: Lock Architecture And Contracts

Goal:

- finish the design decisions that should not move during implementation

Deliverables:

- final version of this implementation plan
- final version of `asma-app-family-workflow-behavior.md`
- approved workflow names
- approved repo boundaries
- approved reusable workflow inputs, outputs, and required secrets

Tasks:

| Task  | Description                                             | Exit Condition                                    |
| ----- | ------------------------------------------------------- | ------------------------------------------------- |
| P1-01 | Confirm the three reusable workflow names               | names accepted without further architecture churn |
| P1-02 | Confirm app-family script home in `asma-infrastructure` | script location accepted                          |
| P1-03 | Confirm caller workflows stay thin                      | no domain logic remains planned in app repos      |
| P1-04 | Confirm cross-repo checkout token pattern               | auth approach is chosen and documented            |
| P1-05 | Confirm reusable workflow contracts                     | inputs, secrets, outputs are stable               |

Phase exit criteria:

- no unresolved architecture question blocks implementation

### Phase 2: Reach Shared Release-Planning Parity

Goal:

- make sure the reusable shared release decision layer can support app-family semantics without hidden behavior changes

Deliverables:

- parity decision record for release-gate differences versus legacy Bitbucket behavior
- any approved changes in `release_gate.py` or `git_tagging_plan.py`
- tests for stable, PR, and hotpatch version resolution

Tasks:

| Task  | Description                                                                                                 | Exit Condition                                          |
| ----- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| P2-01 | Compare legacy bump rules with shared release gate                                                          | every difference is documented                          |
| P2-02 | Decide whether `docs`, `ci`, `revert`, and merge commits remain patch-worthy for app-family stable releases | policy is explicit                                      |
| P2-03 | Decide whether PR preview flow must keep commit-message validation                                          | policy is explicit                                      |
| P2-04 | Decide whether path-based change checks stay disabled for initial rollout                                   | workflow behavior is explicit                           |
| P2-05 | Implement only the approved parity changes                                                                  | shared scripts are updated or explicitly left unchanged |
| P2-06 | Add tests covering stable, PR, and hotpatch planning                                                        | tests pass in CI                                        |

Phase exit criteria:

- the plan can explain exactly why a release does or does not proceed in all three flow types

### Phase 3: Build Infra-Side App Release Orchestration

Goal:

- move S3 and directory Hasura behavior into a tested Python entrypoint in `asma-infrastructure`

Deliverables:

- `.github/scripts/apps_workflows/app_release.py`
- shared helpers for S3 target calculation and Hasura payload creation
- tests for payload generation and environment mapping
- an infra CI workflow for these scripts

Tasks:

| Task  | Description                                                                              | Exit Condition                                 |
| ----- | ---------------------------------------------------------------------------------------- | ---------------------------------------------- |
| P3-01 | Create the `apps_workflows` Python package                                               | package structure exists                       |
| P3-02 | Implement a single entrypoint with explicit modes `stable`, `pr-preview`, and `hotpatch` | CLI contract is stable                         |
| P3-03 | Implement S3 replace-and-upload helpers                                                  | repeated runs replace the exact version folder |
| P3-04 | Implement Hasura `app_versions` mutation helpers                                         | all three target environments are supported    |
| P3-05 | Implement stable-only `customer_user_app_version` journal updates in `web.dev`           | legacy behavior is preserved                   |
| P3-06 | Add dry-run and summary output modes for CI observability                                | workflow logs are actionable                   |
| P3-07 | Add tests and script CI                                                                  | script package is safe to evolve               |

Phase exit criteria:

- a single tested Python entrypoint can perform every app-family side effect needed by all three workflows

### Phase 4: Implement Reusable Workflows In `asma-infrastructure`

Goal:

- create the three reusable workflow entrypoints that apps will call

Deliverables:

- `reusable-app-master-release.yml`
- `reusable-app-pr-preview.yml`
- `reusable-app-hotpatch-release.yml`
- shared workflow summaries for all flows

Tasks:

| Task  | Description                                                   | Exit Condition                              |
| ----- | ------------------------------------------------------------- | ------------------------------------------- |
| P4-01 | Create stable release workflow skeleton                       | workflow_call contract is implemented       |
| P4-02 | Wire shared release gate and stable tag planning              | version resolution is deterministic         |
| P4-03 | Call infra script for stable release                          | build, S3, Hasura happen before tag push    |
| P4-04 | Create PR preview workflow skeleton                           | workflow_call contract is implemented       |
| P4-05 | Resolve `pr<number>` from GitHub pull request data            | no merge-message parsing is required        |
| P4-06 | Call infra script for preview release                         | preview assets and Hasura rows are written  |
| P4-07 | Create hotpatch workflow skeleton                             | workflow_call contract is implemented       |
| P4-08 | Resolve `vX.Y.Z-N` from branch name using shared git planning | branch rule is enforced explicitly          |
| P4-09 | Call infra script for hotpatch release                        | hotpatch assets and Hasura rows are written |
| P4-10 | Add workflow summaries and failure diagnostics                | operators can debug from job output         |

Phase exit criteria:

- all three reusable workflows run end to end in a controlled test repository or dry-run setup

### Phase 5: Add Thin Caller Workflows To Pilot Repositories

Goal:

- integrate the reusable workflows into app repositories with minimal local logic

Deliverables:

- caller workflows in `asma-app-shell`
- caller workflows in `asma-app-advoca`
- per-repo inputs for build command and artifact path if needed

Tasks:

| Task  | Description                                                  | Exit Condition                                 |
| ----- | ------------------------------------------------------------ | ---------------------------------------------- |
| P5-01 | Add stable caller workflow to `asma-app-shell`               | caller only forwards inputs and secrets        |
| P5-02 | Add PR caller workflow to `asma-app-shell`                   | caller only forwards inputs and secrets        |
| P5-03 | Add hotpatch caller workflow to `asma-app-shell`             | caller only forwards inputs and secrets        |
| P5-04 | Validate whether `asma-app-advoca` needs any input overrides | differences are explicit and minimal           |
| P5-05 | Add the three caller workflows to `asma-app-advoca`          | workflow parity exists across both pilot repos |
| P5-06 | Add preflight checks for required secrets and token access   | misconfiguration fails early                   |

Phase exit criteria:

- both pilot repositories have only thin reusable-workflow callers and no duplicated deployment logic

### Phase 6: Pilot, Compare, Roll Out, And Decommission Legacy Flow

Goal:

- prove parity against Bitbucket and then scale safely

Deliverables:

- pilot evidence from `asma-app-shell`
- rollout evidence from `asma-app-advoca`
- documented parity deviations if any
- Bitbucket decommission checklist

Tasks:

| Task  | Description                                                                               | Exit Condition                                  |
| ----- | ----------------------------------------------------------------------------------------- | ----------------------------------------------- |
| P6-01 | Run controlled pilot on `asma-app-shell` stable, PR, and hotpatch flows                   | all outputs are captured                        |
| P6-02 | Compare S3 prefixes, Hasura mutations, and tag behavior against known-good Bitbucket runs | parity is verified or deviations are documented |
| P6-03 | Roll out to `asma-app-advoca`                                                             | second repo proves reusability                  |
| P6-04 | Update behavior documentation with any intentional deviations                             | docs match reality                              |
| P6-05 | Define Bitbucket disable and rollback conditions                                          | cutover is operationally safe                   |

Phase exit criteria:

- the GitHub Actions flow is trusted enough to retire the legacy Bitbucket app-family release path

## 6. Concrete File Plan

### Files To Create In `infrastructure/asma-infrastructure`

- `.github/workflows/reusable-app-master-release.yml`
- `.github/workflows/reusable-app-pr-preview.yml`
- `.github/workflows/reusable-app-hotpatch-release.yml`
- `.github/scripts/apps_workflows/__init__.py`
- `.github/scripts/apps_workflows/app_release.py`
- `.github/scripts/apps_workflows/app_release_shared.py`
- `.github/scripts/apps_workflows/tests/`
- `.github/workflows/ci-app-workflow-scripts.yml`

### Files To Update In `shared/asma-workflows`

- `.github/scripts/release_gate.py` if parity changes are approved
- `.github/scripts/git_tagging_plan.py` only if a missing release-planning primitive is identified
- `_docs/asma-app-family-workflow-behavior.md`
- `_docs/implementation-plan-app-family-workflows.md`

### Files To Create In Pilot App Repositories

For `asma-app-shell` and `asma-app-advoca`:

- `.github/workflows/app-master-release.yml`
- `.github/workflows/app-pr-preview.yml`
- `.github/workflows/app-hotpatch-release.yml`

## 7. Execution Details By Flow

### Stable Release

Target sequence:

1. Trigger on push to `master`.
2. Run shared release gate.
3. Resolve next stable version with shared git planning.
4. Build app artifacts.
5. Run infra `app_release.py stable`.
6. Upsert directory Hasura rows for `web.dev`, `web.stage`, and `web`.
7. Apply stable-only journal updates in `web.dev`.
8. Replace and upload the S3 version folder.
9. Push git tag `vX.Y.Z`.

### PR Preview

Target sequence:

1. Trigger on `pull_request` events that represent active PR updates.
2. Optionally run the shared release gate if PR previews should still require release-worthy commits.
3. Resolve `pr<number>` from the GitHub pull request payload.
4. Build app artifacts.
5. Run infra `app_release.py pr-preview`.
6. Upsert directory Hasura rows for `web.dev`, `web.stage`, and `web` using the PR version.
7. Replace and upload the S3 preview folder.
8. Do not create a stable git tag.

### Hotpatch

Target sequence:

1. Trigger on push to `releases/v*.*.*`.
2. Resolve the branch base tag from the branch name.
3. Validate that the base version matches the latest merged stable tag.
4. Resolve the first free hotpatch tag `vX.Y.Z-N`.
5. Build app artifacts.
6. Run infra `app_release.py hotpatch`.
7. Upsert directory Hasura rows for `web.dev`, `web.stage`, and `web`.
8. Replace and upload the S3 hotpatch folder.
9. Push git tag `vX.Y.Z-N`.

## 8. Authentication And Secrets Plan

The implementation must use the same private cross-repo access pattern already present in the workspace.

Required capability groups:

- token capable of checking out `asma-workflows`
- token capable of checking out `asma-infrastructure`
- AWS credentials for S3 asset publication
- directory Hasura endpoints and admin secrets for `web.dev`, `web.stage`, and `web`

Implementation guidance:

- prefer `actions/create-github-app-token` where repository policy requires private cross-repo access
- keep secret names explicit in reusable workflow contracts
- fail fast if any required secret or endpoint is missing
- mask all admin secrets before writing logs

## 9. Testing And Acceptance Criteria

### Shared Script Tests

- release gate tests cover stable, preview, and hotpatch commit/message cases
- git planning tests cover stable, PR, and hotpatch tag resolution
- infra app-release tests cover S3 target calculation, Hasura payload generation, and journal update payloads

### Workflow Validation

- stable workflow does not push the git tag before S3 and Hasura succeed
- PR preview workflow always resolves `pr<number>` from GitHub event data
- hotpatch workflow fails fast for invalid branch names or mismatched base tags
- workflow summaries report resolved version, service name, and target S3 prefix

### Pilot Acceptance

The pilot is accepted only if all of the following are true.

- GitHub Actions generates the same version forms as Bitbucket for stable, PR, and hotpatch flows
- S3 paths match expected legacy folder structure
- `app_versions` mutations land in all required environments
- stable-only journal updates still happen only for plain stable releases
- tags are created only after all side effects succeed

## 10. Risks And Mitigations

| Risk                                                     | Impact                                 | Mitigation                                                                                  |
| -------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------- |
| Shared release gate differs from legacy Bitbucket rules  | different release/no-release outcomes  | document all differences in Phase 2 and implement only approved parity changes              |
| Cross-repo checkout fails in private repos               | workflows cannot access shared scripts | standardize the GitHub App token pattern before rollout                                     |
| Hasura behavior contains undocumented legacy assumptions | workflow parity breaks during cutover  | encode payload logic in tested Python helpers and compare against known-good legacy outputs |
| Wrong version resolution deletes correct S3 assets       | release outage or preview corruption   | dry-run summary, pilot validation, and tag push only after successful side effects          |
| PR preview semantics drift from Bitbucket behavior       | unexpected preview updates             | document the GitHub PR-number source explicitly and validate with real PR events            |

## 11. Non-Goals For The First Rollout

These items are intentionally out of scope for the first implementation pass.

- redesigning the app-family build process
- introducing environment-tag workflows
- reworking non-app-family deployment workflows
- path-based optimization if it changes release semantics before parity is proven
- consolidating all three app-family modes into one workflow before the split design is proven

## 12. Recommended Delivery Order

The recommended execution order is:

1. finish and approve this plan
2. finish parity decisions in the behavior document
3. implement and test infra app-release scripts
4. implement and test reusable workflows in `asma-workflows`
5. integrate `asma-app-shell`
6. validate parity with Bitbucket outputs
7. integrate `asma-app-advoca`
8. document final deviations and decommission criteria

## 13. Related Documents

- `_docs/asma-app-family-workflow-behavior.md`
- `_docs/git-tagging-script-flow.md`
- `_docs/reusable-git-tagging-extraction-plan-completed.md`
- `infrastructure/asma-infrastructure/.github/workflows/reusable-backend-deploy.yml`
- `infrastructure/asma-infrastructure/.github/workflows/reusable-backend-hasura-migration.yml`

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
- **DEP-002**: Existing cross-repo checkout pattern already used by `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-backend-deploy.yml` and `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-backend-hasura-migration.yml`.
- **DEP-003**: GitHub secrets for S3 credentials, Hasura endpoints, and Hasura admin secrets for all required environments.
- **DEP-004**: Agreement on whether app-family workflows must preserve legacy commit-type semantics exactly or may adopt the current shared release-gate semantics.
- **DEP-005**: Agreement on which GitHub authentication method will be standard for cross-repo reusable workflow and script checkout in private repositories.

## 5. Files

- **FILE-001**: `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-app-master-release.yml`.
- **FILE-002**: `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-app-pr-preview.yml`.
- **FILE-003**: `/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-app-hotpatch-release.yml`.
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

/Users/igor/carasent/asma-modules/infrastructure/asma-infrastructure/.github/workflows/reusable-backend-hasura-migration.yml
