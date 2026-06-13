---
work_package_id: WP09
title: Notification tools
dependencies:
- WP03
requirement_refs:
- FR-009
- FR-013
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T06:57:45.220444+00:00'
subtasks:
- T038
- T039
- T040
shell_pid: "2820"
agent: "claude:opus:implementer:implementer"
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/tools/notifications.py
execution_mode: code_change
owned_files:
- src/mcpbin/tools/notifications.py
- tests/test_notifications.py
tags: []
---

# WP09 — Notification tools

## Objective

Implement the 6 notification tools (FR-009) that emit server→client notifications so clients
can validate push handling: resource/prompt/tool list-changed, resource-updated, a progress
sequence, and multi-level logging.

## Context
- Contract: [../contracts/tools.md](../contracts/tools.md) → "notifications";
  [../contracts/protocol.md](../contracts/protocol.md) → "Notifications".
- Research R7 (Context notification/progress/log API) — **verify-on-impl**.
- `register(app, profile, ctx)` contract; conftest from WP03.

## Implement command
```bash
spec-kitty agent action implement WP09 --agent <name>
```

## Subtasks

### T038 — `tools/notifications.py` (list/update notifies)
- `notify_resource_updated` → `notifications/resources/updated`.
- `notify_resource_list_changed` → `notifications/resources/list_changed`.
- `notify_prompt_list_changed` → `notifications/prompts/list_changed`.
- `notify_tool_list_changed` → `notifications/tools/list_changed`.
- Use the request Context to send these (verify exact API, R7). Each returns a small result
  with `_meta`.

### T039 — progress + log
- `notify_progress` → send ≥3 `notifications/progress` (with progress/total) then a result.
- `notify_log` → send `notifications/message` at debug, info, warning, error (≥1 each), then a
  result.

### T040 — `tests/test_notifications.py`
- Attach a notification/message/progress handler on the in-memory client (verify FastMCP's
  client-side hook) and assert the corresponding notifications arrive; `notify_progress` ≥3;
  `notify_log` hits all four levels. `_meta` present on each tool result.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] Each `notify_*` emits the documented notification.
- [ ] `notify_progress` sends ≥3 progress messages; `notify_log` covers all four levels.
- [ ] `uv run pytest tests/test_notifications.py` passes.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- **verify-on-impl (R7)**: exact Context method names for progress/log/notifications and the
  client-side handler API. If the in-memory client can't capture a given notification, assert
  what is observable and document the gap.

## Activity Log

- 2026-06-13T06:57:48Z – claude:opus:implementer:implementer – shell_pid=2820 – Assigned agent via action command
- 2026-06-13T07:00:03Z – claude:opus:implementer:implementer – shell_pid=2820 – 6 notify tools; progress>=3, all log levels; 3 tests pass
- 2026-06-13T07:00:09Z – claude:opus:implementer:implementer – shell_pid=2820 – Orchestrator review: 4 list/update notifications captured via message_handler, >=3 progress via progress_handler, debug/info/warning/error via log_handler; 3 tests pass
