---
description: "Generate a conventional commit message from staged changes"
---
<!-- Generated from .github/prompts/commit-message.prompt.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Commit Message Generator

Generate a conventional commit message following ASMA project conventions.

## Format

```
<type>(<scope>): <Capital letter description>

[Optional body]

[Optional footer]
```

## Rules

- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `hotfix`, `revert`
- Breaking changes: add `!` after type — `feat!: Remove legacy API`
- Description starts with **capital letter**, imperative mood, no period at end
- Scope is optional — use when it adds clarity
- Common scopes: `auth`, `widget`, `shell`, `build`, `deps`, `docs`, `ci`, `workflows`
- No issue IDs in subject line (use body/footer)
- No multiple unrelated changes in one commit
- No vague messages like "fix stuff" or "update code"

## Body (optional)

Include a short bullet list when changes span multiple areas/files.

## Footer (optional)

- Breaking changes: `BREAKING CHANGE: <Description>`
- Issue references: `Closes #123`

## Instructions

1. Look at the staged changes (files and diff)
2. Determine the appropriate type and scope
3. Write a clear, concise subject line
4. Add body bullets if changes are broad
5. Return plain commit message text only (no markdown fences)
