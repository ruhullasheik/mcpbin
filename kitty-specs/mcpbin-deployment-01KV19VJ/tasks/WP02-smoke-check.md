---
work_package_id: WP02
title: Live smoke check
dependencies: []
requirement_refs:
- FR-007
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-deployment-01KV19VJ
base_commit: 17c0b491a6d6dbd0b14d46a10b1cd14f5f52e252
created_at: '2026-06-13T20:24:30.652073+00:00'
subtasks:
- T004
- T005
- T006
shell_pid: '16836'
history:
- date: '2026-06-13'
  author: tasks
  action: created
authoritative_surface: scripts/smoke_check.py
execution_mode: code_change
owned_files:
- scripts/smoke_check.py
tags: []
---

# WP02 — Live smoke check

## Objective

Provide a dependency-light script that verifies a live mcpbin base URL: the UI loads and the
`/mcp` endpoint accepts an MCP `initialize`. It tolerates free-tier cold starts and is usable
both locally and against the deployed Space.

## Context
- Contract: [../contracts/smoke-check.md](../contracts/smoke-check.md). Research R5 in
  [../research.md](../research.md). Deployment surface: [../contracts/deployment-surface.md](../contracts/deployment-surface.md).
- **Stdlib only** (`urllib`, `json`, `argparse`, `time`) — no third-party deps, so it runs in
  any Python 3.12 env without installs.

## Implement command
```bash
spec-kitty agent action implement WP02 --agent <name>
```

## Scope — ONLY this owned file
- `scripts/smoke_check.py`

## Subtasks

### T004 — CLI scaffold
- `argparse`: positional `base_url` (e.g. `https://owner-mcpbin.hf.space` or
  `http://localhost:8000`); `--timeout` seconds (default 30) as the cold-start retry budget;
  `--interval` (default 2).
- Normalize `base_url` (strip trailing `/`). Print a clear PASS/FAIL line per check; exit `0`
  only if all checks pass, non-zero otherwise.

### T005 — The two checks + cold-start retries
- **Check 1 — UI:** `GET <base>/` → expect HTTP 200 and body contains an app-shell marker
  (`id="search"` or `mcpbin`). 
- **Check 2 — MCP:** `POST <base>/mcp` with headers `Content-Type: application/json` and
  `Accept: application/json, text/event-stream`, body a JSON-RPC `initialize`:
  ```json
  {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}
  ```
  Pass if the HTTP status is 200 and the response parses as JSON-RPC (or SSE `data:` carrying
  JSON) — i.e. a real MCP reply, **not** 404/405. (A JSON-RPC `error` body still proves the
  endpoint is live; only transport-level 404/405/connection failure is a fail.)
- **Cold start (NFR-004):** wrap both checks in a retry loop with `--interval` backoff until
  they pass or `--timeout` elapses; treat connection errors / 5xx / 503 as "still waking".

### T006 — Local verification
- Document at the top of the file (and verify) the local run:
  `uv run mcpbin --transport http` in one shell, then
  `python scripts/smoke_check.py http://localhost:8000` → both checks PASS, exit 0.
- Confirm a dead URL (e.g. an unused port) exits non-zero within the timeout.

## Branch Strategy
Planning/base **main**; merge target **main**; worktree per lane from `lanes.json`.

## Definition of Done
- [ ] `python scripts/smoke_check.py http://localhost:8000` passes against a running server (exit 0).
- [ ] A dead URL exits non-zero after retrying up to the timeout.
- [ ] Stdlib-only; no third-party imports.
- [ ] Clear per-check PASS/FAIL output; usable in CI or by hand.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- SSE vs JSON: the `/mcp` response may be `text/event-stream`; parse `data:` lines if so.
  Reviewer: confirm both content types are handled and that a JSON-RPC error still counts as
  "endpoint live".
- Keep retries bounded; don't hang. Reviewer: run it against localhost (pass) and a closed
  port (fail) to confirm both paths.
