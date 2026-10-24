---
name: chrome-devtools
description: 'Expert-level browser automation, debugging, and performance analysis using Chrome DevTools MCP. Use for interacting with web pages, capturing screenshots, analyzing network traffic, and profiling performance.'
license: MIT
---
<!-- Generated from .github/skills/chrome-devtools/SKILL.md by _tools/scripts/sync-module-agent-config.py; do not edit. -->

# Chrome DevTools Agent

## Overview

A specialized skill for controlling and inspecting a live Chrome browser. This skill leverages the `chrome-devtools` MCP server to perform a wide range of browser-related tasks, from simple navigation to complex performance profiling.

## When to Use

Use this skill when:

- **Browser Automation**: Navigating pages, clicking elements, filling forms, and handling dialogs.
- **Visual Inspection**: Taking screenshots or text snapshots of web pages.
- **Debugging**: Inspecting console messages, evaluating JavaScript in the page context, and analyzing network requests.
- **Performance Analysis**: Recording and analyzing performance traces to identify bottlenecks and Core Web Vital issues.
- **Emulation**: Resizing the viewport or emulating network/CPU conditions.

## Tool Categories

### 1. Navigation & Page Management

- `new_page`: Open a new tab/page.
- `navigate_page`: Go to a specific URL, reload, or navigate history.
- `select_page`: Switch context between open pages.
- `list_pages`: See all open pages and their IDs.
- `close_page`: Close a specific page.
- `wait_for`: Wait for specific text to appear on the page.

### 2. Input & Interaction

- `click`: Click on an element (use `uid` from snapshot).
- `fill` / `fill_form`: Type text into inputs or fill multiple fields at once.
- `hover`: Move the mouse over an element.
- `press_key`: Send keyboard shortcuts or special keys (e.g., "Enter", "Control+C").
- `drag`: Drag and drop elements.
- `handle_dialog`: Accept or dismiss browser alerts/prompts.
- `upload_file`: Upload a file through a file input.

### 3. Debugging & Inspection

- `take_snapshot`: Get a text-based accessibility tree (best for identifying elements).
- `take_screenshot`: Capture a visual representation of the page or a specific element.
- `list_console_messages` / `get_console_message`: Inspect the page's console output.
- `evaluate_script`: Run custom JavaScript in the page context.
- `list_network_requests` / `get_network_request`: Analyze network traffic and request details.

### 4. Emulation & Performance

- `resize_page`: Change the viewport dimensions.
- `emulate`: Throttling CPU/Network or emulating geolocation.
- `performance_start_trace`: Start recording a performance profile.
- `performance_stop_trace`: Stop recording and save the trace.
- `performance_analyze_insight`: Get detailed analysis from recorded performance data.

## Workflow Patterns

### Pattern A: Identifying Elements (Snapshot-First)

Always prefer `take_snapshot` over `take_screenshot` for finding elements. The snapshot provides `uid` values which are required by interaction tools.

```markdown
1. `take_snapshot` to get the current page structure.
2. Find the `uid` of the target element.
3. Use `click(uid=...)` or `fill(uid=..., value=...)`.
```

### Pattern B: Troubleshooting Errors

When a page is failing, check both console logs and network requests.

```markdown
1. `list_console_messages` to check for JavaScript errors.
2. `list_network_requests` to identify failed (4xx/5xx) resources.
3. `evaluate_script` to check the value of specific DOM elements or global variables.
```

### Pattern C: Performance Profiling

Identify why a page is slow.

```markdown
1. `performance_start_trace(reload=true, autoStop=true)`
2. Wait for the page to load/trace to finish.
3. `performance_analyze_insight` to find LCP issues or layout shifts.
```

## Best Practices

- **Context Awareness**: Always run `list_pages` and `select_page` if you are unsure which tab is currently active.
- **Snapshots**: Take a new snapshot after any major navigation or DOM change, as `uid` values may change.
- **Timeouts**: Use reasonable timeouts for `wait_for` to avoid hanging on slow-loading elements.
- **Screenshots**: Use `take_screenshot` sparingly for visual verification, but rely on `take_snapshot` for logic.

## Live authenticated debugging — attach to the developer's own Chrome (VPN + login reuse)

The highest-leverage setup for debugging a **deployed, authenticated** environment (e.g.
`*.dev.adopus.no` behind VPN + SSO): instead of letting the MCP launch a throwaway browser, **attach it
to a Chrome the developer already runs and is logged in to**. The agent then inspects the live
authenticated session — console, network (full URLs + response MIME), and `evaluate_script` — directly,
with zero copy-paste. `WebFetch`/`curl` can't reach these pages (auth + VPN); this can.

### One-time setup (automated by the agent)

The agent should set this up automatically on first use. Here's the canonical configuration:

#### 1. MCP Config (`.vscode/mcp.json` — committed, shared across team)

```json
{
  "servers": {
    "chrome-devtools": {
      "args": ["--browserUrl", "http://127.0.0.1:9222"],
      "command": "chrome-devtools-mcp",
      "type": "stdio"
    }
  }
}
```

Uses `--browserUrl` (not `--autoConnect`) because it's more reliable across Chrome versions.
`--autoConnect` requires Chrome 144+ AND a manual `chrome://inspect/#remote-debugging` toggle
that does not persist reliably across Chrome restarts. `--browserUrl` with a fixed port and
persistent profile is deterministic.

#### 2. Launch debug Chrome — ALWAYS use `asma debug chrome`

**This is the ONLY supported way to launch the debug Chrome.** The ASMA CLI ships a
`debug chrome` command that handles everything: starting Chrome with the right flags,
a persistent profile (`~/.chrome-debug`), idempotent reuse of an already-running instance,
and waiting for the endpoint to be ready.

```bash
asma debug chrome
```

What it does:
- Checks if debug Chrome is already running on port 9222 → reuses it if so
- Launches Chrome with `--remote-debugging-port=9222 --user-data-dir=~/.chrome-debug --no-first-run --no-default-browser-check`
- Waits up to 15s for the endpoint to come up and reports the browser version
- Prints the attach hint for the MCP

The profile at `~/.chrome-debug` is **persistent** — sign into Google and ASMA apps once, they survive forever:
- `Default/Login Data` — saved passwords & account tokens
- `Default/Cookies` — session cookies
- `Default/Preferences` + `Secure Preferences` — Chrome settings
- `Default/Sync Data/` — Chrome sync state

**Never** launch Chrome manually with `--remote-debugging-port` — always use `asma debug chrome`.
**Never** create a fish function or alias for this — the CLI is the single source of truth.

#### 3. Programmatic remote debugging enablement (Chrome default profile)

Only needed if `--autoConnect` is ever used (not recommended). The Chrome preference can be set
programmatically instead of requiring the manual `chrome://inspect/#remote-debugging` toggle:

```python
import json
path = '$HOME/Library/Application Support/Google/Chrome/Local State'
with open(path, 'r') as f:
    data = json.load(f)
data.setdefault('devtools', {})
data['devtools']['remote_debugging'] = {'user-enabled': True}
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
```

This sets `devtools.remote_debugging.user-enabled = true` in `Local State`.
**Must be done while Chrome is closed** — Chrome overwrites `Local State` on shutdown.

#### 4. Verify connectivity

```bash
asma debug chrome     # launch or verify
curl -s http://127.0.0.1:9222/json/version | jq -r '.Browser'
# Should return: Chrome/150.x.y.z
```

If the MCP tools fail with "Could not find DevToolsActivePort", restart the MCP server:
`Cmd+Shift+P` → "MCP: Restart Server" → `chrome-devtools`.

### Agent bootstrap sequence (every session)

When you (the agent) need browser access, run this checklist:

1. **Launch/reuse debug Chrome via the CLI:**
   ```bash
   asma debug chrome
   ```
   This is idempotent — safe to run every session. It either reuses an existing debug Chrome
   or launches a fresh one on the persistent profile.

2. **Verify MCP connectivity:**
   Run `mcp_chrome_devtoo_list_pages`. If it fails:
   - Ask developer to restart MCP server: `Cmd+Shift+P` → "MCP: Restart Server" → `chrome-devtools`.
   - If still failing, Chrome may have died — re-run `asma debug chrome`.

3. **Sign in (first time only):** If this is a new profile, the developer signs into their
   Google account once. The profile persists — subsequent sessions skip this.

### Troubleshooting quick reference

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Could not find DevToolsActivePort" | Chrome not running or MCP server stale | `asma debug chrome` + restart MCP server |
| MCP connects but no pages | Chrome launched without `--remote-debugging-port` | Kill Chrome, run `asma debug chrome` |
| "DevTools remote debugging requires non-default data directory" | Forgot `--user-data-dir` | Run `asma debug chrome` (it handles this) |
| `curl` to 9222 returns nothing | Chrome 150+ changed the HTTP endpoint | `asma debug chrome` waits for the WS endpoint; HTTP fallback works with `--remote-debugging-port` |
| Profile starts fresh every time | Wrong `--user-data-dir` path | Always use `asma debug chrome` — it sets `~/.chrome-debug` |

### Workflow once attached

1. `navigate_page` to the failing URL (or the dev opens it in the attached tab; `select_page` to focus).
2. `list_network_requests` — read the **real** request URLs and response MIME types. This is the payoff:
   the console alone collapses a failing module URL to its bare filename, hiding whether the path is wrong.
3. `evaluate_script` for runtime state (injected platform, localStorage overrides, feature flags).
4. `list_console_messages` for the error stream.

### Worked example — native-ESM widget "Expected a JavaScript module … MIME text/html"

A widget/micro-app whose chunks 404 to the SPA's `index.html` (→ `text/html` → strict-MIME rejection) is
a **base-resolution** bug. The decisive evidence is the *request URL*, which only the network list shows:

```js
// full URLs of the failing chunks — is it the site root, or the correct /cdn path?
performance.getEntriesByType('resource').map(r => r.name)
  .filter(n => /rolldown-runtime|AppProviders|vendor-/.test(n))
// the base injected for the app
JSON.stringify(window.__ASMA_PLATFORM__?.apps?.['asma-app-directory'])
// dev overrides that would corrupt the base to the bare origin
Object.entries(localStorage).filter(([k]) => k.startsWith('import-map-override') || k === 'esm-overrides')
```

- `…adopus.no/chunks/…` (site **root**) ⇒ the app's ESM `base` resolved to the bare origin — a stale
  `import-map-override:<app>` / `esm-overrides` localStorage value winning over the correct injected
  `/cdn/<app>/<ver>/` base. **Fix:** clear the override.
- correct `/cdn/<app>/<ver>/chunks/…` **but returns HTML** ⇒ deploy/stale-hash gap (the entry references
  chunk hashes not published at that version). **Fix:** redeploy the widget build so entry + chunks ship
  from one build.

### Caveats

- While attached, the MCP can do anything the logged-in session can — it's the developer's own browser.
  Don't point the debug window at production.
- The `.vscode/mcp.json` with `--browserUrl=http://127.0.0.1:9222` is **committed and shared** —
  every developer on the team uses the same port and profile layout.
  The only per-developer piece is signing into Google/ASMA once in the persistent `~/.chrome-debug` profile.
