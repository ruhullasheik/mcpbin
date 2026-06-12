---
work_package_id: WP08
title: Schema validation tools
dependencies:
- WP03
requirement_refs:
- FR-005
- FR-013
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/tools/schema.py
execution_mode: code_change
owned_files:
- src/mcpbin/tools/schema.py
- tests/test_schema.py
tags: []
---

# WP08 — Schema validation tools

## Objective

Implement the 6 schema tools (FR-005) with strict input schemas so clients can validate they
read and enforce JSON Schema: required, optional, enum, nested, typed array, and no-args.

## Context
- Contract: [../contracts/tools.md](../contracts/tools.md) → "schema".
- `register(app, profile, ctx)` contract; `_meta` from WP02; conftest from WP03.
- Schemas are derived from type hints / explicit schema per the pinned FastMCP's mechanism.

## Implement command
```bash
spec-kitty agent action implement WP08 --agent <name>
```

## Subtasks

### T035 — `tools/schema.py` (6 tools)
- `schema_required_fields`: ≥1 required field; missing → validation error.
- `schema_optional_fields`: all optional; omitting them succeeds.
- `schema_enum`: a field restricted to an enum (e.g. `color ∈ {red,green,blue}`); off-enum →
  error.
- `schema_nested`: a deeply nested object; accepts + returns it.
- `schema_array_items`: a typed array (e.g. `list[int]`); accepts + returns it.
- `schema_no_args`: no `inputSchema`; succeeds with no args.
- All carry `_meta`.

### T036 — validation behavior + `_meta`
- Ensure the declared schemas actually appear in `tools/list` (so a client UI can read them).
- Confirm how the pinned FastMCP reports input validation errors to the client and align tests.

### T037 — `tests/test_schema.py`
- Missing required field → error; omitting optionals → success; off-enum value → error;
  nested + array round-trip; no-args succeeds with no input. `_meta` present.
- Assert each tool's `inputSchema` is exposed in `tools/list` with the expected constraints.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] 6 tools with the documented schema shapes; validation behaves per contract.
- [ ] Schemas are visible in `tools/list`.
- [ ] `uv run pytest tests/test_schema.py` passes.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- Whether validation errors surface as `-32602` vs a tool error depends on FastMCP — reviewer:
  confirm tests assert the actual surfaced behavior rather than an assumed one.
