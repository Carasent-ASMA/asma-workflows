# Git Tagging Script Flow

## Purpose

This document describes the current git tagging design in a compact, workflow-oriented way.

It is written for both humans and AI agents that need to answer these questions quickly:

- what each tagging module is responsible for
- what can be composed safely in CI
- which commands are read-only versus state-changing
- how version and tag resolution works

## Current Entry Points

- [release_gate.py](/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/release_gate.py)
- [git_tagging_plan.py](/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/git_tagging_plan.py)
- [git_tagging_ops.py](/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/git_tagging_ops.py)

## Design Summary

The tagging logic follows a plug-and-play split.

- `release_gate` decides whether release work should continue
- `plan` resolves versions and tags once the workflow has decided to continue
- `ops` performs git mutations

The important design rule is: do not mix release decision logic with git side effects unless a workflow explicitly wants both in the same step.

## Plug-And-Play Principle

The helpers are intentionally composable.

That means a workflow can:

1. stop early in one gate step
2. resolve a version or tag in a later step
3. update files after that
4. push tags only at the end

This is useful when a pipeline needs to:

- calculate a version before building artifacts
- reuse the resolved tag in multiple later jobs
- delay any remote mutation until validation passes
- push one or more tags only after other release actions succeed

In short:

- planning commands are safe to call early
- operations commands should be called only when the workflow is ready to mutate git state

## Module Responsibilities

### Planning Module

[git_tagging_plan.py](/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/git_tagging_plan.py) is read-only.

It is responsible for:

- resolving stable tags
- resolving hotpatch tags
- resolving prerelease tags
- checking whether a tag already exists
- exporting planning outputs through `GITHUB_OUTPUT`

It should not create commits, tags, or remote changes.

### Release Gate Module

[release_gate.py](/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/release_gate.py) is the early release gate.

It is responsible for:

- checking whether release-relevant files changed
- analyzing commit subjects for release relevance
- deciding whether the workflow should continue
- exporting gate outputs such as `code_changed`, `should_publish`, `bump_type`, and `should_continue`

### Operations Module

[git_tagging_ops.py](/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/git_tagging_ops.py) performs git mutations.

It is responsible for:

- configuring git auth and identity
- fetching remote tags
- creating annotated tags
- deleting tags
- pushing tags
- committing files and pushing with tags

It should not decide bump type or choose the next release version.

### Shared Module

[git_tagging_shared.py](/Users/igor/carasent/asma-modules/shared/asma-workflows/.github/scripts/git_tagging_shared.py) contains low-level shared utilities.

It centralizes:

- regex definitions
- semver parsing and bumping
- generic git command helpers
- tag listing and existence checks
- first-free-tag resolution logic

## Read-Only Versus State-Changing Commands

### Read-only planning commands

- `tag-exists`
- `resolve-stable-tag`
- `resolve-next-stable-release`
- `resolve-hotpatch-tag`
- `resolve-prerelease-tag`

### Read-only gate commands

- `check-path-changes`
- `release-gate`

### State-changing operations commands

- `configure-remote-auth`
- `fetch-tags`
- `create-annotated-tag`
- `delete-tag-if-exists`
- `push-tag`
- `commit-and-push-follow-tags`

## Logic Flow

### 1. Release Gate

`release-gate` decides whether the workflow should continue at all.

It combines two checks:

- file-path eligibility
- commit-message release eligibility

Supported strategies:

- `last_commit_only`
- `all_commits_since_last_stable_tag`

The repository uses a broader conventional-commit vocabulary than the release gate itself.

Documented commit types in the repo conventions are:

- `feat`
- `fix`
- `docs`
- `style`
- `refactor`
- `test`
- `chore`
- `perf`
- `ci`
- `build`

Breaking changes are expressed by adding `!` after the type, for example `feat!:` or `refactor!:`.

The current release gate does not treat all conventional commit types as release bumps.

The release-triggering rules are:

- breaking change regex: `^[a-z]+!(\([^)]*\))?:`
- feature regex: `^feat(\([^)]*\))?:`
- patch regex: `^(fix|perf|style|refactor|chore)(\([^)]*\))?:`

That means:

- any `type!:` or `type(scope)!:` becomes `major`
- `feat:` becomes `minor`
- `fix:`, `perf:`, `style:`, `refactor:`, and `chore:` become `patch`
- `docs`, `test`, `ci`, and `build` do not trigger a release by default unless marked as breaking with `!`

Severity order is:

1. `major`
2. `minor`
3. `patch`
4. `none`

Outputs typically written:

- `code_changed`
- `should_publish`
- `bump_type`
- `analysis_strategy`
- `reason_commit`
- `should_continue`

This distinction is important:

- `code_changed=true` means release-relevant files changed
- `should_publish=true` means commit messages requested a semantic release

Examples with the current policy:

- `style: Update tailwind classes` -> `patch`
- `refactor: Simplify cache invalidation` -> `patch`
- `chore: Refresh generated assets` -> `patch`
- `docs: Update release guide` -> no release by default

### 2. Version Resolution

Stable version bumping uses semantic versioning.

Examples:

- `1.2.3` + `major` -> `2.0.0`
- `1.2.3` + `minor` -> `1.3.0`
- `1.2.3` + `patch` -> `1.2.4`

`resolve-next-stable-release` works like this:

1. get latest stable tag if one exists
2. fall back to the provided version when none exists
3. bump according to the requested bump type
4. check for collisions
5. return the first free stable tag

### 3. Stable Tag Allocation

Stable tags use the format `vN.N.N`.

The allocator uses a first-free-candidate strategy.

That means it does not assume the next tag is automatically available. It keeps generating ordered candidates until it finds the first exact tag that does not already exist.

This makes the result deterministic and consistent with hotpatch handling.

### 4. Hotpatch Tag Allocation

Hotpatch tags use the format `vN.N.N-X`.

Hotpatch resolution works like this:

1. extract the stable base tag from the branch name
2. confirm that base tag matches the latest merged stable tag
3. try `<base>-1`, then `<base>-2`, then `<base>-3`, and so on
4. return the first free exact tag

Example:

- existing tags: `v1.2.3-1`, `v1.2.3-3`
- next resolved tag: `v1.2.3-2`

This is important: hotpatch allocation now follows the same first-free principle as stable allocation.

### 5. Prerelease Tag Allocation

Prerelease tags use the format `pr<number>`.

Optional branch validation can enforce that the PR tag is only resolved for allowed branch prefixes.

## Why The Split Exists

The split is not just for code organization. It supports safer workflow composition.

Without the split, a single command would tend to do all of these at once:

- inspect history
- decide a version
- mutate files
- create tags
- push remotes

That is harder to reuse and harder to recover from when a workflow fails mid-run.

With the split:

- planning can happen early and safely
- outputs can be reused by multiple later steps
- mutation can be delayed until the workflow is ready
- the same planning logic can be paired with different release flows

## Recommended Workflow Shape

A typical stable release flow should look like this:

1. run `release_gate.py release-gate`
2. stop early if `should_continue=false`
3. run build and validation steps
4. run `git_tagging_ops.py fetch-tags`
5. run `git_tagging_plan.py resolve-next-stable-release`
6. update versioned files
7. run `git_tagging_ops.py configure-remote-auth` if needed
8. run `git_tagging_ops.py commit-and-push-follow-tags`

This shape keeps git mutation near the end, where failure is cheaper to reason about.

## Minimal Mental Model

If you only remember one thing, remember this split:

- `plan` answers: what tag should exist?
- `release_gate` answers: should release work continue at all?
- `ops` answers: now that we know it, do we want to mutate git?

That is the core plug-and-play principle of the current git tagging design.
