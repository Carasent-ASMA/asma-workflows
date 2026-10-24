---
description: "Scaffold a new widget in a domain app following ASMA widget architecture"
---
<!-- Generated from .github/prompts/new-widget.prompt.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# New Widget Scaffolding

Create a new widget following the ASMA widget-based micro-frontend architecture.

## Widget Architecture

- Widget-level granularity (not app-level)
- Zero module duplication via Import Maps
- Runtime isolation with shared dependencies
- Supports standalone & integrated modes

## Naming Convention

- Widget names: kebab-case, descriptive
- Pattern: `{domain}-widget-{purpose}` (e.g., `chat-widget-inbox`, `directory-widget-list`)
- File: `src/widgets/{widget-name}/index.tsx`

## Standard Widget Structure

```
src/widgets/{widget-name}/
├── index.tsx              # Widget entry point and exports
├── {WidgetName}.tsx       # Main widget component
├── components/            # Widget-specific components
├── hooks/                 # Widget-specific hooks
└── types.ts               # Widget-specific types
```

## Widget Entry Point Template

The entry point should export:

1. A default React component
2. Widget metadata (name, version, dependencies)
3. Mount/unmount lifecycle hooks if needed

## Instructions

1. Ask which domain app the widget belongs to (e.g., `chat`, `directory`, `artifact`)
2. Ask for the widget purpose/name
3. Create the widget directory structure
4. Create the entry point with proper exports
5. Create the main component with TypeScript
6. Register the widget in the app's widget index
7. Use shared dependencies from Import Maps (React, MUI, etc.) — don't bundle them

## Rules

- TypeScript only (`.tsx`)
- Use existing React/Vite patterns from the target app
- Import shared modules from workspace packages, not duplicated
- Follow existing component patterns in the domain app
