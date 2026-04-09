---
goal: Investigate and plan migration of AI release notes from gh copilot CLI to GitHub Models org-attributed inference
version: 1.0
date_created: 2026-04-09
last_updated: 2026-04-09
owner: Platform Engineering
status: Planned
tags:
  - github-models
  - release-notes
  - npm-publish
  - workflows
  - investigation
  - implementation-plan
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This document records the investigation into replacing the current `gh copilot` CLI usage in `shared/asma-workflows/.github/scripts/npm_publish/release_notes.py` with GitHub Models REST inference.

The trigger for this investigation is the current failure mode in GitHub Actions where large rendered prompts cause `OSError: [Errno 7] Argument list too long: 'gh'` before the model request is sent. The goal is to determine whether GitHub Models can remove the CLI argument-size limitation, what authentication model is required, whether free small-model usage is available, and what exact changes would be required in `asma-workflows` when the preferred target is the org-attributed endpoint for `Carasent-ASMA`.

## 1. Investigation Findings

### 1.1 Current Failure Mechanism

The current release-note implementation renders a large prompt and passes it to the Copilot CLI as a command-line argument:

```text
gh copilot -- --model <model> -p <rendered prompt> --silent
```

This means the request is constrained by the operating system process argument-size limit, not only by the model context window.

Observed consequence:

- Large AST context or large commit/file lists can make the rendered prompt too large for `subprocess.run(...)` to launch `gh`.
- Changing from one model to another does not solve this specific failure.
- Prompt truncation is the only safe workaround while the workflow still uses `gh copilot -p ...`.

### 1.2 What GitHub Models Provides

GitHub Models exposes a documented REST inference API that accepts prompts in the HTTP request body instead of in the command-line argument vector.

Relevant endpoints:

- `POST https://models.github.ai/inference/chat/completions`
- `POST https://models.github.ai/orgs/{org}/inference/chat/completions`
- `GET https://models.github.ai/catalog/models`

Documented capabilities relevant to this migration:

- Chat-completions style requests using `model` and `messages`
- Streaming or non-streaming responses
- Standard generation controls such as `max_tokens`, `temperature`, `top_p`, `seed`, and `stop`
- Model catalog lookup, including per-model limits and rate-limit tier metadata
- Organizational attribution and usage tracking when calling the org endpoint

Practical implication:

- Migrating from `gh copilot` CLI to GitHub Models removes the OS argv-size bottleneck because the prompt is sent in JSON over HTTPS.
- It does not remove model token limits, so prompt bounding and summarization still remain necessary.
- The org-attributed endpoint is a first-class documented API, not a workaround, and it aligns better with centralized governance for `Carasent-ASMA`.

### 1.3 Does GitHub Models Provide Free Small Models?

Yes, but the exact answer is more nuanced than simply "small models are free."

Findings from GitHub documentation:

- All GitHub accounts receive included free but rate-limited GitHub Models usage.
- Free usage is intended for prototyping and experimentation.
- Billing for GitHub Models is separate from GitHub Copilot billing.
- Free usage limits vary by model tier and by GitHub Copilot plan.
- GitHub documentation explicitly states that all supported models are available under the free offering, but availability and quotas differ by plan and model family.

What this means in practice:

- Smaller models generally have better free limits than larger models.
- Free usage is not unlimited.
- Some model families are not available on lower-tier plans even under the free quota.

Examples from the current docs:

- Generic `low` tier models have higher free request/day limits than `high` tier models.
- `gpt-5-mini`, `gpt-5-nano`, `gpt-5-chat`, and related mini-family models are documented with free quotas for Copilot Pro, Business, and Enterprise plans, but the table shows `Not applicable` for Copilot Free.
- Paid GitHub Models usage enables higher rate limits and larger context windows.

Conclusion for `asma-workflows`:

- GitHub Models can support a low-cost release-notes use case.
- A smaller model such as `openai/gpt-4o-mini` or `openai/gpt-5-mini` is a reasonable target, but the exact default should be validated against the live catalog and organization policy before rollout.

### 1.4 Authentication Model

GitHub Models authentication is different from the current `gh copilot` CLI path.

#### Actions Authentication

GitHub quickstart documentation explicitly shows GitHub Actions using the built-in `GITHUB_TOKEN` with:

- workflow/job permission `models: read`
- `Authorization: Bearer $GITHUB_TOKEN`

This is the most important finding for `asma-workflows`:

- No dedicated `COPILOT_TOKEN` secret is required for the GitHub Models API path in GitHub Actions.
- The reusable workflow must add `models: read` to the `publish_release` job permissions.
- For the org-attributed endpoint, the workflow must run in a repository that belongs to `Carasent-ASMA`, and GitHub Models must be enabled for that organization.

#### Local or Manual Execution

For local manual API calls, GitHub documentation says a personal access token is required.

Required permission model:

- PAT with `models` scope, or
- fine-grained PAT / GitHub App token with `models: read`

Additional org-attributed requirement:

- The caller must be a member of `Carasent-ASMA` and the organization must have models enabled.

#### Existing `COPILOT_TOKEN`

The existing `COPILOT_TOKEN` secret is useful for the current `gh copilot` CLI flow, but it is not the documented authentication method for GitHub Models inference.

Recommendation:

- Do not rely on `COPILOT_TOKEN` for a GitHub Models implementation.
- Keep it only if the workflow temporarily supports both backends during migration.

### 1.5 Organizational Enablement Constraints

GitHub Models is not purely a code change.

Operational prerequisites from the docs:

- GitHub Models must be enabled for the repository and/or organization.
- For organizations and enterprises, owners can control which models are allowed.
- Paid usage is disabled by default and must be explicitly enabled if higher quotas are required.
- The org-attributed endpoint requires the request to be attributed to a specific org login and is intended for organization-level usage tracking.

Implication:

- A code-only migration is insufficient if the org has not enabled GitHub Models or if the chosen model is blocked by policy.
- If `Carasent-ASMA` wants centralized visibility of usage, budgets, and model governance, the org-attributed endpoint is the correct primary path.

### 1.6 What Changes in the Current Script

Current implementation characteristics:

- backend: `gh copilot`
- transport: CLI argument via `-p`
- auth: `GH_TOKEN` or `COPILOT_TOKEN`
- model naming: short CLI names such as `gpt-5-mini`

Target implementation characteristics:

- backend: GitHub Models REST inference via the org-attributed endpoint
- transport: HTTP POST body to `https://models.github.ai/orgs/Carasent-ASMA/inference/chat/completions`
- auth in Actions: `GITHUB_TOKEN` with `models: read`
- model naming: full catalog IDs such as `openai/gpt-4.1`
- org attribution: `Carasent-ASMA`

Required code changes:

- Replace `subprocess.run(["gh", "copilot", ...])` with HTTP inference calls.
- Build the endpoint URL from an organization-aware configuration, defaulting to `Carasent-ASMA` for workflow execution.
- Map current short model names to GitHub Models catalog IDs.
- Resolve the auth token differently for Actions vs local execution.
- Add HTTP error handling for `401`, `403`, `422`, `429`, and `5xx` failures.
- Preserve the current commit-summary fallback when AI generation fails.
- Keep prompt truncation because request-body transport removes argv limits but not model input-token limits.
- Avoid silently falling back from the org-attributed endpoint to the non-org endpoint unless an operator explicitly opts into that behavior.

### 1.7 Recommended Migration Strategy

Recommended direction:

- Use GitHub Models REST inference for release-note generation through the org-attributed endpoint for `Carasent-ASMA`.
- Keep the current release-notes prompt template file.
- Continue bounding prompt size.
- Use the built-in `GITHUB_TOKEN` in GitHub Actions.
- Add `models: read` permission to the release job.
- Keep the non-org endpoint only as an explicit fallback option, not as the default path.

Reasoning:

- It solves the current CLI argument-size failure directly.
- It avoids dependence on undocumented Copilot inference behavior.
- It removes the need for a separate `COPILOT_TOKEN` secret in the GitHub Actions path.
- It adds organization-level attribution and usage tracking, which is useful because `Carasent-ASMA` controls the org and can govern model access centrally.
- It is aligned with GitHub’s documented API surface.

## 2. Requirements & Constraints

- **REQ-001**: AI release-note generation must no longer depend on command-line prompt transport.
- **REQ-002**: The migration must preserve the existing commit-summary fallback behavior if AI generation fails.
- **REQ-003**: GitHub Actions should use the repository-provided `GITHUB_TOKEN` when possible instead of requiring a dedicated extra secret.
- **REQ-004**: The implementation must continue to support configurable model selection.
- **REQ-005**: The implementation must remain compatible with the current reusable npm publish workflow.
- **REQ-006**: GitHub Actions inference requests should be attributed to the `Carasent-ASMA` organization by default.
- **SEC-001**: Tokens must only be sent in the `Authorization` header and must not be logged.
- **SEC-002**: The workflow must use the minimum permission needed for inference: `models: read`.
- **CON-001**: GitHub Models must be enabled for the repository or organization before rollout can succeed.
- **CON-002**: Model access and free quotas vary by Copilot plan and organization policy.
- **CON-003**: The API removes argv-size limits, but model token-per-request limits still apply.
- **CON-004**: Billing for GitHub Models is separate from GitHub Copilot billing.
- **CON-005**: Local callers cannot use the org-attributed endpoint unless they are members of `Carasent-ASMA` and the org has enabled models for their usage path.
- **GUD-001**: Prefer Python standard library HTTP clients over adding third-party dependencies just for a single POST request.
- **GUD-002**: Prefer the documented org-attributed endpoint first because `Carasent-ASMA` has full control over org policy, attribution, and billing.
- **PAT-001**: Preserve the existing `release_notes_prompt.md` prompt authoring flow so prompt maintenance stays repository-local.

## 3. Implementation Steps

### Implementation Phase 1

- GOAL-001: Prepare the workflow contract and org-attributed backend switch for GitHub Models.

- TASK-001: Update `shared/asma-workflows/.github/workflows/reusable-npm-publish.yml` so the `publish_release` job includes `models: read` in its permissions block alongside existing permissions.
- TASK-002: Add a backend selection mechanism in `shared/asma-workflows/.github/scripts/npm_publish/release_notes.py`, for example an `AI_RELEASE_NOTES_BACKEND` variable with `models-org`, `models`, and `copilot` as supported values, defaulting to `models-org` only after rollout confidence is established.
- TASK-003: Define a deterministic mapping from current short model names (`gpt-4.1`, `gpt-4o-mini`, `gpt-5-mini`) to GitHub Models IDs (`openai/gpt-4.1`, `openai/gpt-4o-mini`, `openai/gpt-5-mini`) inside `release_notes.py`.
- TASK-004: Add configuration for the organization login, defaulting to `Carasent-ASMA` in workflow execution, and validate that the value is present before building the org-attributed endpoint.
- TASK-005: Add preflight documentation or script comments that state GitHub Models must be enabled for `Carasent-ASMA` and that the chosen model must be allowed by org policy.

### Implementation Phase 2

- GOAL-002: Replace the CLI transport with GitHub Models HTTP inference against the `Carasent-ASMA` org endpoint.

- TASK-006: Add a new function in `shared/asma-workflows/.github/scripts/npm_publish/release_notes.py` that sends `POST https://models.github.ai/orgs/Carasent-ASMA/inference/chat/completions` or the equivalent org-configured URL with a JSON payload and parses `choices[0].message.content`.
- TASK-007: Use Python standard library HTTP tooling (`urllib.request` and `json`) unless there is a strong reason to add an external dependency.
- TASK-008: Resolve the auth token for GitHub Models by preferring `GITHUB_TOKEN` in GitHub Actions and allowing PAT-based execution locally for users who are members of `Carasent-ASMA`.
- TASK-009: Preserve existing prompt rendering by using `release_notes_prompt.md` as the prompt source, rendered into either a single `user` message or a `system` plus `user` split.
- TASK-010: Keep prompt truncation logic in place and align it to model token constraints rather than CLI argv constraints alone.
- TASK-011: Add handling for API status codes `401`, `403`, `422`, `429`, and `5xx`, converting them into the same fallback path currently used for `gh copilot` failures, with error messages that distinguish org-policy failures from generic inference failures.

### Implementation Phase 3

- GOAL-003: Validate org-attributed rollout behavior and remove unnecessary Copilot-specific dependencies.

- TASK-012: Extend `shared/asma-workflows/.github/scripts/tests/test_release_notes.py` with tests for auth resolution, request-body creation, model-ID mapping, org-endpoint URL construction, response parsing, and fallback on HTTP errors.
- TASK-013: Run a pilot release from a low-risk package such as `asma-ui-icons` using the org-attributed GitHub Models backend and inspect workflow summaries for request success, fallback behavior, response quality, and usage attribution under `Carasent-ASMA`.
- TASK-014: After successful rollout, make `COPILOT_TOKEN` optional only for legacy fallback or remove Copilot-specific wiring from `shared/asma-workflows/.github/workflows/reusable-npm-publish.yml` if the CLI backend is retired.
- TASK-015: Document the final operational auth path in `shared/asma-workflows/readme.md` so callers understand that `models: read` plus `GITHUB_TOKEN` is the preferred GitHub Actions path and that requests are attributed to `Carasent-ASMA` by default.

## 4. Alternatives

- **ALT-001**: Keep using `gh copilot` and rely only on prompt truncation. Rejected because it does not remove the core transport limitation and still depends on CLI-specific behavior.
- **ALT-002**: Use the org-attributed endpoint first (`/orgs/{org}/inference/chat/completions`). Selected because `Carasent-ASMA` has full control over org policy, can track usage centrally, and can align billing and model governance with the release workflow.
- **ALT-003**: Use the non-org endpoint first (`/inference/chat/completions`). Deferred to contingency use only because it gives up org attribution and makes governance weaker even though it is otherwise technically simpler.
- **ALT-004**: Call OpenAI or Azure APIs directly. Rejected for the first migration because GitHub Models already provides a documented GitHub-native inference path and simpler GitHub Actions auth.
- **ALT-005**: Continue using `COPILOT_TOKEN` as the main secret. Rejected because GitHub Models documentation points to `GITHUB_TOKEN`, PATs with `models` scope, or GitHub App tokens with `models: read`, not Copilot-specific tokens.

## 5. Dependencies

- **DEP-001**: `shared/asma-workflows/.github/scripts/npm_publish/release_notes.py` must be updated to support HTTP inference.
- **DEP-002**: `shared/asma-workflows/.github/workflows/reusable-npm-publish.yml` must grant `models: read` in the release job.
- **DEP-003**: GitHub Models must be enabled for the `Carasent-ASMA` organization and for the repositories that will invoke the reusable workflow.
- **DEP-004**: The target model ID must be available in the GitHub Models catalog and allowed by `Carasent-ASMA` organization policy.
- **DEP-005**: If local manual runs are required, developers need a PAT with `models` scope or an equivalent GitHub App token with `models: read`, and they must be members of `Carasent-ASMA` to use the org endpoint.

## 6. Files

- **FILE-001**: `shared/asma-workflows/.github/scripts/npm_publish/release_notes.py` — main migration target from CLI transport to REST inference.
- **FILE-002**: `shared/asma-workflows/.github/scripts/tests/test_release_notes.py` — unit tests for prompt rendering, auth resolution, API calls, and fallback behavior.
- **FILE-003**: `shared/asma-workflows/.github/workflows/reusable-npm-publish.yml` — workflow permissions and env wiring.
- **FILE-004**: `shared/asma-workflows/.github/scripts/npm_publish/release_notes_prompt.md` — prompt template to preserve or split into structured chat messages.
- **FILE-005**: `shared/asma-workflows/readme.md` — optional documentation update for the new auth model, org attribution behavior, and workflow usage.
- **FILE-006**: `shared/asma-workflows/_docs/github-models-release-notes-investigation-and-implementation-plan.md` — this investigation and implementation plan.

## 7. Testing

- **TEST-001**: Unit test that model short names map to expected GitHub Models catalog IDs.
- **TEST-002**: Unit test that request payloads are built with `model`, `messages`, and bounded prompt content.
- **TEST-003**: Unit test that org-endpoint URL construction produces `https://models.github.ai/orgs/Carasent-ASMA/inference/chat/completions` when org attribution is enabled.
- **TEST-004**: Unit test that `GITHUB_TOKEN` is used for GitHub Models inference when present in GitHub Actions-like execution.
- **TEST-005**: Unit test that PAT-based execution works for local/manual invocations.
- **TEST-006**: Unit test that `401`, `403`, `422`, `429`, and `5xx` API failures produce AI fallback instead of workflow termination.
- **TEST-007**: Unit test that response parsing extracts `choices[0].message.content` and rejects empty output.
- **TEST-008**: End-to-end pilot validation in a real package workflow such as `asma-ui-icons`.

## 8. Risks & Assumptions

- **RISK-001**: The short model names currently used by the Copilot CLI may not map one-to-one to GitHub Models catalog IDs and may need per-model validation.
- **RISK-002**: Free quotas may be insufficient for heavy release traffic, especially on higher-cost model families.
- **RISK-003**: Organization policy may block the preferred model even if the model exists in the public catalog.
- **RISK-004**: Output quality may differ between the current Copilot CLI backend and raw GitHub Models inference, requiring prompt tuning.
- **RISK-005**: The repo or org may not have GitHub Models enabled, causing `403` failures until platform configuration is completed.
- **RISK-006**: Local testing of the org-attributed endpoint may fail for developers who are not members of `Carasent-ASMA`, even if generic GitHub Models access works elsewhere.
- **ASSUMPTION-001**: The current reusable workflow has access to `GITHUB_TOKEN` and can be updated to add `models: read`.
- **ASSUMPTION-002**: GitHub-hosted runners can reach `https://models.github.ai` without additional network setup.
- **ASSUMPTION-003**: The release-notes use case does not need advanced tool-calling or streaming features.
- **ASSUMPTION-004**: Python standard library HTTP support is sufficient for the first implementation.

## 9. Recommendation

The recommended next implementation is:

1. Add `models: read` to the `publish_release` job in `reusable-npm-publish.yml`.
2. Implement a GitHub Models backend in `release_notes.py` using the org-attributed endpoint for `Carasent-ASMA`.
3. Configure the workflow so org attribution defaults to `Carasent-ASMA`, while keeping the non-org endpoint available only as an explicit contingency path.
4. Use `GITHUB_TOKEN` in Actions and PATs locally for developers who are members of `Carasent-ASMA`.
5. Keep prompt truncation and fallback behavior.
6. Pilot on one package before removing any remaining `gh copilot` path.

This approach removes the CLI argument-size failure without introducing a new secret requirement for the GitHub Actions path, and it keeps usage attribution, model governance, and billing control with `Carasent-ASMA`.

## 10. Related Specifications / Further Reading

- [GitHub Models quickstart](https://docs.github.com/en/github-models/quickstart)
- [GitHub Models inference API](https://docs.github.com/en/rest/models/inference)
- [GitHub Models catalog API](https://docs.github.com/en/rest/models/catalog)
- [Prototyping with AI models](https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models)
- [GitHub Models billing](https://docs.github.com/en/billing/managing-billing-for-your-products/about-billing-for-github-models)
- [About GitHub Models](https://docs.github.com/en/github-models/about-github-models)
