---
work_package_id: WP14
title: Reference frontend
dependencies:
- WP03
requirement_refs:
- FR-015
- NFR-004
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T07:03:18.781329+00:00'
subtasks:
- T053
- T054
- T055
shell_pid: "16336"
agent: "claude:opus:implementer:implementer"
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: frontend/
execution_mode: code_change
owned_files:
- frontend/index.html
- frontend/app.js
- frontend/style.css
tags: []
---

# WP14 — Reference frontend

## Objective

Build the static, framework-free reference UI (FR-015) served at `/` that fetches the live
catalog from `/mcp` (Streamable HTTP), groups tools by feature area, follows all pagination
cursors for resources/prompts, shows a single inline error per section when `/mcp` is
unreachable, and renders offline after first load (NFR-004). Documentation-only — no tool
execution.

## Context
- Spec "Frontend Spec" in [../../../PRD.md](../../../PRD.md) and FR-015; served by WP03's HTTP
  transport. No Node, no build step, no framework, no external/CDN deps (C-004, NFR-004).

## Implement command
```bash
spec-kitty agent action implement WP14 --agent <name>
```

## Subtasks

### T053 — `frontend/index.html`
- Fixed top navbar: mcpbin name left, protocol badge `MCP 2025-03-26` right.
- Left sidebar: three collapsible sections — Tools, Resources, Prompts — each item clickable.
- Main content: detail panel for the selected item. No external resources referenced.

### T054 — `frontend/app.js` (vanilla JS)
- Speak MCP over Streamable HTTP to `/mcp`: initialize, then `tools/list` / `resources/list` /
  `prompts/list`, **following every `nextCursor`** to build complete lists.
- Tools view (default): cards with name (monospace), description, and input schema as a
  formatted JSON block; **grouped by feature area** with headings (Echo, Response Types, Errors,
  Delays, Schema, Notifications, Sampling, Inspect). Derive grouping from a name→area map or
  tool naming.
- Resources view: URI, name, description, MIME type. Prompts view: name, description, arguments
  table (name/required/description).
- **Error state**: if `/mcp` is unreachable, each section shows exactly
  `"Could not reach MCP server at /mcp"` — no uncaught exception.

### T055 — `frontend/style.css`
- Layout for navbar/sidebar/detail; readable cards; collapsible sections. System fonts only
  (no CDN fonts/icons). Must render correctly fully offline after first load.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] `uv run mcpbin --transport http` → `/` renders the catalog grouped by feature area.
- [ ] Resources/prompts lists follow all cursors to show complete lists.
- [ ] Stopping `/mcp` → each section shows the single inline error, no JS exception in console.
- [ ] Zero external/CDN requests; renders offline after first load (NFR-004).
- [ ] No "run tool" controls (documentation-only).
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- Implementing a minimal MCP-over-Streamable-HTTP client in vanilla JS (initialize + list +
  cursor-following) is the main effort — keep it small and robust. Reviewer: verify the
  cursor-following loop terminates when `nextCursor` is absent and that the offline/error path
  is exercised (kill `/mcp`, reload).
- Feature-area grouping needs a name→area mapping; keep it data-driven and easy to extend.

## Activity Log

- 2026-06-13T07:03:21Z – claude:opus:implementer:implementer – shell_pid=16336 – Assigned agent via action command
- 2026-06-13T07:05:46Z – claude:opus:implementer:implementer – shell_pid=16336 – Static UI; server serves / + app.js + style.css; POST /mcp reaches MCP (verified via ASGI probe)
