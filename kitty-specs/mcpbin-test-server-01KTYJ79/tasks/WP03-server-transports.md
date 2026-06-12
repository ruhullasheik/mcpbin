---
work_package_id: WP03
title: Server, transports, profile gating, pagination wiring
dependencies:
- WP02
requirement_refs:
- FR-008
- FR-011
- FR-014
- FR-015
- FR-016
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning/base branch devs/ruhulla; completed work merges into devs/ruhulla. Execution worktree is allocated per computed lane from lanes.json.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
- T021
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/server.py
execution_mode: code_change
owned_files:
- src/mcpbin/server.py
- tests/conftest.py
- tests/test_server.py
tags: []
---

# WP03 — Server, transports, profile gating, pagination wiring

## Objective

Create the FastMCP application and CLI that tie everything together: select a transport,
apply a capability profile (advertise + gate omitted capabilities with `-32601`), wire
opaque-cursor pagination into the list methods, serve the static frontend at `/` and MCP at
`/mcp` for HTTP transports, and provide shared pytest fixtures for all feature WPs.

## Context

- Plan: [../plan.md](../plan.md). Contracts: [../contracts/protocol.md](../contracts/protocol.md).
- Research: R1 (transport), R2 (profile gating), R3 (pagination wiring) — **verify-on-impl**.
- Depends on WP02 primitives: `registry.register_all`, `profiles`, `pagination`, `session`,
  `errors`. **Does not** reference any feature module directly (auto-discovery handles that).

## Implement command

```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Subtasks

### T014 — `server.py`: build app + register
- `build_app(profile_name: str, transport: str) -> FastMCP`: create the `FastMCP` instance,
  resolve the `Profile` (WP02), create the `SessionStore`, and call
  `registry.register_all(app, profile, ctx)`.
- Advertise capabilities at `initialize` to match the profile (tools/resources/prompts/
  sampling/pagination/listChanged) — verify how the pinned FastMCP lets you set advertised
  capabilities (R2).

### T015 — CLI + `main()`
- `main(argv=None)`: parse `--transport {stdio,sse,http}` (default `stdio`) and
  `--profile {full,tools-only,no-sampling,minimal}` (default `full`). Keep it dependency-free
  (argparse) to honor C-003.
- Structured logging to **stderr** (FR-016) — log selected transport/profile and per-request
  info at a sensible level.

### T016 — Transport run wiring
- Map `--transport` to FastMCP's run call: stdio, SSE, and Streamable HTTP (FR-014). Verify the
  exact transport keyword strings against the pinned FastMCP (R1). One entry point, one flag.

### T017 — Static frontend + `/mcp`
- For HTTP transports, serve `frontend/` as static files at `/` and mount the MCP server at
  `/mcp` (Streamable HTTP). Resolve the `frontend/` path from package data / a known path
  (coordinate with WP01's packaging decision). stdio transport skips the web surface.

### T018 — Capability gating → `-32601`
- When the active profile omits a capability, its list method (`resources/list`,
  `prompts/list`, etc.) must return JSON-RPC **`-32601`** (method not found) — **not** an empty
  list (FR-011). `minimal` additionally must not advertise `listChanged`.
- Implement by not registering those features (registry already skips them) **and** ensuring
  the omitted list method raises `-32601` rather than returning empty. If FastMCP auto-serves
  an empty list, override/disable that handler (R2 fallback).

### T019 — Pagination wiring
- Wrap/override the `tools/list`, `resources/list`, `prompts/list` handlers to page the
  registered catalog via `pagination.paginate` (page size 10): opaque `nextCursor`, **absent**
  on the final page; invalid cursor → `-32602` `"invalid or expired cursor"` (FR-008).
- The mechanism is catalog-agnostic — it paginates whatever is registered, so it needs no
  feature-module imports.

### T020 — `tests/conftest.py` (shared fixtures)
- Fixtures that build an in-memory FastMCP client against `build_app(profile, "stdio")` for a
  given profile (default `full`). Verify FastMCP's in-memory client API.
- Expose fixtures like `client_full`, `client_tools_only`, `client_no_sampling`,
  `client_minimal`, plus a parametrizable factory. Feature WP tests consume these — they must
  not modify this file.

### T021 — `tests/test_server.py`
- `main(["--help"])` / arg parsing works; defaults are stdio + full.
- `full` profile advertises tools/resources/prompts/sampling.
- `tools-only`: `resources/list` and `prompts/list` → `-32601`.
- `minimal`: no `listChanged` advertised.
- Pagination smoke: a list method returns ≤10 items + an opaque `nextCursor` when the catalog
  exceeds a page; a bad cursor → `-32602`.

## Branch Strategy

Planning/base **devs/ruhulla**; merge target **devs/ruhulla**. Worktree per lane from
`lanes.json`.

## Definition of Done

- [ ] `uv run mcpbin --help` lists `--transport` and `--profile`.
- [ ] `uv run mcpbin` starts over stdio (full profile) without error.
- [ ] HTTP transport serves `/` (frontend) and `/mcp`.
- [ ] Omitted-capability list methods return `-32601` for `tools-only`/`minimal`; `minimal`
      omits `listChanged`.
- [ ] Pagination: page size 10, opaque cursor, absent final `nextCursor`, `-32602` on bad cursor.
- [ ] `tests/conftest.py` fixtures usable by feature WPs; `uv run pytest tests/test_server.py`
      passes.
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance

- **Highest-risk WP** for FastMCP API assumptions (R1/R2/R3). If FastMCP's high-level API
  cannot (a) set advertised capabilities, (b) override list handlers for `-32601`, or
  (c) inject pagination, drop to the low-level MCP server/handler layer FastMCP wraps. Document
  whichever path you took in the PR — later WPs and WP15 depend on the contract being stable.
- Keep `server.py` free of feature-module imports to preserve ownership isolation.
- Reviewer: confirm the in-memory client fixtures actually exercise the registered catalog so
  downstream feature tests are meaningful.
