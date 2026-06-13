---
work_package_id: WP05
title: Response-type tools
dependencies:
- WP03
requirement_refs:
- FR-002
- FR-013
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T01:52:44.722160+00:00'
subtasks:
- T025
- T026
- T027
- T028
shell_pid: '2776'
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/tools/response_types.py
execution_mode: code_change
owned_files:
- src/mcpbin/tools/response_types.py
- src/mcpbin/assets/test.png
- tests/test_response_types.py
tags: []
---

# WP05 — Response-type tools

## Objective

Implement the 6 response-type tools (FR-002) covering every MCP content type, plus a committed
deterministic PNG asset for `return_image`. Resolve the `return_empty` + mandatory `_meta`
reconciliation (research R5).

## Context
- Contract: [../contracts/tools.md](../contracts/tools.md) → "response_types".
- Research R5/R10 in [../research.md](../research.md).
- `register(app, profile, ctx)` contract; conftest fixtures from WP03; `_meta` from WP02.

## Implement command
```bash
spec-kitty agent action implement WP05 --agent <name>
```

## Subtasks

### T025 — `tools/response_types.py` (6 tools)
- `return_text` → one text block. `return_image` → image block: base64 of `assets/test.png`,
  `mimeType: "image/png"`. `return_resource` → a resource content block with a valid embedded
  resource object. `return_multiple` → ≥3 mixed blocks (text + image + resource).
  `return_empty` → no substantive content. `return_isError` → `isError: true` + ≥1 text block.
- All carry `_meta`.

### T026 — `assets/test.png`
- Commit a tiny (e.g. 1×1 or small solid) valid PNG. Load bytes at runtime and base64-encode
  (deterministic, NFR-001). Do **not** add an image library (C-003) — ship the bytes.

### T027 — `return_empty` / `_meta` reconciliation
- Follow the WP02 decision: if the MCP result type supports a result-level `_meta` field,
  `return_empty` returns truly zero content blocks + result-level `_meta`. Otherwise the
  `_meta` text block is the sole block (documented as the documentation envelope). Assert the
  chosen behavior in tests and note it in the PR.

### T028 — `tests/test_response_types.py`
- Each tool returns the expected content type(s). `return_image` base64 decodes to bytes
  starting with the PNG signature `\x89PNG`. `return_multiple` has ≥3 distinct types.
  `return_isError` sets `isError: true`. `return_empty` matches the chosen reconciliation.
  Every result has `_meta`.

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane.

## Definition of Done
- [ ] 6 tools registered; image decodes to a valid PNG with `image/png`.
- [ ] `return_empty` behavior matches WP02's `_meta` decision and is tested.
- [ ] `uv run pytest tests/test_response_types.py` passes.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- The `return_empty` vs mandatory-`_meta` tension is the one spec ambiguity here — reviewer:
  confirm the implemented choice is internally consistent and documented.
- Keep the PNG tiny but valid; verify it's committed as binary (not corrupted by text mode).
