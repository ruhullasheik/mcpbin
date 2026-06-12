---
work_package_id: WP02
title: Core protocol primitives
dependencies:
- WP01
requirement_refs:
- FR-008
- FR-011
- FR-012
- FR-013
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-12T19:36:39.085275+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
shell_pid: "11120"
agent: "claude:opus:reviewer:reviewer"
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: src/mcpbin/registry.py
execution_mode: code_change
owned_files:
- src/mcpbin/_meta.py
- src/mcpbin/errors.py
- src/mcpbin/pagination.py
- src/mcpbin/profiles.py
- src/mcpbin/session.py
- src/mcpbin/registry.py
- src/mcpbin/tools/__init__.py
- tests/test_core.py
tags: []
---

# WP02 — Core protocol primitives

## Objective

Build the cross-cutting modules every feature area depends on: the `_meta` envelope helper,
JSON-RPC error helpers, the opaque cursor pagination codec, the four capability profiles, the
per-session store, and the **auto-discovery registry** that lets feature modules register
without touching shared files.

## Context

- Plan: [../plan.md](../plan.md). Data model: [../data-model.md](../data-model.md).
- Contracts: [../contracts/protocol.md](../contracts/protocol.md),
  [../contracts/meta-schema.json](../contracts/meta-schema.json).
- Research decisions: R2 (profiles), R3 (pagination), R4 (errors), R5 (`_meta`), R9 (session)
  in [../research.md](../research.md). Several are **verify-on-impl** against the FastMCP
  version pinned in WP01 — confirm the exact API as you go.
- **Registry contract** (the linchpin): every feature module exposes
  `register(app, profile, ctx) -> None`. `registry.register_all` discovers them.

## Implement command

```bash
spec-kitty agent action implement WP02 --agent <name>
```

## Subtasks

### T007 — `_meta.py`
- `build_meta(tool: str, received: dict, note: str) -> dict` → `{"tool","received","note"}`
  exactly matching `contracts/meta-schema.json` (FR-013).
- `append_meta(content: list, meta: dict) -> list` → returns content with the `_meta` object
  serialized as the **final text content block** (JSON-encoded text), per PRD `_meta` rules.
- Decide and document the representation: a trailing text block whose text is
  `json.dumps({"_meta": {...}})`. If the pinned FastMCP/MCP result type exposes a native
  result-level `_meta` field, prefer it and note the choice (affects `return_empty`, WP05).
- `received` must reflect raw parsed input even when ignored.

### T008 — `errors.py`
- Constants for standard codes: `PARSE_ERROR=-32700`, `INVALID_REQUEST=-32600`,
  `METHOD_NOT_FOUND=-32601`, `INVALID_PARAMS=-32602`, `INTERNAL_ERROR=-32603`.
- `mcp_error(code, message, data=None)` helper that raises the FastMCP/MCP error type carrying
  a JSON-RPC `code` (verify the exact exception class, e.g. `McpError`/`ToolError` with code).
- `INVALID_CURSOR_MESSAGE = "invalid or expired cursor"` constant (shared with pagination).
- A helper to build a *simulated* JSON-RPC error object (plain dict) for `error_parse` (WP06).

### T009 — `pagination.py`
- `encode_cursor(offset: int) -> str`: opaque base64 of an internal token (e.g.
  `base64.urlsafe_b64encode(f"offset:{offset}".encode())`). Must be opaque — clients never
  parse it (FR-008).
- `decode_cursor(cursor: str | None) -> int`: `None` → 0; malformed/garbage/out-of-range →
  raise `mcp_error(INVALID_PARAMS, "invalid or expired cursor")`.
- `paginate(items: list, cursor: str | None, page_size: int = 10) -> tuple[list, str | None]`:
  returns `(page_items, next_cursor)` where `next_cursor` is `None` on the final page so the
  caller can **omit** `nextCursor` entirely (not null/empty).
- `PAGE_SIZE = 10`.

### T010 — `profiles.py`
- Enum/constants for `full`, `tools-only`, `no-sampling`, `minimal`.
- A `Profile` dataclass/structure capturing which capabilities are advertised: `tools`,
  `resources`, `prompts`, `sampling`, `pagination`, `list_changed` — per the matrix in
  `data-model.md`.
- `get_profile(name) -> Profile`; `PROFILES` mapping; default `full`.
- Helper predicates: `profile.has(capability) -> bool` used by feature modules' `register`
  (e.g. sampling module registers nothing when `not profile.sampling`).
- Note: turning omitted list methods into `-32601` happens in WP03 (server) using these flags.

### T011 — `session.py`
- A `SessionState` holding `protocol_version`, `client_info`, `negotiated_capabilities`,
  `transport`, `request_count` (FR-012).
- A `SessionStore` keyed by FastMCP session identity (verify how the pinned FastMCP exposes a
  per-connection id/context). Methods: `get_or_create(session_id)`, `increment(session_id)`.
- `request_count` increments per request; excluded from determinism checks (NFR-001).
- Keep it transport-agnostic; WP03 sets `transport` and WP11 reads the state.

### T012 — `registry.py` + `tools/__init__.py`
- `tools/__init__.py`: empty package marker (enables `pkgutil` discovery).
- `registry.register_all(app, profile, ctx) -> None`:
  - Walk `mcpbin.tools` submodules via `pkgutil.iter_modules(tools.__path__)`, import each,
    and call its `register(app, profile, ctx)`.
  - Then import `mcpbin.resources` and `mcpbin.prompts` **guarded** with
    `try/except ImportError` (they may not exist yet during WP02/03; log a warning). Call their
    `register(app, profile, ctx)` when present.
  - Respect `profile`: modules self-skip via `profile.has(...)`, but resources/prompts should
    also be skipped here when the profile omits them.
- Document the `register(app, profile, ctx)` signature as the contract for all feature WPs.

### T013 — `tests/test_core.py`
- Cursor codec: round-trips offsets; `decode_cursor(None)==0`; garbage raises `-32602` with
  the exact message; `paginate` yields page_size 10 and `None` next on final page.
- Profiles: matrix correctness for all four profiles.
- `_meta`: `build_meta` matches the JSON Schema (load `contracts/meta-schema.json` and
  validate, or assert keys/types).
- Session: `increment` raises count; distinct sessions isolated.

## Branch Strategy

Planning/base branch **devs/ruhulla**; merge target **devs/ruhulla**. Worktree per lane from
`lanes.json`.

## Definition of Done

- [ ] All six modules importable; `tools/__init__.py` present.
- [ ] `uv run pytest tests/test_core.py` passes.
- [ ] Cursor invalid → `-32602` `"invalid or expired cursor"`; final page → no next cursor.
- [ ] `_meta` helper output validates against `contracts/meta-schema.json`.
- [ ] `register_all` discovers tool modules and guards resources/prompts imports.
- [ ] FastMCP error/exception types used for coded errors are confirmed against the pinned
      version (note any deviation from research R4/R8 in the PR description).
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance

- **verify-on-impl**: the exact FastMCP exception type for raising a coded JSON-RPC error
  (R4), and how to key a session (R9). If FastMCP doesn't expose what's needed, document the
  fallback (e.g. low-level handler) so WP03 can rely on it.
- Keep `pagination.py` independent of FastMCP — pure functions, easy to unit-test.
- The guarded resources/prompts import is intentional; reviewer should confirm it logs rather
  than crashes when those modules are absent.

## Activity Log

- 2026-06-12T19:36:41Z – claude:opus:implementer:implementer – shell_pid=10812 – Assigned agent via action command
- 2026-06-12T19:47:35Z – claude:opus:implementer:implementer – shell_pid=10812 – Ready for review: core primitives (_meta, errors, pagination, profiles, session, registry); 36 tests pass
- 2026-06-12T19:48:59Z – claude:opus:reviewer:reviewer – shell_pid=11120 – Started review via action command
