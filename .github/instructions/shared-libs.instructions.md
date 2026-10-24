---
applyTo: "shared/**/*.{ts,tsx}"
---
<!-- Generated from .github/instructions/shared-libs.instructions.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Shared Libraries Instructions

Apply these rules when working on shared libraries (`shared/`).

## Auth Flow Golden Rule

- **Only `asma-auth-client` talks to `asma-njs-auth`** — domain apps NEVER make direct calls to the auth service.
- Apps READ auth state from `window.__ASMA_AUTH__`, never call auth endpoints directly.
- Shell initializes auth once; widgets consume shared state.

## Dependency Hierarchy

- `asma-core-helpers` is generic (HTTP, validation, dates) — **no auth logic in it**.
- All UI libraries (`asma-ui-table`, `asma-ui-notistack`, `asma-ui-richeditor`) depend on `asma-ui-core` as their foundation.
- `asma-auth-client` lives in `/auth/` folder (domain ownership), not in `/shared/`.

## NPM / Publishing Rules

- Preferred: deploy from Git submodules, no NPM publishing needed.
- Local dev uses pnpm workspace with automatic symlinks — changes are instant via HMR.
- If publishing to NPM, follow SemVer (major.minor.patch).
- Use git commit hashes as versions during active dev; add git tags for stable releases.

## Strict Conventions

- pnpm only (not npm or yarn).
- Submodule sync is automated via Python scripts (`sync-submodule.py`).
- Import from the correct package name — e.g. `asma-core-helpers`, not legacy `asma-helpers`.

## Widget Architecture Context

- Widget-level granularity (not app-level).
- Zero module duplication via Import Maps.
- HMR support for local development.
- Shared modules loaded once across all widgets.

## Reference

For deep architecture documentation: `asma-modules/_docs/SHARED_LIBRARIES_ARCHITECTURE.md`
