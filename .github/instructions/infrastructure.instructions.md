---
applyTo: 'infrastructure/**'
---
<!-- Generated from .github/instructions/infrastructure.instructions.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Infrastructure Instructions

Apply these rules when working on infrastructure, ArgoCD, and deployment configurations.

## YAML Patterns

-   4-space indentation, always.
-   Use single quotes for string values.
-   Env value files: `{env}.yaml` (`dev.yaml`, `stage.yaml`, `prod.yaml`).
-   ArgoCD app files: `{service-name}-app.yaml`.
-   Service names in kebab-case: `asma-njs-auth`, `asma-app-shell`.
-   Always use the dual-source pattern (both `asma-argocd` + `asma-helm-chart` repos referenced).

## Environment Naming

-   Valid environments: `dev`, `test`, `stage`, `prod`, `prod-adcuris`.
-   Variables suffixed `_NONPROD` are for dev/test/stage only — never use in prod configs.
-   Dev: verbose logging, lower resources.
-   Prod: stricter security, higher replicas/resources.

## Secrets Handling

-   **NEVER** put actual secret values in YAML files.
-   Use `secrets: true` / `secretsCommon: true` flags to reference externally managed secrets.
-   No hardcoded passwords, tokens, or sensitive data.

## Critical Rules

**DO:**

-   Preserve existing comments when modifying files.
-   Keep env configs consistent across environments.
-   Validate YAML syntax.
-   Include comments for non-obvious configurations.
-   Always update `app-of-apps/apps.yaml` when adding a new service.
-   Always include health checks and resource limits in service configs.

**DON'T:**

-   Modify production files without explicit user confirmation.
-   Run `kubectl apply` directly (GitOps only).
-   Remove the dual-source pattern.
-   Break YAML syntax.

## Reference

For comprehensive ArgoCD patterns: `infrastructure/asma-argocd/.github/copilot-instructions.md`
