---
work_package_id: WP07
title: Delay tools
dependencies:
- WP03
requirement_refs:
- FR-004
- FR-013
- NFR-002
- NFR-003
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T01:53:00.957517+00:00'
subtasks:
- T032
- T033
- T034
shell_pid: "16312"
agent: "claude:opus:implementer:implementer"
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/tools/delays.py
execution_mode: code_change
owned_files:
- src/mcpbin/tools/delays.py
- tests/test_delays.py
tags: []
---

# WP07 — Delay tools

## Objective

Implement timed tools and cancellation handling (FR-004): `delay` (clamped to 30s), fixed
`delay_1s/5s/30s`, and `delay_cancel` which honors `notifications/cancelled` and returns within
1s with a fixed message (NFR-002, NFR-003).

## Context
- Contract: [../contracts/tools.md](../contracts/tools.md) → "delays".
- Research R6 (cancellation signal API) — **verify-on-impl** against pinned FastMCP.
- Async tools (`pytest-asyncio` from WP01). `register(app, profile, ctx)` contract; conftest WP03.

## Implement command
```bash
spec-kitty agent action implement WP07 --agent <name>
```

## Subtasks

### T032 — `tools/delays.py` (delay + fixed)
- `delay` `{seconds: number}` → `await asyncio.sleep(min(seconds, 30))` then a text result;
  clamp at 30 (FR-004). `delay_1s`/`delay_5s`/`delay_30s` → fixed sleeps.
- All carry `_meta` (include the effective delay in `note`/`received`).

### T033 — `delay_cancel`
- Wait up to 60s while observing the request's cancellation signal (R6 — Context cancel scope /
  `asyncio.CancelledError` / cancel token; verify the real API).
- On `notifications/cancelled` before completion: return within 1s (NFR-003) with
  `isError: true`, message exactly `"cancelled by client"`, and `_meta` reporting `cancelled`.
- On 60s timeout with no cancellation: normal text result, `_meta` reporting `completed`.

### T034 — `tests/test_delays.py`
- `delay {seconds:2}` completes in ~2s (assert within a tolerant window; NFR-002 is 2±0.5 but
  keep CI-tolerant). `delay {seconds:99}` clamps to ≤30 (don't actually wait 30 in CI — assert
  the clamp logic or use a short patched value).
- `delay_cancel`: start the call, send a cancellation, assert `isError`, `"cancelled by
  client"`, and that it returned promptly. Verify how to inject cancellation via the in-memory
  client (R6); if not feasible in-memory, unit-test the cancellation branch directly.
- `_meta` present on all.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] `delay` clamps to 30s; fixed delays behave.
- [ ] `delay_cancel` returns `isError`+`"cancelled by client"` <1s after cancellation, else a
      normal result; `_meta` always reports cancelled vs completed.
- [ ] `uv run pytest tests/test_delays.py` passes without multi-30s CI waits.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- **Cancellation API is verify-on-impl (R6)** — if FastMCP doesn't surface a per-request cancel
  signal, fall back to a cooperative polling flag and document it.
- Keep tests fast: don't sleep 30s/60s in CI; assert clamp/branch logic with small values or
  patched constants. Reviewer: confirm no test blocks CI for tens of seconds.

## Activity Log

- 2026-06-13T01:53:03Z – claude:opus:implementer:implementer – shell_pid=16312 – Assigned agent via action command
- 2026-06-13T06:43:32Z – claude:opus:implementer:implementer – shell_pid=16312 – 10 tests pass; foundation fix merged; cancel test rewritten for event loop
