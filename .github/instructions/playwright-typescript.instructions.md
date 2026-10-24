---
description: 'Playwright test generation instructions'
applyTo: '**/*.spec.ts, **/*.spec.tsx, **/*.feature, **/*.steps.ts'
---
<!-- Generated from .github/instructions/playwright-typescript.instructions.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

## Test Writing Guidelines

### Code Quality Standards
- **Locators**: Prioritize user-facing, role-based locators (`getByRole`, `getByLabel`, `getByText`, etc.) for resilience and accessibility. Use `test.step()` to group interactions and improve test readability and reporting.
- **Assertions**: Use auto-retrying web-first assertions. These assertions start with the `await` keyword (e.g., `await expect(locator).toHaveText()`). Avoid `expect(locator).toBeVisible()` unless specifically testing for visibility changes.
- **Timeouts**: Rely on Playwright's built-in auto-waiting mechanisms. Avoid hard-coded waits or increased default timeouts.
- **Clarity**: Use descriptive test and step titles that clearly state the intent. Add comments only to explain complex logic or non-obvious interactions.


### Test Structure
- **Imports**: Start with `import { test, expect } from '@playwright/test';`.
- **Organization**: Group related tests for a feature under a `test.describe()` block.
- **Hooks**: Use `beforeEach` for setup actions common to all tests in a `describe` block (e.g., navigating to a page).
- **Titles**: Follow a clear naming convention, such as `Feature - Specific action or scenario`.


### File Organization
- **Location**: Store all test files in the `tests/` directory.
- **Naming**: Use the convention `<feature-or-page>.spec.ts` (e.g., `login.spec.ts`, `search.spec.ts`).
- **Scope**: Aim for one test file per major application feature or page.

### Assertion Best Practices
- **UI Structure**: Use `toMatchAriaSnapshot` to verify the accessibility tree structure of a component. This provides a comprehensive and accessible snapshot.
- **Element Counts**: Use `toHaveCount` to assert the number of elements found by a locator.
- **Text Content**: Use `toHaveText` for exact text matches and `toContainText` for partial matches.
- **Navigation**: Use `toHaveURL` to verify the page URL after an action.


## Example Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Movie Search Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application before each test
    await page.goto('https://debs-obrien.github.io/playwright-movies-app');
  });

  test('Search for a movie by title', async ({ page }) => {
    await test.step('Activate and perform search', async () => {
      await page.getByRole('search').click();
      const searchInput = page.getByRole('textbox', { name: 'Search Input' });
      await searchInput.fill('Garfield');
      await searchInput.press('Enter');
    });

    await test.step('Verify search results', async () => {
      // Verify the accessibility tree of the search results
      await expect(page.getByRole('main')).toMatchAriaSnapshot(`
        - main:
          - heading "Garfield" [level=1]
          - heading "search results" [level=2]
          - list "movies":
            - listitem "movie":
              - link "poster of The Garfield Movie The Garfield Movie rating":
                - /url: /playwright-movies-app/movie?id=tt5779228&page=1
                - img "poster of The Garfield Movie"
                - heading "The Garfield Movie" [level=2]
      `);
    });
  });
});
```

## Behaviour scenarios with playwright-bdd (opt-in trial)

Applies when the owning plan declares `behaviour_scenarios: bdd`
([Behaviour scenarios](../skills/create-implementation-plan/SKILL.md#behaviour-scenarios-opt-in-trial)).
The approved scenario text comes from the plan; this section covers only how
it executes. During the pilot, runs are manual and CI is unchanged.

- **Layout.** Under the repository's Playwright test root (`testDir`):
  `features/<capability>.feature` and `steps/<domain-concept>.steps.ts`.
  Generated specs go to `.features-gen/` at the repository root: gitignored
  (`**/.features-gen/**/*.spec.js` and `*.spec.js.map`), never edited, never
  committed. Verify no other runner collects them: add `**/.features-gen/**` to
  the unit runner's `exclude`, and confirm the existing E2E script still
  discovers only its own specs.
- **Configuration.** A separate `playwright.bdd.config.ts` imports the base
  config and sets `testDir` from `defineBddConfig({ features, steps })`, so
  `retries: 0`, workers, reporters and `webServer` are inherited. Keep
  `missingSteps: 'fail-on-gen'` and `arityCheck` at their defaults. Add the
  script `e2e:bdd`, which runs `bddgen -c playwright.bdd.config.ts` and then
  `playwright test -c playwright.bdd.config.ts`, both through the package
  manager as the [Node project rules](node-project.instructions.md) require.
  The existing `e2e` script and its CI job stay untouched.
- **Dependency.** Pin `playwright-bdd` to an exact version in the adopting
  repository only, inside its declared `@playwright/test` peer range for the
  repository's installed version. Record the pin and its check in the plan,
  not here.
- **Feature files.** Untagged `Feature:` line, then scenarios. Each scenario
  carries exactly one tag, its identity tag `@<TASK-KEY>-SCN-<nnn>`, and nothing
  else: no `@skip`, `@fixme`, `@only`, `@fail`, `@slow`, `@retries:N`,
  `@timeout:N` or `@mode:*`, no `Background:`, no `Rule:`, no `#` comments
  inside a scenario. The body equals the approved plan block under the plan
  skill's normalized hash; a change is a recorded amendment first.
- **Meta-test.** The adopting repository keeps a unit-runner meta-test over
  `features/**/*.feature` asserting: every id matches
  `^[A-Z][A-Z0-9]+-\d+-SCN-\d{3}$` and is unique; each scenario has exactly one
  tag and it is the id; no tag on `Feature:` or `Rule:`; no `Background:` or
  `Rule:`. It proves reference integrity and the mechanical half of the freeze
  rule, never execution or coverage.
- **Steps.** `import { createBdd } from 'playwright-bdd'`. Organize by domain
  concept, never by feature file. Each step is a thin call into a page object
  or helper using role-based locators; no step calls another step; no shared
  mutable state beyond Playwright fixtures. Gherkin steps already report as
  steps: do not wrap their bodies in `test.step()`.
- **Runs and evidence.** Run `pnpm e2e:bdd` at zero retries. Copy the
  per-scenario `list` lines, the exact command and the HEAD SHA into the task's
  Verification and evidence. `bddgen export --unused-steps` lists unused
  steps for the pilot evaluation. The HTML report is diagnostic; JUnit
  is optional.
- **Readiness before another repository adopts this.** An interaction
  Playwright config (not visual regression); `@playwright/test` inside the
  peer range; a deterministic harness reachable without a live backend or
  login, or a harness task first; a named repository owner; the runner
  exclusions above verified; the meta-test in place; lower-layer tests for the
  changed decision logic; and, only when CI adoption is decided after the
  pilot, an identified insertion point for `bddgen` before `playwright test`.

## Test Execution Strategy

1. **Initial Run**: Execute tests with `npx playwright test --project=chromium`
2. **Debug Failures**: Analyze test failures and identify root causes
3. **Iterate**: Refine locators, assertions, or test logic as needed
4. **Validate**: Ensure tests pass consistently and cover the intended functionality
5. **Report**: Provide feedback on test results and any issues discovered

## Quality Checklist

Before finalizing tests, ensure:
- [ ] All locators are accessible and specific and avoid strict mode violations
- [ ] Tests are grouped logically and follow a clear structure
- [ ] Assertions are meaningful and reflect user expectations
- [ ] Tests follow consistent naming conventions
- [ ] Code is properly formatted and commented