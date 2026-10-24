---
applyTo: '**/*.{ts,tsx,js,jsx,py,sql}'
---
<!-- Generated from .github/instructions/coding-standards.instructions.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Shared Coding Standards

Apply these standards across all coding tasks unless a scoped instruction file provides stricter rules.

## Authority and scope

- Follow the user's request within the authority granted by higher-level policy.
- Apply an owning decision or instruction within its stated domain and scope; scoped rules refine shared guidance for that scope.
- Resolve conflicts by authority, scope and explicit supersession recorded by the owner. File recency or discovery order does not supersede an existing decision.
- This shared file supplies defaults where no applicable scoped rule or owning decision governs.

## Workspace File Location Policy

- Workspace definition files (`*.code-workspace`) must live only under `root/workspaces/*`.
- Do not create or modify workspace files outside `workspaces/`.

## Type Safety Policy (STRICT)

- Never use `# type: ignore`.
- Only allowed exception: `# type: ignore[import-untyped]` for external untyped packages.
- Do not silence errors by default; resolve root cause.
- For application code authored as TypeScript or JavaScript, use TypeScript and do not introduce JavaScript unless the user explicitly requests it. This rule applies to new TS/JS app code; Python, SQL, shell, infrastructure, and other runtimes follow their own conventions.
- Follow the target Python, SQL, and runtime-specific instructions for those files.

Use these patterns instead:

- Cast based on inspected structure: `cast(Optional[list[str]], data.get("key"))`
- Guard before use: `if value is not None and isinstance(value, list):`
- Document expected structure in docstrings.
- Validate input with explicit, actionable error messages.

## Structure and Size Targets

- File size target: 200–400 lines, hard limit 600.
- Function size target: 10–50 lines, hard limit 100.
- Split files/functions when responsibilities diverge.
- Organize by feature/capability, not generic buckets.

## Design Guidelines

- Prefer small composable functions for transformations.
- Use classes only for state, lifecycle, orchestration, or caches.
- Avoid classes that only wrap static helpers.
- One clear responsibility per file/function/class.

## Naming Guidelines

- Functions: verb + noun (`create_server_group`, `validate_pattern`).
- Classes: clear nouns (`DatabaseInspector`, `PipelineGenerator`).
- Variables: descriptive nouns (`excluded_databases`, not `exc`).
- Constants: `UPPER_CASE_WITH_UNDERSCORES`.
- Files: specific names matching responsibility; avoid `utils.py`, `common.py`, `misc.py`.

## Type Hints and Documentation

- Require type hints on all new/changed public functions and methods.
- Prefer precise types (`TypedDict`, `Literal`, explicit containers) for domain structures.
- Public functions require docstrings: one-line summary, args, returns, short example where useful.

## Linking Doc Comments to Specs/Docs

When a doc comment (JSDoc/TSDoc, or a Python docstring) documents a feature that is specified in a design/spec/architecture doc, add a machine-navigable pointer to the exact section so a reader can jump straight from the code to the source of truth — as well as the human-readable citation.

- Add one `@see` line per referenced doc, using a **workspace-relative path with a line number**: `@see asma-modules/_docs/.../spec-file.md:35 — what it covers`. The `path:line` form is copy-pasteable into VS Code Quick Open (Cmd+P honors the trailing `:line`) and resolves for every contributor.
- Keep the stable textual citation alongside it (`REQ-002`, `BHV-005`, `§8`, etc.). Requirement/section IDs do not rot; the `:line` is a navigation convenience that drifts when the doc is edited, so never rely on it alone.
- Relative paths only. Never use absolute paths, `file://`, or `vscode://` URLs — they hardcode one machine, are dead links for everyone else and in review, and are not portable.
- Point at the most specific anchor available (the requirement/section's line), not just the file top.

## Error Handling and Validation

- Validate inputs early with clear failures.
- Use specific exceptions (`ValueError`, `TypeError`, etc.).
- Keep user-facing errors concise and actionable.
- Log detailed diagnostics only where appropriate.

## Backend Service Error Handling (Node/Bun)

These rules live in the [`backend-request-context-and-errors`](../skills/backend-request-context-and-errors/SKILL.md) skill, auto-loaded for backend repos via [`backend-service.instructions.md`](backend-service.instructions.md). Read the skill before writing or changing any backend handler/middleware/helper (reference services: `auth/asma-njs-auth`, `editor/asma-bunjs-editor`).

## Backend Request Context (Node/Bun)

Same single source of truth: the [`backend-request-context-and-errors`](../skills/backend-request-context-and-errors/SKILL.md) skill holds the hook catalogue and the `use*` / `make*` / `set*` pattern. See [`backend-service.instructions.md`](backend-service.instructions.md) for the pointer.

## API Input Validation (OpenAPI + Zod + ArkType)

Full rules live in the [`api-validation-openapi-zod-arktype`](../skills/api-validation-openapi-zod-arktype/SKILL.md) skill. Decision rationale: [ADR-0004](asma-modules/_docs/adr/adr-api-0004-api-input-validation-openapi-zod-arktype.md). Read the skill before adding or changing any REST route schema or request/response validation.

## Security and Data Safety

- Never hardcode credentials, tokens, or secrets.
- Use environment variables or secret managers.
- Prevent injection risks with validation/parameterization.
- Avoid unsafe dynamic execution and unvalidated path operations.

## YAML Editing Guidance

Full YAML editing rules live in [`yaml.instructions.md`](yaml.instructions.md) (auto-loaded for `*.yml`/`*.yaml`).

## Performance and Reliability

- Avoid redundant expensive operations (duplicate I/O, connections, parsing).
- Prefer context managers for resources.
- Keep behavior deterministic and reproducible.
- Prioritize clarity first; optimize when there is evidence of bottlenecks.

## Mandatory Post-Generation Quality Gate

After any code generation or modification, run and resolve all relevant quality checks before considering the task done.

Required checks (run what exists in the target project):

1. Tests (unit/integration where available)
2. Type checks
    - Python: Pylance/Pyright/mypy (as configured)
    - TypeScript: `tsc` and project type checks
3. Lint/warnings
    - Python: `ruff` (and other configured linters)
    - JS/TS: `eslint` (and other configured linters)

Rules:

- Fix all new and existing errors/warnings in scope of the task.
- Do not ignore failing checks or silence warnings without a strong, explicit reason.
- If tests do not exist for changed behavior, emit a warning and add appropriate tests.
- If no test framework exists, emit a warning that tests are missing and note risk.
- Do not declare completion until checks pass, or clearly report blockers with exact failing output.
- For CLI/command changes, always add or update both unit tests and E2E-style tests in the same change.

Execution behavior for tooling:

- Avoid repeated environment setup/configuration loops.
- If environment setup is canceled/unavailable, continue with available checks and report the missing step as a blocker.
- When you change `AGENTS.md`, `.github/copilot-instructions.md`, or any `.github/instructions/*.md`, run `python3 _tools/scripts/check-instruction-duplicates.py` to verify no canonical rule drifted into a second home.

## Review Checklist (AI Quick Pass)

Before finishing a change:

- [ ] File/function sizes within limits.
- [ ] Type hints present and accurate.
- [ ] Doc comments that cite a spec/design doc include a relative `@see path:line` pointer plus the stable textual citation.
- [ ] No forbidden `# type: ignore` usage.
- [ ] Naming is explicit and domain-specific.
- [ ] Validation and errors are clear.
- [ ] No credentials/secrets in code.
- [ ] Changes scoped to request.
- [ ] Tests run; missing tests added or flagged.
- [ ] Type checks pass.
- [ ] Lint checks pass.
