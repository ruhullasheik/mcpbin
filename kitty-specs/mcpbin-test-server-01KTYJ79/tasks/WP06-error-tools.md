---
work_package_id: WP06
title: Error tools
dependencies:
- WP03
requirement_refs:
- FR-003
- FR-013
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T01:52:52.787110+00:00'
subtasks:
- T029
- T030
- T031
shell_pid: "18576"
agent: "claude:opus:implementer:implementer"
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/tools/errors.py
execution_mode: code_change
owned_files:
- src/mcpbin/tools/errors.py
- tests/test_errors.py
tags: []
---

# WP06 — Error tools

## Objective

Implement the 7 error tools (FR-003) that let a client distinguish JSON-RPC protocol errors
from tool-level errors, including the simulated `error_parse` and a non-standard
`error_unknown_code`.

## Context
- Contract: [../contracts/tools.md](../contracts/tools.md) → "errors";
  [../contracts/protocol.md](../contracts/protocol.md) → "Error codes".
- Uses `errors.py` (codes + `mcp_error` + simulated-parse helper) from WP02. Research R4.
- `register(app, profile, ctx)` contract; conftest from WP03.

## Implement command
```bash
spec-kitty agent action implement WP06 --agent <name>
```

## Subtasks

### T029 — `tools/errors.py` (7 tools)
- `error_invalid_request` → raise `-32600`; `error_method_not_found` → `-32601`;
  `error_invalid_params` → `-32602`; `error_internal` → `-32603` (protocol-level errors via
  `mcp_error`).
- `error_parse` → **simulated**: return a normal tool result whose text content is a
  well-formed JSON-RPC error object with code `-32700`; `_meta.note` explains that real parse
  errors occur before routing so this is a simulation (FR-003 + spec edge case).
- All error tools still emit `_meta` with the raw received input (even though they ignore it).

### T030 — tool-level & unknown-code semantics
- `error_tool_level` → normal result with `isError: true` (NOT a protocol error).
- `error_unknown_code` → a non-standard code **outside** `-32700…-32603` (e.g. `-32000` or a
  positive code) — surfaced consistently (as a protocol error with that code, or simulated like
  `error_parse`; pick one and document). Tests assert the code is out of the standard range.

### T031 — `tests/test_errors.py`
- Each `error_*` surfaces its documented code (protocol error raises; client sees the code).
- `error_tool_level` returns `isError: true`, not a protocol error.
- `error_parse` text contains a `-32700` JSON-RPC object and `_meta.note` mentions simulation.
- `error_unknown_code` is outside `-32700…-32603`.
- Every result (including error results) carries `_meta`.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] All 7 tools behave per contract; protocol vs tool-level distinction is observable.
- [ ] `error_parse` is simulated with the explanatory `_meta.note`.
- [ ] `error_unknown_code` uses a non-standard code.
- [ ] `uv run pytest tests/test_errors.py` passes.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- How a protocol error appears to the in-memory client (exception vs error result) depends on
  FastMCP (R4) — reviewer: confirm the test asserts the actual surfaced shape, and that the
  `_meta` requirement (FR-013) holds even on protocol errors per spec rule.

## Activity Log

- 2026-06-13T01:52:55Z – claude:opus:implementer:implementer – shell_pid=18576 – Assigned agent via action command
