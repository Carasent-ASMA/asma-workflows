---
name: migration-assistant
description: "Use when moving an ASMA app or widget between APIs, UI component generations, or repository layouts. Database schema migrations follow the owning repository's procedure and database-specific skill."
---
<!-- Generated from .github/skills/migration-assistant/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Application and widget migration

1. Identify source and target versions, owning module, migration boundary, consumers, and rollback point. Read package manifests, API contracts, and local migration notes.
2. For MUI-based asma-ui-core to the MUI-free rewrite, use ui-core-mui-free-migration. For shared UI component selection, use asma-ui-components.
3. Inventory affected call sites and compatibility constraints before changing code. Preserve public APIs and deployment compatibility unless a breaking change is authorized.
4. Migrate a representative slice first, validate it, then apply the proven transformation to the remaining named scope. Do not claim scripts or checklists that are absent from the repository.
5. Run target-repository tests and builds that cover changed consumers; record deferred consumers and rollback risks.

Database schema and data migrations are outside this skill. Follow the owning database repository's established migration procedure and PostgreSQL or HSR guidance.
