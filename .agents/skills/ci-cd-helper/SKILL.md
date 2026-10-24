---
name: ci-cd-helper
description: "Use when authoring, reviewing, or troubleshooting CI jobs, GitHub Actions runners, deployment workflows, or Argo CD pipelines. For app handlers use the backend skill; for release notes use release-manager."
---
<!-- Generated from .github/skills/ci-cd-helper/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# CI/CD helper

## Workflow

1. Name the repository, workflow, target environment, and requested outcome. Read the workflow and owning repository instructions first.
2. Prefer existing reusable workflows, runner labels, deployment sources, and validation scripts. For ASMA deployment conventions, read the infrastructure instruction and pipeline owner.
3. Trace triggers, permissions, secrets, artifacts, concurrency, environment approvals, and deployment targets. Treat fork-controlled input and credentials as untrusted boundaries.
4. Make the smallest change that addresses the observed failure. Identify a template or script only if it exists in the target repository.
5. Run the narrow workflow validation supported by the repository. Report hosted-runner behavior that could not be exercised locally.

This skill does not authorize publishing, deployment, credential rotation, or runner infrastructure changes.
