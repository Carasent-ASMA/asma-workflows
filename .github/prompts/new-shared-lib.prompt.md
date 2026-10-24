---
description: "Create a new shared library following ASMA naming and architecture conventions"
---
<!-- Generated from .github/prompts/new-shared-lib.prompt.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# New Shared Library Scaffolding

Create a new shared library following ASMA project conventions.

## Naming Convention

**Pattern:** `{segment}-{tech}-{domain}`

| Type | Pattern | Example |
|------|---------|---------|
| UI Library | `asma-ui-{component}` | `asma-ui-table` |
| Core Library | `asma-core-{purpose}` | `asma-core-helpers` |

**Rules:**

- All lowercase with hyphens (kebab-case)
- Tech keyword in middle position
- Tech tokens are registry-based, not fixed to 3 characters
- Descriptive domain or purpose names (no unclear abbreviations)
- No environment suffixes (`-prod`, `-dev`)

## Directory Structure

New shared libraries go in `shared/`:

```
shared/asma-{tech}-{name}/
├── .github/
│   └── workflows/
│       └── publish.yml         # References reusable workflow
├── src/
│   └── index.ts                # Library entry point
├── package.json
├── tsconfig.json
├── .gitignore
├── .npmignore
├── README.md
└── cspell.json
```

## Workflow Reference

Every shared library's `publish.yml` should reference the centralized workflow:

```yaml
jobs:
  publish:
    uses: Carasent-ASMA/asma-workflows/.github/workflows/reusable-npm-publish.yml@master
    with:
      publish_npm: false  # Set true if publishing to npm
      package_name: "asma-{tech}-{name}"
    secrets: inherit
```

## Dependency Rules

- `asma-core-helpers` is generic — no auth logic.
- UI libraries depend on `asma-ui-core` as foundation.
- pnpm workspace for local linking (instant HMR).
- Import from correct package name, not legacy names.

## Instructions

1. Ask for the library type (UI component or core utility)
2. Ask for the library name/purpose
3. Create the directory structure in `shared/`
4. Set up `package.json` with correct name and dependencies
5. Create `tsconfig.json` extending the root config
6. Create the publish workflow referencing `asma-workflows`
7. Create the entry point (`src/index.ts`)
8. Add README with usage instructions
9. Init as git submodule if needed

## Rules

- TypeScript only
- Follow existing shared library patterns
- Use pnpm (not npm or yarn)
- SemVer for versioning if publishing to npm
