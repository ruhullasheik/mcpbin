---
work_package_id: WP04
title: Echo tools
dependencies:
- WP03
requirement_refs:
- FR-001
- FR-013
- FR-016
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T01:52:36.707215+00:00'
subtasks:
- T022
- T023
- T024
shell_pid: '1752'
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/tools/echo.py
execution_mode: code_change
owned_files:
- src/mcpbin/tools/echo.py
- tests/test_echo.py
tags: []
---

# WP04 — Echo tools

## Objective

Implement the 7 echo tools (FR-001) that return their inputs unchanged, each ending with a
valid `_meta` block (FR-013). This is the canonical example of a feature module using the
`register(app, profile, ctx)` contract.

## Context

- Contract: [../contracts/tools.md](../contracts/tools.md) → "echo".
- Uses `_meta.build_meta`/`append_meta` from WP02 and the conftest fixtures from WP03.
- Module contract: expose `register(app, profile, ctx)`; the registry auto-discovers it.

## Implement command
```bash
spec-kitty agent action implement WP04 --agent <name>
```

## Subtasks

### T022 — `tools/echo.py` (7 tools)
- `register(app, profile, ctx)` registers all 7 via FastMCP's tool decorator/registration:
  `echo`, `echo_string`, `echo_number`, `echo_boolean`, `echo_object`, `echo_array`,
  `echo_all_types`.
- Each returns its input unchanged as JSON text content, then appends `_meta` via
  `build_meta(tool=<name>, received=<raw args>, note=<one sentence>)`.
- Every tool has a clear `description` (FR-016).

### T023 — Input schemas
- `echo`: free-form object (accept arbitrary args). `echo_string`: `{value: string}` required;
  similarly number/boolean/object/array. `echo_all_types`:
  `{string, number, boolean, object, array}`.
- Echo back exactly what was received (preserve types).

### T024 — `tests/test_echo.py`
- Using `client_full`, call each tool and assert the value round-trips unchanged.
- Assert `_meta.tool` equals the tool name and `_meta.received` equals the sent arguments.
- `echo_all_types` returns all five values.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] 7 echo tools registered and return inputs unchanged.
- [ ] Every result carries a schema-valid `_meta` (tool + received correct).
- [ ] `uv run pytest tests/test_echo.py` passes.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- Confirm `received` reflects the **raw parsed** args (the `_meta` contract). Reviewer: verify
  no type coercion sneaks in (a number stays a number, not a string).
