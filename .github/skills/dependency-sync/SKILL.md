---
name: dependency-sync
description: "Use when aligning shared package versions or import-map declarations across named ASMA consumers. Not for a single-package implementation or broad module materialization; use target package instructions and explicitly scoped ASMA operations."
---
<!-- Generated from .github/skills/dependency-sync/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Dependency synchronization

1. Identify the shared package or import-map entry, its owner, exact consuming modules, and requested version/range. Read modules.yml and relevant package manifests.
2. For shared-library eligibility or kernel externalization decisions, route to kernel-lib-eligibility. For bundle impact, use bundle-optimization.
3. Compare source manifests, lockfiles, import maps, and consumer declarations. Change only named consumers and preserve each repository's runtime and package-manager conventions.
4. Use the supported ASMA operation only for the explicitly requested module set. Do not run an unbounded asma sync or advance unrelated checkouts.
5. Validate affected manifests and the smallest relevant build/type check. Report consumers that could not be materialized or checked.

This skill contains no bundled sync scripts or templates.
