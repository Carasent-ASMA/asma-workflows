---
goal: [One sentence stating what is true when this plan is done. Not a title — if you cannot say how you would check it, it is not a goal yet.]
version: [Optional: e.g., 1.0, Date]
date_created: [YYYY-MM-DD]
last_updated: [Optional: YYYY-MM-DD]
owner: [Optional: Team/Individual responsible for this spec]
status: 'Completed'|'In progress'|'Planned'|'Deprecated'|'On Hold'
# Required when status is 'On Hold'. All four fields are mandatory and
# review_by is an ISO date no earlier than today and at most 30 days ahead;
# _tools/scripts/check-plan-holds.py enforces it.
# hold:
#   reason: waiting on a named dependency
#   owner: <the person or seat that acts when it lifts>
#   lifts_when: <an observable condition, not a restatement of the reason>
#   review_by: 'YYYY-MM-DD'
orchestration: paseo # Select exactly one: paseo or kontor.
workflow: kontor # kontor (default) or free
workstream: [Required: one key from config/orchestration/workstreams.json; the Jira epic carries the label ws:<key>]
# Optional, only when explicitly selecting a Paseo-direct trial:
# delivery_strategy: milestone
# behaviour_scenarios: bdd
tags: [Optional: List of relevant tags or categories, e.g., `feature`, `upgrade`, `chore`, `architecture`, `migration`, `bug` etc]
---
<!-- Generated from .github/skills/create-implementation-plan/assets/plan-template.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# <Descriptive Implementation Plan Title>

[Insert the complete current metadata and When-to-Load block required by
`document-organization`; do not copy a stale local variant into this template.]

![Status: <status>](https://img.shields.io/badge/status-<status>-<status_color>)

**Orchestration:** paseo

*Both options use the unified Kontor workflow, including its roles, skills,
naming conventions and quality checks. `paseo` coordinates through Paseo and
ASMA commands without `kontord`; `kontor` routes all epic orchestration through
the `kontord` daemon, which adds deterministic automation and enforcement. These
obligations apply to `workflow: kontor` plans; a `workflow: free` plan follows
only the safety floor and the pieces it asks for.*

[Match the displayed value to the frontmatter. For `kontor`, also retain the
existing declaration `Orchestration: kontor-governed` in this first section
and confirm the Jira epic label `kontor-governed` under the transition rule.]

[A short concise introduction to the plan and the goal it is intended to achieve.]

## 1. Requirements & Constraints

[Explicitly list all requirements & constraints that affect the plan and constrain how it is implemented. Use bullet points or tables for clarity.]

- **REQ-001**: Requirement 1
- **SEC-001**: Security Requirement 1
- **[3 LETTERS]-001**: Other Requirement 1
- **CON-001**: Constraint 1
- **GUD-001**: Guideline 1
- **PAT-001**: Pattern to follow 1

### 1.1 Behaviour Scenarios (SCN)

[Only for `behaviour_scenarios: bdd`; otherwise omit this subsection. One row
and one fenced `gherkin` block per scenario. The block is the approval
snapshot; the home named in the row is the only executable copy after task
start. Rules: "Behaviour scenarios (opt-in trial)" in the
create-implementation-plan skill.]

| Draft id | Bound id | Proves | Owning task | Layer | Home (repository · planned path) | Companion / exemption | Approved hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SCN-001 | `ASMA-<task>-SCN-001` (at binding) | REQ-001 · AC-003 (`<spec path>`) | TASK-002 | e2e \| unit \| component \| service | `<repo>` · `tests/features/<capability>.feature` | `SCN-002` \| `E2E-only: no changed decision logic` \| `n/a (lower layer)` | `sha256:<hex>` |

~~~gherkin
@SCN-001
Scenario: <one observable behaviour, stated declaratively>
  Given <the state the user or caller is in>
  When <the action>
  Then <the observable outcome>
~~~

#### Amendments

[Empty until a frozen scenario changes. One row per amendment.]

| Amendment | Scenario | Date | Reason | Authority | Evidence revalidated | New hash | Commit |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 2. Implementation Steps

Rows represent meaningful delivery tasks; implementation steps remain checklists within those rows. Every task row carries a **closure condition**: one testable sentence stating what is true when that
task is done. It is the authoritative source of that task's Jira `Goal` under the
[task content contract](../../kontor-jira-linked-creation/SKILL.md#task-content-contract), which copies
it verbatim; the frontmatter `goal:` remains the whole-plan closure condition and is copied only to a
task that owns the entire outcome.

### Implementation Phase 1

- GOAL-001: [Describe the goal of this phase, e.g., "Implement feature X", "Refactor module Y", etc.]

| Task | Description | Closure condition | Completed | Date |
|------|-------------|-------------------|-----------|------|
| TASK-001 | Description of task 1 | One testable sentence that is true when this task is done | ✅ | 2025-04-25 |
| TASK-002 | Description of task 2 | Task 2's testable completion condition | | |
| TASK-003 | Description of task 3 | Task 3's testable completion condition | | |

### Implementation Phase 2

- GOAL-002: [Describe the goal of this phase, e.g., "Implement feature X", "Refactor module Y", etc.]

| Task | Description | Closure condition | Completed | Date |
|------|-------------|-------------------|-----------|------|
| TASK-004 | Description of task 4 | Task 4's testable completion condition | | |
| TASK-005 | Description of task 5 | Task 5's testable completion condition | | |
| TASK-006 | Description of task 6 | Task 6's testable completion condition | | |

### 2.5 Dependency Graph and Waves

[Required for new plans and dependency amendments. The JSON graph is the only
editable dependency source. See the [versioned contract](../references/plan-graph-contract.md).
Phases group outcomes; computed Plan-Graph Waves measure longest dependency depth.
Neither structural width nor absence of sibling blockers grants permission to launch.]

#### (a) Authoritative dependency graph

[Replace the example tasks/edges with the real delivery tasks from §2. Every task
has all seven fields. `depends_on: []` explicitly means no sibling prerequisites;
external fences go in their own array. Use `null` for unbound Jira/Kontor identifiers
while drafting; never invent bindings. Fill confirmed bindings before execution.]

```plan-graph
{
  "schema_version": 1,
  "epic": {
    "jira": null,
    "kontor_id": null
  },
  "tasks": [
    {
      "id": "TASK-001",
      "title": "Description of task 1",
      "phase": "Phase 1",
      "jira": null,
      "kontor_id": null,
      "depends_on": []
    },
    {
      "id": "TASK-002",
      "title": "Description of task 2",
      "phase": "Phase 1",
      "jira": null,
      "kontor_id": null,
      "depends_on": [
        "TASK-001"
      ]
    },
    {
      "id": "TASK-003",
      "title": "Description of task 3",
      "phase": "Phase 1",
      "jira": null,
      "kontor_id": null,
      "depends_on": [
        "TASK-001"
      ]
    },
    {
      "id": "TASK-004",
      "title": "Description of task 4",
      "phase": "Phase 2",
      "jira": null,
      "kontor_id": null,
      "depends_on": [
        "TASK-002"
      ]
    },
    {
      "id": "TASK-005",
      "title": "Description of task 5",
      "phase": "Phase 2",
      "jira": null,
      "kontor_id": null,
      "depends_on": [
        "TASK-003"
      ]
    },
    {
      "id": "TASK-006",
      "title": "Description of task 6",
      "phase": "Phase 2",
      "jira": null,
      "kontor_id": null,
      "depends_on": [
        "TASK-004",
        "TASK-005"
      ]
    }
  ],
  "external_fences": []
}
```

#### (b) Generated waves and Kontor/Jira binding view

[Do not hand-edit this projection. After editing the JSON, run from the workspace root:
`python3 _tools/ai-orchestration/plan_graph.py sync <plan.md>`, then
`python3 _tools/ai-orchestration/plan_graph.py validate <plan.md>`.
Name every cross-stream join and its dependency/safety reason below the projection.]

<!-- plan-graph:derived:start -->

```text
wave 0   TASK-001   (1 nodes)
wave 1   TASK-002  TASK-003   (2 nodes)
wave 2   TASK-004  TASK-005   (2 nodes)
wave 3   TASK-006   (1 nodes)

Dependencies (prerequisite -> dependent):
  TASK-001 -> TASK-002
  TASK-001 -> TASK-003
  TASK-002 -> TASK-004
  TASK-003 -> TASK-005
  TASK-004 -> TASK-006
  TASK-005 -> TASK-006

unbound epic
  TASK-001 · unbound · Phase 1 · wave 0 · Description of task 1
  TASK-002 · unbound · Phase 1 · wave 1 · Description of task 2
  TASK-003 · unbound · Phase 1 · wave 1 · Description of task 3
  TASK-004 · unbound · Phase 2 · wave 2 · Description of task 4
  TASK-005 · unbound · Phase 2 · wave 2 · Description of task 5
  TASK-006 · unbound · Phase 2 · wave 3 · Description of task 6
```

Structural waves only; external fences, gates and capacity still govern admission.

<!-- plan-graph:derived:end -->

#### (c) The scheduling facts

- **Maximum useful concurrency:** [N in wave 0, then per wave]
- **Concurrency cap authorised:** [and why — a cap above the graph's real width is theatre]
- **Recommended start:** [usually below the cap while another epic is live on the same module]
- **Intra-phase parallelism:** [which TASK ids run together, which serialize]
- **Collision control:** [for any module an in-flight plan also edits — worktree, new-file bias, single call site]
- **External fences:** [each dependency on another plan's work item, what ships without it, and that it **cannot** be expressed in `depends_on` — so the item reads `ready` and must not be armed on that basis]

#### Useful concurrency, safe integration

1. Size tasks by coherent outcomes before computing graph width.
2. Add dependency edges for actual inputs or safety constraints; record resource
   serialization separately when it is not a deliverable dependency.
3. Bound launches by readiness, external fences, checkout ownership, provider
   capacity and the ability to review/integrate finished work.
4. Separate worktrees prevent shared-checkout writes, not semantic conflicts.
   Serialize conflicting contracts and integration even when files differ.
5. Keep joins explicit. Graph width alone never authorizes a launch.

### Autonomous TPM operation

[Mandatory for epic plans. Record every item the
[plan binding contract](../../epic-orchestration/references/autonomous-tpm-operation.md#plan-binding)
lists; for an unsupported capability, explain the bounded usable behavior.]

### 2.6 Delivery and checkout mapping

[Required for `delivery_strategy: milestone`. For a simple plan, compact these
facts into one small table; do not manufacture milestones, issues or empty rows.]

| Milestone | Outcome / usable stopping point | Tasks (confirmed keys when bound) | Repositories, branches and PR targets | Prerequisites / compatibility order | Acceptance and rollout / rollback |
| --- | --- | --- | --- | --- | --- |

| Task | Milestone | Primary owner / affected repositories | Included implementation steps | Dependencies / external fences | Risk and sizing rationale when needed |
| --- | --- | --- | --- | --- | --- |

| Repository / checkout | Writer and task sequence | Branch / base / integration target | Parallelism and serialization | Integration owner | Capability evidence / fallback |
| --- | --- | --- | --- | --- | --- |

[Each task has one planned delivery milestone; shared prerequisites are assigned
once and referenced by dependents. Keep plan mappings authoritative and link them
from Jira instead of copying a second graph. Maps describe intent; native binding
readbacks confirm the observed checkout assignment. Exclusive writing also
requires the dedicated-checkout policy and the owning workflow's checks; claim
enforced fencing only for a separately qualified supported mechanism.
Record task contribution SHAs, integration results, merged PRs and release checks
as evidence becomes available.
Implemented, integrated, merged and released are distinct observations, not new
Jira statuses. State which boundary the task's existing Done means requires.

An amendment records the reason, affected keys/milestones, dependency and risk
changes, evidence needing revalidation, and any delivery impact. Preserve old
bindings and history; the owning workflow handles substantive Jira revisions.]

## 3. Alternatives

[A bullet point list of any alternative approaches that were considered and why they were not chosen. This helps to provide context and rationale for the chosen approach.]

- **ALT-001**: Alternative approach 1
- **ALT-002**: Alternative approach 2

## 4. Dependencies

[List any dependencies that need to be addressed, such as libraries, frameworks, or other components that the plan relies on.]

- **DEP-001**: Dependency 1
- **DEP-002**: Dependency 2

## 5. Files

[List the files that will be affected by the feature or refactoring task.]

- **FILE-001**: Description of file 1
- **FILE-002**: Description of file 2

## 6. Testing

[List the tests that need to be implemented to verify the feature or refactoring task.]

- **TEST-001**: Description of test 1
- **TEST-002**: Description of test 2

[Only for a plan that changes runtime behavior: one `MUT-` row per seeded mutant, filled in as the mutation phase runs. Rules: "Mutation validation" in the create-implementation-plan skill.]

| Mutant | File:line | Suite | Result | Action |
|--------|-----------|-------|--------|--------|
| **MUT-001**: [mutant, e.g. "skip the insert"] | `path:line` | `suite.test.ts` | KILLED \| SURVIVED \| EQUIVALENT | [assertion strengthened, or — ] |

[Only for `behaviour_scenarios: bdd`: one row per scenario, filled in as tasks
run. A point-in-time snapshot; the home and its git history are the live
record. `e2e` rows are `report-only`: no `MUT-` row exists for them.]

| Scenario | Layer | Home (repository · path) | Baseline commit | Hash check | Command | Run SHA | Observed result | RED observed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ASMA-<task>-SCN-001` | e2e | `<repo>` · `tests/features/<capability>.feature` | `<sha>` | match \| mismatch | `pnpm e2e:bdd` | `<sha>` | copied runner line, or `Not yet performed` | first behavioural failure and SHA, or `n/a (existing behaviour)` |

## 7. Risks & Assumptions

[List consequential risks and assumptions. For each assumption state its scope,
validation, consequence if false and the point beyond which dependent work waits.]

- **RISK-001**: Risk 1
- **ASSUMPTION-001**: Assumption 1

[Apply the create-implementation-plan Ambiguity and uncertainty rule. Include the table only when
consequential questions exist; otherwise state that none are identified.
References are local to this plan, not new backlog identifiers. Kind distinguishes
ambiguity, vagueness/missing detail and uncertainty; split linked questions when
they need different actions. Status records whether the question is open, under
investigation or resolved, without introducing a runtime/Jira state.]

| Reference / kind | Question / competing interpretations | Affected tasks / readiness boundary | Owner | Next action / timebox or decision deadline | Closure evidence / decision and authority | Status |
| --- | --- | --- | --- | --- | --- | --- |

## 8. Related Specifications / Further Reading

[Link to related spec 1]
[Link to relevant external documentation]
