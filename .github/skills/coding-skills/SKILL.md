---
name: coding-skills
description: Use when selecting the applicable ASMA coding policy across languages, resolving a scoped coding-rule conflict, or reviewing shared standards. For a concrete backend, frontend, Python, SQL, infrastructure, or documentation task, use its scoped owner directly.
---
<!-- Generated from .github/skills/coding-skills/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Coding skills router

This skill routes to existing standards; it is not a second coding-standard source. Read the instructions and skills that match the target repository and files, then apply the narrowest compatible rule.

## Authority and conflicts

The user's task and authorization set the request boundary. Workspace-wide safeguards and the owning repository's accepted decisions remain in force. A scoped rule may refine a general rule inside its stated paths and task trigger. One source supersedes another only when the authorized owner explicitly records that scope and supersession. File timestamps, ordering, or apparent recency do not decide conflicts.

If two applicable rules still conflict, preserve both scopes, avoid the disputed change, and use the owning ambiguity/uncertainty workflow to record the question and disposition. Do not invent a priority rule or silently choose a convenient standard.

## Route by work

- Node/Bun request handlers: read backend-service.instructions.md and backend-request-context-and-errors.
- React/MST or shared ASMA UI: use frontend topology and the relevant frontend/UI skill.
- Python, SQL, YAML, infrastructure, and Markdown: follow their language or path-scoped instruction and local repository conventions.
- New documents: document-organization owns placement, naming, metadata, and router updates.

For a concrete change, load only the applicable scoped instruction and task skill; do not treat this router as a catch-all trigger.
