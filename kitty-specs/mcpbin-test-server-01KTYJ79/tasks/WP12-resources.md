---
work_package_id: WP12
title: Resources
dependencies:
- WP03
requirement_refs:
- FR-006
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning/base branch devs/ruhulla; completed work merges into devs/ruhulla. Execution worktree is allocated per computed lane from lanes.json.
subtasks:
- T047
- T048
- T049
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/resources.py
execution_mode: code_change
owned_files:
- src/mcpbin/resources.py
- tests/test_resources.py
tags: []
---

# WP12 — Resources

## Objective

Implement every MCP resource shape (FR-006): plain text, markdown, binary blob, a large
paginated family (≥100 entries to force `resources/list` pagination), a URI template
`mcpbin://dynamic/{id}`, and a `mcpbin://missing` resource that is listed but always
not-found on read.

## Context
- Contract: [../contracts/resources.md](../contracts/resources.md).
- Registered via `register(app, profile, ctx)` and discovered by the registry's guarded
  `mcpbin.resources` import (WP02). Under `tools-only`/`minimal` the registry skips this module
  (profile gating handled in WP03).
- Pagination of `resources/list` is wired in WP03; this WP just supplies a large enough catalog.

## Implement command
```bash
spec-kitty agent action implement WP12 --agent <name>
```

## Subtasks

### T047 — `resources.py` static + large family
- `mcpbin://text/plain` (`text/plain`), `mcpbin://text/markdown` (`text/markdown`),
  `mcpbin://blob/binary` (base64 blob, e.g. `application/octet-stream`) — deterministic content.
- A **large paginated family**: register ≥100 resources (e.g. `mcpbin://large/paginated/{n}`
  for n in 0..120, or a documented set) so `resources/list` needs multiple cursor pages
  (SC-004). These are legitimately a "large resource list" per PRD — not synthetic padding.

### T048 — template + missing not-found
- `mcpbin://dynamic/{id}` URI template: `id ∈ {alpha, beta, gamma}` → distinct short text
  naming the id; any other id → not-found error (the URI resolves but content doesn't exist).
- `mcpbin://missing` → listed in `resources/list` but **always** returns a not-found error on
  read (simulates deleted/unavailable). Distinct from the unknown-template case.

### T049 — `tests/test_resources.py`
- `resources/list` (following all cursor pages) includes text/markdown/blob, the template
  entry, `mcpbin://missing`, and ≥100 total.
- Read text/markdown → text; blob → valid base64. `dynamic/alpha|beta|gamma` distinct; unknown
  id and `mcpbin://missing` → not-found errors. Content deterministic across reads (NFR-001).

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] All documented resource shapes present; ≥100 total to force pagination.
- [ ] Template resolves alpha/beta/gamma; unknown id and `mcpbin://missing` → not-found.
- [ ] `uv run pytest tests/test_resources.py` passes (following cursors).
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- **verify-on-impl**: how the pinned FastMCP registers resource templates and signals a
  not-found read (exception vs error result). Reviewer: confirm the unknown-template vs
  `missing` distinction is observable and that the large family genuinely spans >1 list page.
