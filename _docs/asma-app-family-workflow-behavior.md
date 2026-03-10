# ASMA App Family Workflow Behavior

## Purpose

This document captures the current release behavior for the private `asma-app-*` family as implemented today in Bitbucket pipelines and legacy shell scripts.

It also records what has already been introduced on the GitHub Actions side, so future reusable workflows in `asma-workflows` can migrate behavior without changing release semantics by accident.

## Scope

This document is about the app-family frontend release flow used by repositories such as `asma-app-shell` and `asma-app-advoca`.

It covers:

- stable releases from `master`
- PR preview releases for active pull requests
- hotpatch releases from `releases/v*.*.*`
- S3 asset publication
- `app_versions` updates through directory Hasura
- the new shared release gate that has already been added in GitHub Actions

It does not define backend deployment, ArgoCD deployment, or Hasura migration flows for backend services.

## Source Inputs

The behavior described below comes from these current sources:

- `asma-app-shell/bitbucket-pipelines.yml`
- `asma-app-advoca/bitbucket-pipelines.yml`
- `asma-infrastructure/legacy-asma-scripts/prBitbucketScripts/*`
- `asma-workflows/.github/workflows/reusable-npm-publish.yml`
- `asma-workflows/.github/scripts/release_gate.py`
- `asma-workflows/_docs/git-tagging-script-flow.md`

## Current Bitbucket Trigger Matrix

Both `asma-app-shell` and `asma-app-advoca` use the same Bitbucket pipeline shape.

### Pull Requests

Trigger:

- `pull-requests: '**'`

Entry script:

- `prBitbucketPrerelease.sh`

Result:

- build preview assets on every commit while the PR is active
- publish assets to S3 under a PR-scoped version folder
- update directory `app_versions`
- do not create a stable git tag

### Master

Trigger:

- `branches: master`

Entry script:

- `prBitbucketRelease.sh`

Result:

- determine the next stable version from commit-message semantics and existing tags
- build the app
- publish assets to S3 under the stable version folder
- update directory `app_versions`
- create and push a git tag `vX.Y.Z`

### Hotpatch Branches

Trigger:

- `branches: releases/v*.*.*`

Entry script:

- `patchRelease.sh`

Result:

- validate that the branch is tied to the latest merged stable release
- build a hotpatch asset version
- publish assets to S3
- update directory `app_versions`
- create and push a git tag `vX.Y.Z-N`

## Shared Legacy Runtime Behavior

All three Bitbucket flows share the same operational pattern.

### Bootstrap

Each Bitbucket step:

- installs `tzdata`, `awscli`, and `jq`
- downloads the release scripts from `s3://asma-app-cdn/asma-scripts/<script-version>/prBitbucketScripts/`
- makes the scripts executable
- sets `NODE_OPTIONS=--max_old_space_size=6144`

### Build

The build script `prBitbucketBuildSendToS3AndHasura.sh`:

- installs `pnpm` globally
- runs `pnpm install`
- runs `pnpm run build`
- resolves `serviceName` from `package.json`

### S3 Publishing

Artifacts are published to:

```text
s3://asma-app-cdn/<serviceName>/<VERSION>/
```

Before upload, the legacy helper deletes any existing folder for the same version and then re-uploads the new build.

That means repeated runs for the same version replace the previously uploaded asset set.

### Directory Hasura Updates

After the build, the legacy flow calls `revman_insert_and_clean_new_app_version` against all three directory environments:

- `web.dev`
- `web.stage`
- `web`

The mutation payload includes:

- service name
- version
- PR id in the form `pr<number>`
- last commit message
- Jira key when one is detected

For stable versions in plain `X.Y.Z` form, the legacy scripts also update `customer_user_app_version` in `web.dev` for the `ADOPUS` and `ADCURIS` journals.

## Stable Release Behavior On Master

The `master` flow is implemented by `prBitbucketRelease.sh`.

### Version Decision

The legacy script reads the last commit message and maps it to a bump type.

Legacy bump rules:

- `major`: `feat!`, `fix!`, `docs!`, `style!`, `refactor!`, `hotfix!`, `chore!`, `revert!`, `ci!`
- `minor`: `feat`
- `patch`: `fix`, `docs`, `style`, `refactor`, `hotfix`, `chore`, `revert`, `ci`, and merge commit subjects beginning with `Merged` or `Merge`
- anything else fails the script

The stable version is then resolved from the latest stable tag `vX.Y.Z`.

If the current commit is already tagged, the script reuses that version instead of incrementing again.

### PR Enforcement On Master

The master release flow extracts the PR id from the merge commit message.

Direct commits to `master` are treated as invalid by the helper that parses the PR id, so the legacy flow assumes releases come through PR merge commits.

### Stable Release Sequence

Current effective sequence:

1. Inspect the last commit message.
2. Determine `major`, `minor`, or `patch`.
3. Resolve the next stable version from the latest stable tag.
4. Build the app.
5. Upsert and clean the new app version in directory Hasura.
6. Delete any existing S3 folder for that version.
7. Upload the new build to S3.
8. Create git tag `vX.Y.Z`.
9. Push tags.

## PR Preview Behavior

The PR flow is implemented by `prBitbucketPrerelease.sh`.

### Version Naming

PR builds use:

```text
VERSION=pr<BITBUCKET_PR_ID>
```

Example:

```text
pr123
```

This means preview assets are uploaded to:

```text
s3://asma-app-cdn/<serviceName>/pr123/
```

### PR Commit Policy

Even though the PR flow does not create a stable git tag, it still validates the last commit message with the same conventional-commit mapping used by the stable release script.

If the commit message does not match the expected format, the PR release script exits.

### PR Release Sequence

Current effective sequence:

1. Inspect the last commit message.
2. Require it to match the legacy release commit format.
3. Set `VERSION=pr<number>` from the Bitbucket PR id.
4. Build the app.
5. Upsert and clean the new app version in directory Hasura.
6. Delete any existing S3 folder for that PR version.
7. Upload the new build to S3.
8. Do not create or push a stable git tag.

The practical effect is that every new commit on an open PR refreshes the same PR-scoped asset folder.

## Hotpatch Behavior

The hotpatch flow is implemented by `patchRelease.sh`.

### Branch Rule

Hotpatch branches must match:

```text
releases/vX.Y.Z
```

The stable version in the branch name must equal the latest merged stable tag visible on the branch.

If it does not, the script fails fast.

### Hotpatch Versioning

The script looks for the latest existing hotpatch tag matching the same stable base.

Examples:

- branch: `releases/v1.2.3`
- existing tags: `v1.2.3-1`, `v1.2.3-2`
- next hotpatch version: `1.2.3-3`

If no hotpatch tag exists yet, the first hotpatch version becomes `1.2.3-1`.

If the current commit is already tagged with the stable base version, the script exits early.

### Hotpatch Release Sequence

Current effective sequence:

1. Validate the branch naming rule.
2. Validate that the branch base version equals the latest merged stable tag.
3. Resolve the next hotpatch suffix `-N`.
4. Build the app.
5. Upsert and clean the new app version in directory Hasura.
6. Delete any existing S3 folder for that hotpatch version.
7. Upload the new build to S3.
8. Create git tag `vX.Y.Z-N`.
9. Push tags.

## Behavior Already Being Shared In GitHub Actions

The current shared GitHub Actions work in `asma-workflows` has already extracted the reusable git-tagging building blocks into Python entrypoints.

Relevant shared pieces:

- `release_gate.py`
- `git_tagging_plan.py`
- `git_tagging_ops.py`
- `git_tagging_shared.py`

The reusable workflow that currently uses this is `reusable-npm-publish.yml`.

### What Has Been Added So Far

For the `asma-app-*` migration, the main new shared behavior that exists today is the release gate.

The release gate currently:

- analyzes commit messages before the workflow continues
- outputs `should_continue`, `should_publish`, `bump_type`, and related metadata
- uses the strategy `all_commits_since_last_stable_tag`
- is intended to support file-pattern change checks

### Important Current Detail

In the current implementation of `release_gate.py`, path-based gating is intentionally disabled.

That means the current gate behaves as a commit-message gate, not a combined file-change plus commit-message gate, even though workflow callers still pass `--patterns`.

Today, `code_changed` is effectively derived from `should_publish`.

## Release Gate Semantics Compared To Legacy Bitbucket Logic

The new shared release gate is not identical to the legacy Bitbucket commit parser.

### Shared Release Gate Commit Rules

Current GitHub Actions release-gate rules:

- `major`: any conventional commit with `!`, for example `feat!:` or `refactor(scope)!:`
- `minor`: `feat`
- `patch`: `fix`, `perf`, `style`, `refactor`, `chore`
- `none`: everything else unless it is breaking with `!`

### Differences From Legacy App Pipelines

Compared with the existing Bitbucket scripts, the shared release gate currently does not treat these as patch-worthy by default:

- `docs`
- `hotfix`
- `revert`
- `ci`
- merge commit subjects such as `Merge` or `Merged`

Compared with the legacy scripts, the shared release gate does treat this as patch-worthy by default:

- `perf`

This matters because a repository migrated from Bitbucket to the shared release gate may observe different release/no-release outcomes unless the gate rules are aligned intentionally.

## What Still Needs To Be Added For Full `asma-app-*` Migration

At the time of writing, the shared GitHub Actions work does not yet reproduce the full app-family release flow.

Still to be added on top of the release gate:

- stable app build orchestration for `master`
- PR preview asset publication under `pr<number>/`
- hotpatch branch handling for `releases/v*.*.*`
- S3 upload and replace behavior for frontend assets
- directory Hasura `app_versions` updates
- journal-specific `customer_user_app_version` updates for stable releases
- repository-specific enforcement around PR merge commits and PR id capture

## Recommended Migration Rule

When the reusable `asma-app-*` workflow is implemented in GitHub Actions, preserve the existing runtime behavior first and only then decide which legacy quirks should be normalized.

In practice that means:

1. keep trigger semantics explicit for `master`, PRs, and `releases/v*.*.*`
2. keep S3 and Hasura side effects outside the generic tagging helpers
3. reuse the shared tagging and release-gate modules only for the parts that are actually generic
4. document any intentional semantic changes, especially commit-type mapping differences

## Current Summary

The legacy Bitbucket flow for `asma-app-*` apps is a release-and-deploy flow, not only a tagging flow.

It combines version resolution, frontend build, S3 publication, directory Hasura updates, and optional stable or hotpatch tagging.

The new shared GitHub Actions implementation has started with reusable tagging primitives and a release gate. For app-family workflows, the currently added piece is the release gate and its change-detection boundary, while the app-specific S3 and Hasura release behavior still needs to be migrated separately.
