---
name: security-check
description: "Use when asked to review code, configuration, or dependencies for a scoped security risk. Use only scanners already available in the target repository; a source review is not a complete audit."
---
<!-- Generated from .github/skills/security-check/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Scoped security review

1. Confirm the changed system, threat boundary, data sensitivity, and requested review depth. Read security instructions and relevant architecture.
2. Inspect input validation, authorization, secret handling, logging, dependency use, path/process boundaries, and error exposure relevant to the change.
3. Run only configured security or dependency checks that exist in the repository and fit the task. Do not install scanners or transmit source externally without authorization.
4. Report findings with evidence, impact, and a concrete fix. Separate confirmed defects from possible risks and record examined files/commands.
5. State untested boundaries; do not describe a scoped review as a complete audit or certification.
