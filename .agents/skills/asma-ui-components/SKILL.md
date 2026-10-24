---
name: asma-ui-components
description: "Choose and use shared ASMA UI controls, tables, icons, date/time, rich-text, dialogs, widgets and notifications. For Figma mapping use asma-figma-design-system; for ui-core parity, accessibility authoring or MUI-free migration use the specialized skill."
argument-hint: "Choose and use ASMA shared UI components correctly"
---
<!-- Generated from .github/skills/asma-ui-components/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# ASMA UI Components

Use this skill when frontend work touches reusable UI in ASMA modules.

## Core Rule

Prefer shared components from `asma-modules/shared/asma-ui-*` before using raw MUI, ad hoc SVGs, or app-local generic UI wrappers.

Domain-specific composition can stay in the app slice, but reusable controls, icons, tables, date/time inputs, rich text editors, dialogs, notifications, and widget shells should come from the shared UI families when possible.

## Required Reference

Before implementing or reviewing UI, read the shared catalog:

- `asma-modules/_docs/ASMA_UI_COMPONENTS.md`

When the source is Figma / Design System (fileKey `wXrXt5uKNNzV2DnQCgyYZH`), also read:

- `.cursor/skills/asma-figma-design-system/SKILL.md`
- `.cursor/skills/asma-figma-design-system/component-map.md`

Never ship Figma MCP Tailwind stubs — map to `asma-ui-*` exports.

If the current workspace is a child app or shared package, the file lives in the parent polyrepo root at:

- `../..` or another parent hop to `asma-modules/_docs/ASMA_UI_COMPONENTS.md`, depending on the current repo depth

## Component Family Selection

Use these package defaults:

- `asma-ui-core` for buttons, inputs, selects, chips, dialogs, popovers, menus, links, loading/empty states, form wrappers, widgets, and module titles.
- `asma-ui-datetime` for date and time input fields.
- `asma-ui-table` for table-heavy views, TanStack table integration, row actions, DnD, sticky headers/footers, expandable rows, and persisted table state.
- `asma-ui-icons` for icons. Do not create local SVG components unless no shared icon exists or the icon is domain-specific to one slice.
- `asma-ui-richeditor` for rich text editing or read-only rich content.
- `asma-ui-notistack` for application snackbar providers, snackbar helpers, alert variants, and notistack integration.

## Workflow

1. Identify the UI need and owning slice.
2. Read `ASMA_UI_COMPONENTS.md` for the matching component family.
3. Search the current slice for existing usage of the same component family and follow local patterns.
4. Import from package roots such as `asma-ui-core`, `asma-ui-table`, or `asma-ui-icons` unless the package documents a different public path.
5. Pass required `dataTest` props and keep selectors stable for tests — but do **not** reach for them from a vitest/jsdom test without reading the gotcha below first.
6. Keep app-specific business logic in the app slice and generic UI behavior in shared packages.
7. If a shared component is missing a generic capability, prefer improving the shared package over duplicating a local generic component.
8. Validate with the narrowest relevant component test, typecheck, lint check, or diagnostics.

## Trap: `dataTest` renders as `data-testid`, but apps query `data-test`

**`getByTestId` cannot find an `asma-ui-core` component by its `dataTest` prop.** This has cost real
debugging time more than once, in both directions — writing the test first, and writing the component
first.

Measured against `asma-ui-core@3.49.0`: **28 of 31** components that accept `dataTest` render it as
**`data-testid`** (`StyledButton`, `StyledInputField`, `StyledCheckbox`, `StyledRadio`,
`StyledRadioGroup`, `StyledSearchField`, `StyledChip`, `StyledBadge`, `StyledDialog` + title/actions,
`MinimizableDialog`, `StyledEmptyPage`, `VirtualizedList`, `StyledLabel`, `StyledFormLabel`,
`StyledModuleTitle`, `DynamicToolbar`, …). Only **3** render `data-test`: `StyledDialogContent`,
`StyledFilteredEmptyState`, `StyledMenuItem`.

Consuming apps configure testing-library the other way, because *their own* JSX writes `data-test`
(e.g. `asma-app-editor/src/test/setup.ts`: `configure({ testIdAttribute: 'data-test' })`, chosen
because that app has 59 `data-test` attributes against 2 `data-testid`). So inside such an app:

- a `data-test` **you wrote in your own JSX** → `getByTestId` works;
- a `dataTest` **you passed to a ui-core component** → `getByTestId` silently matches nothing.

Silently is the problem: the failure is `Unable to find an element by: [data-test="…"]`, which reads
like the component did not render at all, so the hunt starts in the wrong place.

**What to do instead** — query the way a user perceives the control, and scope it:

```tsx
// Anchor on an element whose data-test you control (a row wrapper, a section), then query by role.
const row = (id: string) => within(screen.getByTestId(`qnr-alternative-${id}`))

expect(row('a-1').getByRole('button', { name: text.removeAlternative })).toBeTruthy()
row('a-1').getByRole('button', { name: text.moveAlternativeUp }).click()
```

Scoping is what makes this work when many rows repeat the same accessible name. It is also the better
test: it asserts the control is reachable by its label, which a test id never proves.

Keep passing `dataTest` — Playwright specs and production debugging use it, and it is required by the
review checklist. Just do not query it from jsdom.

## Common Choices

- Standard action: `StyledButton`
- Text input: `StyledInputField`
- Search input: `StyledSearchField`
- Boolean input: `StyledCheckbox` or `StyledSwitch`
- Single-choice input: `StyledRadioGroup` with `StyledRadio`
- Adaptive select: `StyledDynamicSelect`
- MUI select: `StyledSelect` with `StyledSelectItem`
- Autocomplete: `StyledSelectAutocomplete`
- Multi-line text: `StyledTextarea`
- Date/range input: `StyledDatePicker`
- Time input: `StyledTimePicker`
- Table/list grid: `StyledTable`
- Dialog: `StyledDialog` family or `MinimizableDialog`
- Filter popover: `StyledFilterMenu`
- Empty state: `StyledEmptyPage` or `StyledFilteredEmptyState`
- Copy affordance: `CopyWrapper` or `CopyButton`
- Rich text: `RichInput`
- Snackbar: `SnackbarProvider`, `enqueueSnackbar`, and shared snackbar processors

## Forms adapter (`asma-ui-core/forms`)

Form state, validation timing, and focus wiring live in the shared react-hook-form adapter, not per app (ASMA-7729):

```ts
// app `src/forms/index.ts` — the only binding an app writes
import { createAsmaForms } from 'asma-ui-core/forms'
import { i18n } from '@/i18n'

export const { AsmaFieldController, submitChanged } = createAsmaForms({ getLanguageCode: () => i18n.code })
export { focusFormField, getDirtyValues, useAsmaForm } from 'asma-ui-core/forms'
```

- `useAsmaForm` pins the fleet contract: `mode: 'onBlur'`, `reValidateMode: 'onSubmit'`, `criteriaMode: 'all'`, `shouldFocusError: true` (apps never override).
- Per-app options are explicit: `browserAutofill` (shell login/auth forms) enables mount validation, autofill sync, merged ref, touched-gated errors, and touch-on-failed-submit as one design. `requestFocus` is a per-field prop for controls that own their ref (comboboxes, rich editors).
- `render` receives a typed `value` (`FieldPathValue<TFieldValues, TName>`).
- Never import `asma-ui-core/forms` in a Formik app (`adopus-app-directory`, `crm`): the subpath requires react-hook-form, which Formik apps do not install. The root `asma-ui-core` barrel never imports it either.

Plan of record: `_docs/frontend/plans/2026-09-28-00-28-plan-forms-adapter-into-asma-ui-core.md`.

## Review Checklist

When reviewing ASMA frontend UI, check that:

- shared components are used before raw MUI or local duplicates
- imports come from public package roots
- required `dataTest` props are present
- icons come from `asma-ui-icons` when available
- tables use `StyledTable` when table behavior is non-trivial
- date/time inputs use `asma-ui-datetime`
- snackbar usage is compatible with `asma-ui-notistack`
- custom component code is slice-specific rather than generic shared UI
- form state goes through the shared `asma-ui-core/forms` adapter binding (`src/forms/index.ts`), never an app-local `AsmaFieldController` copy
- tests verify behavior instead of shared component implementation details

## Related

- UX contracts that drive field/error wording and placement: [`_docs/ux/index.md`](../../../_docs/ux/index.md) (form-error pattern).
- Styling parity and the single ledger: [Figma styling authority](../../../_docs/ux/architecture/2026-09-26-04-07-architecture-figma-styling-authority.md).
