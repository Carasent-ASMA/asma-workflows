---
name: performance-audit
description: "Use when asked to measure frontend bundle size, loading, rendering, or runtime performance. For chunking and import-map decisions use bundle-optimization; do not run an unrequested release-wide audit."
---
<!-- Generated from .github/skills/performance-audit/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Performance audit

1. Define the measured page or workload, environment, baseline, and symptom. Gather evidence before proposing optimization.
2. For ASMA frontend bundle/chunk analysis, follow bundle-optimization and target app build scripts. For server or database paths, use the runtime's existing profiler and domain guidance.
3. Record reproducible measurements, tool/version, sample conditions, and known noise. Separate measurements from hypotheses.
4. Identify the largest verified cost and propose the smallest reversible change. Avoid adding instrumentation or dependencies unless requested and justified.
5. Re-measure the same workload and compare it with baseline. If the local environment cannot reproduce production behavior, state that boundary.
