---
applyTo: "{shared}/**/*.{ts,tsx},{activities,artifact,calendar,chat,consents,crm,devextreme,editor,notification,office,shell,storage}/asma-app-*/**/*.{ts,tsx},directory/{asma-app-*,adopus-app-*}/**/*.{ts,tsx}"
---
<!-- Generated from .github/instructions/development-workflow.instructions.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# ASMA Development Workflow

Apply these rules when doing product development in domain apps and shared libraries.

## Primary Interface

- Use `asma {cmd-group}` commands first.
- Prefer: `asma git ...`, `asma app ...`, `asma workspace ...`.
- Use direct `git`, `pnpm`, or other commands only if no ASMA command exists.

## Context-First Syntax

For context-aware flows:

- `asma git <context> <command> ...`
- `asma app <context> <command> ...`

Examples:

- ✅ `asma git chat status`
- ✅ `asma git chat branch create --from ASMA-1234`
- ❌ `asma git status chat`

## Day-to-Day Stack

- React + TypeScript (micro apps)
- Node.js services
- Bun.js services (incremental adoption)
- Hasura metadata/workflow

## Branching and Commit Flow

- Create feature branches from Jira via ASMA commands.
- Prefer `--from` flow with autocomplete and Jira-driven naming.
- When needed, use dependent-aware operations so target + dependents stay aligned.
- Keep safety defaults and guardrails active.

## TypeScript app code generation

When generating frontend app/domain code for a TypeScript or JavaScript application:

1. Write new app code and tests in TypeScript (`.ts`/`.tsx`).
2. Do not introduce JavaScript app code or tests unless the user explicitly requests it. An established JavaScript file may be changed without adding new JavaScript files.
4. Follow existing React/Vite patterns in the target module before introducing new abstractions.
5. Keep changes scoped to the active domain/context; avoid broad cross-repo edits unless requested.
6. Preserve existing public contracts (API/schema/component props) unless migration is explicit.

This applies to TS/JS applications, not Python CLI tools, SQL migrations, shell scripts, or infrastructure. For Node/Bun backend code, preserve the target runtime and follow the TypeScript app-generation rule above.

When generating Node/Bun backend code:

1. Match runtime already used by the target repo; do not switch runtime implicitly.
2. Keep startup/build scripts consistent with existing package scripts.
3. Add clear runtime-safe error handling and minimal logging.

When generating Hasura-related changes:

1. Keep metadata changes minimal and consistent with current folder conventions.
2. Avoid speculative schema changes outside requested scope.
3. Prefer additive, reversible modifications where possible.

## Missing Workflow Rule

If a workflow is missing or not intuitive:

1. Inform explicitly what is missing.
2. Propose a new ASMA command or flag.
3. Prioritize: safety → DX clarity → automation.
4. Provide a minimal syntax example.
