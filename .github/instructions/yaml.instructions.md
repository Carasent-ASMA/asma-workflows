---
applyTo: "**/*.{yml,yaml}"
---
<!-- Generated from .github/instructions/yaml.instructions.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# YAML Editing Instructions

Apply these rules when creating or modifying YAML files.

## Editing Strategy

- YAML is whitespace-sensitive. Treat indentation changes as structural changes.
- If a YAML block already has indentation or schema errors, replace the entire step, job, mapping, or file instead of patching individual keys inside the broken block.
- If more than one YAML error appears after an edit, stop doing incremental fixes and rewrite the affected section cleanly.
- Prefer smaller numbers of structurally complete edits over many surgical edits.

## Validation Requirements

- Validate YAML after every edit.
- Do not rely on a single validation source when the file appears inconsistent.
- If diagnostics and file content disagree, inspect the exact on-disk lines before continuing.
- Do not continue stacking edits on top of malformed YAML.

## GitHub Actions YAML

- Prefer replacing a full workflow step or job rather than editing individual keys inside a damaged block.
- Prefer simple `run:` forms that are easy to validate.
- Use literal blocks (`|`) when a command spans multiple lines and shell continuation is required.
- Avoid folded blocks when they make shell argument boundaries ambiguous.
- Keep indentation consistent with the surrounding file. Do not mix indentation depths within the same list item.

## Safety Rules

- Do not change unrelated indentation or formatting in nearby YAML.
- Preserve comments unless the user asks to remove or rewrite them.
- When introducing environment variables or secrets, keep them in the correct mapping level and verify they remain attached to the intended step or job.
- After a failed YAML edit, prefer a clean replacement of the affected region over another micro-patch.