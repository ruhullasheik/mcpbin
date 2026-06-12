---
work_package_id: WP10
title: Sampling tools
dependencies:
- WP03
requirement_refs:
- FR-010
- FR-013
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning/base branch devs/ruhulla; completed work merges into devs/ruhulla. Execution worktree is allocated per computed lane from lanes.json.
subtasks:
- T041
- T042
- T043
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/tools/sampling.py
execution_mode: code_change
owned_files:
- src/mcpbin/tools/sampling.py
- tests/test_sampling.py
tags: []
---

# WP10 — Sampling tools

## Objective

Implement the 4 sampling tools (FR-010) that issue `sampling/createMessage` back to the client,
including system prompt and maxTokens variants, and degrade gracefully when the client/profile
lacks the sampling capability.

## Context
- Contract: [../contracts/tools.md](../contracts/tools.md) → "sampling";
  [../contracts/protocol.md](../contracts/protocol.md) → "Sampling".
- Research R8 (Context sampling API + capability detection) — **verify-on-impl**.
- `register(app, profile, ctx)`: under non-sampling profiles the module still registers the
  tools but they degrade gracefully (so `sampling_unsupported` is callable everywhere), OR
  follow the profile — confirm with WP03's gating; default: register but degrade.

## Implement command
```bash
spec-kitty agent action implement WP10 --agent <name>
```

## Subtasks

### T041 — `tools/sampling.py` (simple/system/max_tokens)
- `sampling_simple` → minimal `createMessage` to the client; return the client's response text.
- `sampling_with_system` → include a `systemPrompt`.
- `sampling_max_tokens` → include `maxTokens`.
- Use the Context sampling/create-message method (verify exact API + arg names, R8). `_meta`
  on each (record what was requested).

### T042 — `sampling_unsupported` + degradation
- `sampling_unsupported` → when the client does not advertise sampling, return a graceful
  `isError: true` result explaining sampling is unavailable (not an exception/crash).
- All sampling tools must detect a missing sampling capability and degrade the same way
  (covers `no-sampling`/`tools-only`/`minimal` profiles, FR-011 interaction).

### T043 — `tests/test_sampling.py`
- Build an in-memory client that **advertises sampling** and returns a canned message (verify
  FastMCP's client-side sampling handler). Assert `sampling_simple` returns it; `with_system`
  includes `systemPrompt`; `max_tokens` includes `maxTokens` in the outgoing request.
- With a non-sampling client, assert `sampling_unsupported` returns a graceful error.
- `_meta` present.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] 3 sampling tools issue `createMessage` (system/maxTokens included where specified).
- [ ] `sampling_unsupported` + all sampling tools degrade gracefully without sampling.
- [ ] `uv run pytest tests/test_sampling.py` passes (with a sampling-capable mock client).
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- **verify-on-impl (R8)**: Context sampling method signature and how to register a client-side
  sampling handler in the in-memory test client. Reviewer: confirm the outgoing request
  actually carries `systemPrompt`/`maxTokens` (inspect the captured request, not just the
  response).
