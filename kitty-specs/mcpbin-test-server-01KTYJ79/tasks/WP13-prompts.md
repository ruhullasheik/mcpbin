---
work_package_id: WP13
title: Prompts
dependencies:
- WP03
requirement_refs:
- FR-007
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T06:55:03.733582+00:00'
subtasks:
- T050
- T051
- T052
shell_pid: "5472"
agent: "claude:opus:implementer:implementer"
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/prompts.py
execution_mode: code_change
owned_files:
- src/mcpbin/prompts.py
- tests/test_prompts.py
tags: []
---

# WP13 — Prompts

## Objective

Implement the 5 prompt shapes (FR-007): `simple`, `with_args`, `multi_turn`,
`with_embedded_resource`, and `no_description` (which must have no `description` field in the
listing).

## Context
- Contract: [../contracts/prompts.md](../contracts/prompts.md).
- Registered via `register(app, profile, ctx)`; discovered by the registry's guarded
  `mcpbin.prompts` import (WP02). Skipped under `tools-only`/`minimal` (WP03 gating).
- See research R11 note: only 5 documented shapes — do not pad to hit a count. Catalog-sizing
  decisions belong to WP15.

## Implement command
```bash
spec-kitty agent action implement WP13 --agent <name>
```

## Subtasks

### T050 — `prompts.py` (5 shapes)
- `simple`: no args → one `user` message.
- `with_args`: `topic` (required), `tone` (optional) → message(s) interpolating provided args.
- `multi_turn`: alternating `user`/`assistant` messages (≥2 turns).
- `with_embedded_resource`: a message whose content includes an embedded `resource` block.
- `no_description`: a prompt registered **without** a description (must be absent in
  `prompts/list`, not empty-string).

### T051 — no_description + embedded_resource specifics
- Verify the pinned FastMCP allows registering a prompt with **no** description and that
  `prompts/list` omits the field (vs emitting `""`/null). If FastMCP forces a description,
  document the closest achievable behavior.
- The embedded resource block should reference a plausible resource (e.g. `mcpbin://text/plain`)
  with valid structure.

### T052 — `tests/test_prompts.py`
- `prompts/list` returns all 5; `no_description` has no `description` field.
- `with_args` includes the required + optional argument values in returned messages.
- `multi_turn` alternates user/assistant. `with_embedded_resource` returns a message with an
  embedded resource content block.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] All 5 prompt shapes behave per contract; `no_description` omits the field.
- [ ] `with_args` arguments appear; `multi_turn` alternates; embedded resource present.
- [ ] `uv run pytest tests/test_prompts.py` passes.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- **verify-on-impl**: whether FastMCP can register a prompt with a truly absent description and
  an embedded-resource message. Reviewer: confirm `no_description` is *absent*, not blank.

## Activity Log

- 2026-06-13T06:55:06Z – claude:opus:implementer:implementer – shell_pid=5472 – Assigned agent via action command
- 2026-06-13T06:57:22Z – claude:opus:implementer:implementer – shell_pid=5472 – 5 prompt shapes; no_description absent; embedded resource; 6 tests pass
- 2026-06-13T06:57:28Z – claude:opus:implementer:implementer – shell_pid=5472 – Orchestrator review: 5 shapes; no_description has null description; multi_turn alternates; embedded resource block present; 6 tests pass
