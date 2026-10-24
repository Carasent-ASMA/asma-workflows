---
name: refactor-plan
description: "Draft a lightweight in-chat sequence and rollback for a multi-file refactor. For a durable plan use create-implementation-plan; for an epic backlog use mini-project-kickoff. Not a code-refactoring procedure."
---
<!-- Generated from .github/skills/refactor-plan/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Refactor Plan

Create a detailed plan for this refactoring task.

## Scope boundary

This skill returns an in-chat working plan and does not create a documentation
file. If the request requires a durable repository plan, switch to
[`create-implementation-plan`](../create-implementation-plan/SKILL.md), which
delegates filename and placement to `document-organization`. If it must also
become an executable Jira backlog (and, when governed, a `kontord` graph), use
[`mini-project-kickoff`](../mini-project-kickoff/SKILL.md).

## Refactor Goal

{{refactor_description}}

## Instructions

1. Search the codebase to understand current state
2. Identify all affected files and their dependencies
3. Plan changes in a safe sequence (types first, then implementations, then tests)
4. Include verification steps between changes
5. Consider rollback if something fails

## Output Format

```markdown
## Refactor Plan: [title]

### Current State
[Brief description of how things work now]

### Target State
[Brief description of how things will work after]

### Affected Files
| File | Change Type | Dependencies |
|------|-------------|--------------|
| path | modify/create/delete | blocks X, blocked by Y |

### Execution Plan

#### Phase 1: Types and Interfaces
- [ ] Step 1.1: [action] in `file.ts`
- [ ] Verify: [how to check it worked]

#### Phase 2: Implementation
- [ ] Step 2.1: [action] in `file.ts`
- [ ] Verify: [how to check]

#### Phase 3: Tests
- [ ] Step 3.1: Update tests in `file.test.ts`
- [ ] Verify: Run `npm test`

#### Phase 4: Cleanup
- [ ] Remove deprecated code
- [ ] Update documentation

### Rollback Plan
If something fails:
1. [Step to undo]
2. [Step to undo]

### Risks
- [Potential issue and mitigation]
```

Shall I proceed with Phase 1?
