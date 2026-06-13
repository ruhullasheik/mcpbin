---
work_package_id: WP11
title: Protocol inspection tool
dependencies:
- WP03
requirement_refs:
- FR-012
- FR-013
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T06:49:39.866439+00:00'
subtasks:
- T044
- T045
- T046
shell_pid: '14680'
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/tools/inspect.py
execution_mode: code_change
owned_files:
- src/mcpbin/tools/inspect.py
- tests/test_inspect.py
tags: []
---

# WP11 — Protocol inspection tool

## Objective

Implement `inspect_session` (FR-012) returning live session metadata — protocol version,
client info, negotiated capabilities, transport, and a `requestCount` that increments across
calls in the same session.

## Context
- Contract: [../contracts/tools.md](../contracts/tools.md) → "inspect";
  [../contracts/protocol.md](../contracts/protocol.md) → "Session inspection".
- Uses `session.py` (`SessionStore`/`SessionState`) from WP02. Research R9 — **verify-on-impl**
  for session identity, `clientInfo`, `protocolVersion`, negotiated capabilities.
- `register(app, profile, ctx)` contract; conftest from WP03.

## Implement command
```bash
spec-kitty agent action implement WP11 --agent <name>
```

## Subtasks

### T044 — `tools/inspect.py`
- `inspect_session` returns:
  `{protocolVersion: "2025-03-26", clientInfo: {name, version}, negotiatedCapabilities: {...},
  transport: "stdio"|"sse"|"http", requestCount: <int>}`.
- Read these from the Context/session and the `SessionStore`. Carry `_meta`.

### T045 — requestCount via session store
- Ensure the per-session `requestCount` increments on each request (the increment may live in
  WP03's request handling or here — coordinate; if WP03 increments globally per request, just
  read it). `requestCount` reflects calls within the same session and is isolated per session.

### T046 — `tests/test_inspect.py`
- Call `inspect_session` twice in one session; assert `requestCount` increases.
- Assert `protocolVersion == "2025-03-26"`, `transport` matches, `clientInfo` populated, and
  `negotiatedCapabilities` reflects the `full` profile.
- `_meta` present.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] `inspect_session` returns all five fields with correct values for the active session.
- [ ] `requestCount` increments across calls and is per-session.
- [ ] `uv run pytest tests/test_inspect.py` passes.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- **verify-on-impl (R9)**: how FastMCP exposes session identity, `clientInfo`,
  `protocolVersion`, and negotiated capabilities. If a field isn't directly available, derive
  it (e.g. transport from the configured run mode) and document the source. Reviewer: confirm
  `requestCount` is session-scoped, not a global counter.
