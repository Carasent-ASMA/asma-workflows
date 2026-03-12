---
name: "reusable-workflow-audit"
description: "Audit reusable GitHub Actions workflows for asma-infrastructure and asma-workflows. Use for requests about reusable workflow audits, workflow platform health, CI architecture, mutable refs, permissions, secrets versus vars, release gating, and workflow consistency."
---

# Reusable Workflow Audit Skill

## Purpose

Audit the reusable workflow platform for `asma-infrastructure` and `asma-workflows` with consistent criteria and comparable findings over time.

## Use This Skill When

Use this skill when the request mentions any of these concepts:

- reusable workflow audit
- GitHub Actions audit
- workflow platform review
- CI/CD workflow architecture review
- `asma-infrastructure` workflow review
- `asma-workflows` workflow review
- mutable workflow refs
- workflow permissions
- secrets versus vars in workflows
- release-gate behavior audit

## Required Inputs

Inspect these locations first:

- `asma-infrastructure/.github/workflows/reusable-*.yml`
- `asma-infrastructure/.github/actions/**/action.yml`
- `asma-workflows/.github/workflows/*.yml`
- `asma-workflows/.github/scripts/**`

Read these baseline documents before drafting findings:

- `asma-infrastructure/_docs/reusable-workflow-audit.md`
- `asma-infrastructure/_docs/reusable-workflow-audit-playbook.md`
- `asma-infrastructure/_docs/workflow-and-script-audit-2026-03-11.md`

## Audit Checklist

Always check:

1. workflow inventory and job topology
2. responsibility boundaries between assess, build, publish, tag, and summary phases
3. naming consistency in GitHub Actions UI
4. mutable `@master` and `ref: master` references
5. job and workflow permissions
6. secrets versus vars boundaries
7. artifact handoff and inter-job coupling
8. shared bootstrap and composite action reuse
9. supply-chain risks such as `curl | bash` and unpinned installs
10. `asma-workflows` CI coverage for shared scripts
11. release-gate input versus behavior consistency

## Expected Deliverables

Produce:

1. a short executive summary
2. findings ordered by severity
3. resolved items since the previous audit
4. recommended next actions by priority

When appropriate, update:

- `asma-infrastructure/_docs/reusable-workflow-audit.md`
- `asma-infrastructure/_docs/reusable-workflow-audit-playbook.md`
- `asma-infrastructure/_docs/workflow-and-script-audit-2026-03-11.md`

## Notes

Prefer delta audits against the latest baseline instead of rewriting findings from scratch.

Treat the app-family reusable workflows as the current reference implementation for phased reusable workflow structure unless a newer standard supersedes them.
