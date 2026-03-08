---
goal: Extract reusable git tagging and push logic from shared workflows into a dedicated Python entrypoint
version: 1.1
date_created: 2026-03-07
last_updated: 2026-03-08
owner: Platform Engineering
status: Completed
tags:
  [github-actions, python, git, tags, reusable-workflows, refactor, completed]
---

# Reusable Git Tagging Extraction

This document keeps only the decisions that should continue to guide future changes. The extraction is complete, and the shared workflows repository is now the source of truth for reusable git-tagging behavior.

## Outcome

- Git-tagging logic belongs in the shared `asma-workflows` repository, not in service repositories.

- Generic git operations are separated from caller-specific release policy.

- Stable, hotpatch, and PR prerelease flows can reuse the same low-level git primitives.

- Mutable environment tags such as `env.dev` and `env.prod` remain out of scope.

## Durable Decisions

- Keep reusable git primitives in a standalone Python entrypoint under `asma-workflows/.github/scripts/`.

- Keep package-manager behavior, version file mutation, and workflow-specific policy outside the generic git helper.

- Make release mode and analysis strategy explicit. Do not hide behavior behind auto-detection.

- Prefer a small command-oriented CLI over a large implicit orchestration script.

- Preserve workflow-friendly outputs and deterministic command behavior for GitHub Actions.

## Supported Release Modes

### Stable

- Tag format: `vX.Y.Z`.

- Version source: highest existing stable tag.

- Analysis strategy must be explicit:

  - `all_commits_since_last_stable_tag`

  - `last_commit_only`

- Bump priority:

  - `major` if any commit matches breaking-change syntax such as `type!:` or `type(scope)!:`

  - `minor` if any commit matches `feat:` or `feat(scope):`

  - `patch` if any commit matches patch-worthy types such as `fix:`, `perf:`, `style:`, `refactor:`, or `chore:` with optional scope

  - `none` otherwise

- If the next stable tag already exists, continue to the first free tag candidate.

### Hotpatch

- Tag format: `vX.Y.Z-N`.

- Base version comes from the branch name and must match `*/vN.N.N`.

- If the branch naming rule is violated, fail fast.

- If previous hotpatch tags exist for that base version, increment the highest `N`.

### PR Prerelease

- Tag format: `pr<prnumber>`.

- Supported by shared git primitives, but creation policy stays with the caller.

- Branch-awareness and trigger conditions are caller-controlled.

## Boundaries

- In scope:

  - remote configuration

  - fetching tags

  - tag existence checks

  - annotated tag creation

  - deleting tags when explicitly requested

  - pushing tags

  - commit-and-push follow-up operations needed by release workflows

- Out of scope:

  - mutable deployment environment tags

  - npm version-file mutation as a generic concern

  - hidden policy decisions based on repository or branch guessing

## Files That Matter

- `asma-workflows/.github/scripts/git_tagging.py` or its split successors own reusable git-tagging behavior.

- `asma-workflows/.github/scripts/npm_publish/workflow.py` keeps npm-specific release logic.

- `asma-workflows/.github/workflows/reusable-npm-publish.yml` remains the caller-facing reusable workflow contract.

## Guardrails For Future Changes

- Do not move shared release logic back into individual service repositories.

- Do not couple generic git helpers to npm-only behavior.

- Do not silently unify GitHub and Bitbucket release semantics; strategy differences must stay explicit.

- Do not include environment-tag workflows in the same abstraction unless they remain clearly separate.

- Prefer CI concurrency controls over allowing uncontrolled version skipping during concurrent releases.

## Recommendation

Future work should extend the shared git-tagging surface area only when the behavior is reusable across repositories and release flows. If a behavior is package-manager specific, deployment-environment specific, or repo-policy specific, keep it in the caller layer.
