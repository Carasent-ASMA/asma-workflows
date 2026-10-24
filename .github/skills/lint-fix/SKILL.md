---
name: 'lint-fix'
description: 'Automated linting and code style correction for TypeScript/React.'
---
<!-- Generated from .github/skills/lint-fix/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Lint Fix Skill

## Purpose
Automate linting, formatting, and code style enforcement for all supported modules.

## Instructions
- Use before commit and PR review.
- Integrates with ESLint, Prettier, and project standards.

## Assets
- ESLint/Prettier config examples
- Lint fix scripts

## Lefthook Integration

- Lefthook automates linting and formatting on every commit and push.
- Pre-commit: Runs `pnpm eslint --fix` and `pnpm format` on staged files.
- Pre-push: Runs `pnpm lint` and other checks.
- To set up hooks, run:
  - `python3 _tools/lefthook/_scripts/setup-hooks.py <service>`
  - Or for all: `python3 _tools/lefthook/_scripts/setup-hooks.py --all`
- Lefthook config (`lefthook.yml`) must include lint and format jobs for full automation.
- Manual linting is rarely needed; hooks handle most cases automatically.

## Shared Linting Configuration

- All linting and check tool configs (ESLint, Prettier, etc.) live in the parent asma-modules folder.
- Submodules must not create their own lint config files.
- Submodules should refer to and symlink lint configs from the parent folder.
- This ensures consistent linting rules and avoids duplication or drift.
