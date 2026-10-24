---
name: test-gen
description: "Add or extend behavior-focused tests for a named implementation in its repository framework, including Python/pytest. For explicit test-first work use tdd; for Python coverage use pytest-coverage; for test-strength checks use mutation-testing."
---
<!-- Generated from .github/skills/test-gen/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Test generation

1. Identify behavior, acceptance condition, test layer, existing framework, and neighboring examples. Read language/runtime-specific instructions.
2. Cover observable outcomes, boundary inputs, failure behavior, and regressions tied to the change. Prefer behavior-focused cases over snapshot-only assertions.
3. Keep fixtures local and deterministic. Do not call external services or use credentials unless the task requires a controlled integration environment.
4. Add tests beside the existing suite and run the narrowest relevant test command. Do not encode unimplemented assumptions.
5. Use pytest-coverage for coverage work. Use mutation-testing when checking that assertions detect seeded faults; test generation alone does not prove test quality.
