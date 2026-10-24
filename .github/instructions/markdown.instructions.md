---
applyTo: "**/*.md"
---
<!-- Generated from .github/instructions/markdown.instructions.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Markdown Instructions

Apply these rules when editing Markdown files.

## Documentation Style

- Split large docs into focused 1–2 page documents.
- Use cross-linking between docs.
- Keep `README` as index/navigation.
- Write documentation files under `asma-modules/_docs/` by default.
- Only place documentation outside `asma-modules/_docs/` when explicitly requested.

## Bitbucket Markdown Rendering (Critical)

Bitbucket requires blank lines before lists and code blocks.

Required formatting rules:

1. **MD032/blanks-around-lists** — Lists should be surrounded by blank lines. Always add a blank line both *before* and *after* every list (bullet or numbered), including the line that follows the last list item.
2. Always add a blank line before code blocks (` ``` `).
3. Maintain blank lines between sections.

Wrong:

`**Text:**\n- Item\nNext paragraph`

Correct:

`**Text:**\n\n- Item\n\nNext paragraph`

When editing `.md` files, ensure blank lines exist before and after every list, and before every code block.
