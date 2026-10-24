---
description: "ASMA CLI command-line interface rules for work in _tools/asma-cli and tasks that mention asma cli, asma commands, or command-line tooling."
applyTo: "_tools/asma-cli/**"
---
<!-- Generated from .github/instructions/asma-cli.instructions.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# ASMA CLI Development

Apply these rules when working on ASMA CLI implementation (`_tools/asma-cli/**`).

- Canonical term: `ASMA CLI`.
- Canonical location: `asma-modules/_tools/asma-cli/`.
- If a task says `asma` or `asma-related` and the intent is command-line tooling, treat ASMA CLI as the default target unless the user clearly points to another subsystem.
- The parent `.github/` directory is the shared source for instructions, prompts, agents, and skills; submodule `.github/` entries may be symlinked back to it.

## Development Principles

- Keep CLI behavior beginner-friendly and guided.
- Prefer one-command setup and predictable outputs.
- Keep safety defaults enabled (protected branch guardrails, Jira-gated feature branching).
- Use `--repo` syntax for repo-aware commands.
- During pre-release development, backward compatibility is not required; replace old command shapes immediately when new UX is chosen.

## Python-Specific Rules (STRICT)

1. Never use `# type: ignore` (exception: `# type: ignore[import-untyped]` for untyped packages).
2. Do not use `Any` or unknown/untyped values in new code.
3. Use explicit Python type annotations for all function signatures and key variables.
4. Prefer `dict[str, object]`, typed dataclasses, and typed helper functions.
5. For third-party libraries without type info, declare explicit typed wrappers/adapters.
6. Fix type issues at the root:
   - Cast after structure inspection: `cast(Optional[list[str]], data.get("key"))`.
   - Guard before use: `if value is not None and isinstance(value, list):`.
   - Document expected input/output structure in docstrings.
   - Validate inputs with explicit, actionable error messages.
7. Keep functions focused and reasonably small; split large orchestration logic into helpers.
8. Use descriptive naming (verb+noun for functions, clear nouns for classes/variables).

## Structure Limits

- Maximum file size: 500 lines.
- Maximum function size: 50 lines.
- Prefer domain split:
  - `commands/` for Click command groups.
  - Reusable helpers in dedicated modules (`completion`, commit helpers, shared UI helpers).

## Code Generation Guidelines

1. Default to Python for non-trivial logic.
2. Execute commands in the shell selected for that process or tool.
3. Keep scripts portable when the project requires portability; do not impose Fish syntax on POSIX/zsh tools or POSIX syntax on interactive Fish sessions.
4. Label shell-specific examples and validate against the shell that actually executes them.

When writing automation files:

1. Place Python scripts in `scripts/` when applicable.
2. Make scripts executable: `chmod +x scripts/*.py`.
3. Add shebang: `#!/usr/bin/env python3`.
4. Use type hints and concise docstrings.

When writing build/config helpers:

1. Target ES2020+ output assumptions.
2. Keep outputs reproducible and deterministic.
3. Prefer minimal wrappers with clear logging and actionable errors.

## Command and UX Rules

- Keep command syntax consistent: `asma <cmd-group> ...`.
- For repo-aware git commands: `asma git --repo <context> <command> ...`.
- If `--repo` is omitted, infer context from current directory when possible.
- Do not preserve positional git context syntax in new changes.
- Prefer explicit dry-run and clear error guidance for destructive actions.
- If introducing a new flow, provide an obvious beginner path and an advanced override path.
- Implement behavior changes in the original command first; aliases must only forward.

## Command Testing Rule (MANDATORY)

When adding, modifying, or refactoring any `asma` command:

1. Always add/update/refactor tests in the same change.
2. Cover both unit tests for command/helper logic and CLI-level E2E tests.
3. Keep tests in `tests/` tree grouped by purpose (`tests/unit`, `tests/e2e`).
4. Do not mark work complete until related tests are updated and executed.

## CLI Behavior Expectations

- Keep command behavior deterministic and safe by default.
- Prefer dry-run visibility and explicit opt-in for destructive/network operations.
- Reuse shared helpers for formatting, messaging, and git command execution.

## Setup and Verification

- `make bootstrap` is the minimal setup to make `asma` runnable.
- `asma scaffold` is the full setup/remediation flow.
- Keep scaffold checks focused on local development prerequisites.
- After CLI changes, verify with `asma test`.

## Quality Gates (Required)

Always run checks at end of implementation and fix issues before finishing:

1. Ruff lint checks
2. Pylance/static analysis diagnostics

No known lint warnings or type warnings should remain in changed files.

## Agent Execution Guardrail

When diagnosing/fixing CLI code, do not get stuck repeatedly trying to create/configure Python environments.

1. If environment-configuration is canceled once, continue with non-env options.
2. Prefer: editor diagnostics (`get_errors`), direct file inspection/edits, `ruff check`, targeted `py_compile`.
3. Retry environment setup only when strictly required with clear justification.
4. If an environment-specific check cannot run, report that blocker briefly and continue.

## Missing Workflow Rule

If workflow is missing or unclear for beginners:

1. State what is missing.
2. Propose a concrete command or flag.
3. Prioritize safety + DX + automation.
4. Provide minimal command example.
