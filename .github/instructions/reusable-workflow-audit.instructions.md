---
description: 'Reusable workflow audit guidance for asma-workflows workflow and script reviews.'
applyTo: '.github/workflows/**/*.{yml,yaml}, .github/scripts/**'
---

# Reusable Workflow Audit Instructions

Apply these rules when working on reusable GitHub Actions workflow audits in `asma-workflows`.

## Use The Right Skill

- Use the `reusable-workflow-audit` skill for requests about reusable workflow audits, workflow platform health, shared workflow consistency, mutable refs, permissions, or release behavior.

## Required Reading

Read these baseline documents in `asma-infrastructure` before drafting findings:

- `../../infrastructure/asma-infrastructure/_docs/reusable-workflow-audit.md`
- `../../infrastructure/asma-infrastructure/_docs/reusable-workflow-audit-playbook.md`
- `../../infrastructure/asma-infrastructure/_docs/workflow-and-script-audit-2026-03-11.md`

## Required Audit Scope

Inspect these locations first:

- `.github/workflows/*.yml`
- `.github/scripts/**`

When the audit compares the control plane, also inspect:

- `../../infrastructure/asma-infrastructure/.github/workflows/reusable-*.yml`
- `../../infrastructure/asma-infrastructure/.github/actions/**/action.yml`

## Audit Checklist

Always check:

1. workflow inventory and job topology
2. job responsibility boundaries and reuse shape
3. naming consistency in the GitHub Actions UI
4. mutable `@master` and `ref: master` references
5. workflow and job permissions
6. secrets versus vars boundaries
7. artifact handoff and inter-job coupling
8. shared bootstrap and script reuse
9. supply-chain risks such as unpinned installs or `curl | bash`
10. CI coverage for shared scripts
11. release-gate input versus behavior consistency

## Deliverables

Produce:

1. a short executive summary
2. findings ordered by severity
3. resolved items since the previous audit
4. recommended next actions by priority

Prefer delta audits against the latest baseline instead of rewriting the full history from scratch.