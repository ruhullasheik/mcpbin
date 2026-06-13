# Tasks: mcpbin — Diagnostic MCP Test Server

**Mission**: mcpbin-test-server-01KTYJ79 · **Branch**: `devs/ruhulla` · **Date**: 2026-06-12
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

## Architecture decision driving the breakdown

To keep work-package file ownership **non-overlapping** (a hard finalize-tasks rule), the
server uses an **auto-discovery registry**: `registry.py` walks the `mcpbin.tools` package
and imports `mcpbin.resources` / `mcpbin.prompts` (guarded), calling each module's
`register(app, profile, ctx)`. Consequently:

- `server.py` and `registry.py` never reference individual feature modules → no shared-file
  edits when a feature area is added.
- Each feature area is one module + one test file, independently implementable and
  parallelizable after the foundation lands.
- Shared test fixtures live in `tests/conftest.py` (owned by WP03); feature test files
  *use* the fixtures but never modify them.

## Dependency & lane overview

```
WP01 scaffolding
  └─ WP02 core primitives
       └─ WP03 server / transports / profile-gating / pagination wiring / conftest
            ├─ WP04 echo
            ├─ WP05 response types
            ├─ WP06 errors
            ├─ WP07 delays            (parallel lane group — all depend only on WP03)
            ├─ WP08 schema
            ├─ WP09 notifications
            ├─ WP10 sampling
            ├─ WP11 inspect
            ├─ WP12 resources
            ├─ WP13 prompts
            └─ WP14 frontend
                 └─ WP15 integration, pagination/profile validation, README test checklist
```

MVP = WP01 → WP02 → WP03 + WP04 (one working echo tool over stdio proves the spine).

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | `pyproject.toml` (deps, dev-deps, entry point, package data) | WP01 | | [D] |
| T002 | `.python-version` pin 3.12.x | WP01 | [D] |
| T003 | `src/mcpbin/__init__.py` with `__version__` | WP01 | [D] |
| T004 | `Dockerfile` + `.dockerignore` (uv, build-ready) | WP01 | [D] |
| T005 | Generate `uv.lock` via `uv lock` | WP01 | | [D] |
| T006 | Import smoke check | WP01 | | [D] |
| T007 | `_meta.py` — `build_meta` / `append_meta` | WP02 | [D] |
| T008 | `errors.py` — JSON-RPC codes + coded-error helper | WP02 | [D] |
| T009 | `pagination.py` — opaque cursor codec, page slice, `-32602` | WP02 | [D] |
| T010 | `profiles.py` — 4 profiles + capability matrix + gating helpers | WP02 | [D] |
| T011 | `session.py` — per-session store (requestCount, caps, transport) | WP02 | [D] |
| T012 | `registry.py` + `tools/__init__.py` — auto-discovery `register_all` | WP02 | | [D] |
| T013 | `tests/test_core.py` — codec/profiles/meta/session units | WP02 | | [D] |
| T014 | `server.py` — build FastMCP app, register via registry+profile | WP03 | | [D] |
| T015 | CLI: `--transport {stdio,sse,http}`, `--profile {...}`, `main()` | WP03 | | [D] |
| T016 | Transport run wiring (`app.run` per transport) | WP03 | | [D] |
| T017 | Serve static `frontend/` at `/`, MCP at `/mcp` (HTTP transports) | WP03 | | [D] |
| T018 | Capability gating: omitted caps' list methods → `-32601`; `minimal` no `listChanged` | WP03 | | [D] |
| T019 | Pagination wiring into list handlers (page 10, opaque cursor, absent final `nextCursor`) | WP03 | | [D] |
| T020 | `tests/conftest.py` — in-memory client fixtures per profile | WP03 | | [D] |
| T021 | `tests/test_server.py` — transport/profile/pagination smoke | WP03 | | [D] |
| T022 | `tools/echo.py` — 7 echo tools + `_meta` | WP04 | |
| T023 | Echo input schemas (string/number/boolean/object/array/all_types) | WP04 | |
| T024 | `tests/test_echo.py` — round-trip + `_meta` assertions | WP04 | |
| T025 | `tools/response_types.py` — 6 content-type tools | WP05 | |
| T026 | `assets/test.png` — committed tiny deterministic PNG | WP05 | |
| T027 | `return_empty` / `_meta` reconciliation (research R5) | WP05 | |
| T028 | `tests/test_response_types.py` | WP05 | |
| T029 | `tools/errors.py` — 7 error tools (codes + simulated parse) | WP06 | |
| T030 | `error_tool_level` / `error_unknown_code` semantics | WP06 | |
| T031 | `tests/test_errors.py` | WP06 | |
| T032 | `tools/delays.py` — `delay` (clamp 30), fixed 1/5/30s | WP07 | |
| T033 | `delay_cancel` — cancellation observation, `<1s`, fixed message | WP07 | |
| T034 | `tests/test_delays.py` — timing + cancellation | WP07 | |
| T035 | `tools/schema.py` — required/optional/enum/nested/array/no-args | WP08 | |
| T036 | Schema validation behavior + `_meta` | WP08 | |
| T037 | `tests/test_schema.py` | WP08 | |
| T038 | `tools/notifications.py` — 4 list/update notifies | WP09 | |
| T039 | `notify_progress` (≥3) + `notify_log` (all levels) | WP09 | |
| T040 | `tests/test_notifications.py` | WP09 | |
| T041 | `tools/sampling.py` — simple/system/max_tokens | WP10 | |
| T042 | `sampling_unsupported` + graceful degradation | WP10 | |
| T043 | `tests/test_sampling.py` (with sampling-capable mock client) | WP10 | |
| T044 | `tools/inspect.py` — `inspect_session` | WP11 | |
| T045 | requestCount increment via session store | WP11 | |
| T046 | `tests/test_inspect.py` | WP11 | |
| T047 | `resources.py` — text/markdown/blob + large paginated family (≥100) | WP12 | |
| T048 | `mcpbin://dynamic/{id}` template + `mcpbin://missing` not-found | WP12 | |
| T049 | `tests/test_resources.py` | WP12 | |
| T050 | `prompts.py` — 5 prompt shapes | WP13 | |
| T051 | `no_description` + `with_embedded_resource` specifics | WP13 | |
| T052 | `tests/test_prompts.py` | WP13 | |
| T053 | `frontend/index.html` — navbar + sidebar + detail panel | WP14 | |
| T054 | `frontend/app.js` — fetch `/mcp`, follow cursors, group by area, error state | WP14 | |
| T055 | `frontend/style.css` — no external deps, offline | WP14 | |
| T056 | `tests/test_meta_contract.py` — every tool result has valid `_meta` | WP15 | |
| T057 | `tests/test_pagination.py` — multipage + invalid cursor across all lists | WP15 | |
| T058 | `tests/test_profiles.py` — all 4 profiles' capability gating | WP15 | |
| T059 | `tests/test_integration.py` — catalog sizing + cross-area smoke | WP15 | |
| T060 | `README.md` — test checklist (FR-017) + run/Docker docs | WP15 | |

---

## Work Packages

### WP01 — Project scaffolding & packaging
**Goal**: A `uv`-managed Python 3.12 package that imports cleanly and is Docker-build-ready.
**Priority**: P0 (blocks everything). **Independent test**: `uv run python -c "import mcpbin"`.
**Depends on**: none. **Prompt**: [tasks/WP01-scaffolding.md](tasks/WP01-scaffolding.md) (~200 lines)

- [x] T001 `pyproject.toml` (WP01)
- [x] T002 `.python-version` (WP01)
- [x] T003 `src/mcpbin/__init__.py` (WP01)
- [x] T004 `Dockerfile` + `.dockerignore` (WP01)
- [x] T005 generate `uv.lock` (WP01)
- [x] T006 import smoke check (WP01)

### WP02 — Core protocol primitives
**Goal**: Cross-cutting modules every feature depends on: `_meta`, errors, pagination, profiles,
session, and the auto-discovery registry.
**Priority**: P0. **Independent test**: `uv run pytest tests/test_core.py`.
**Depends on**: WP01. **Prompt**: [tasks/WP02-core-primitives.md](tasks/WP02-core-primitives.md) (~350 lines)

- [x] T007 `_meta.py` (WP02)
- [x] T008 `errors.py` (WP02)
- [x] T009 `pagination.py` (WP02)
- [x] T010 `profiles.py` (WP02)
- [x] T011 `session.py` (WP02)
- [x] T012 `registry.py` + `tools/__init__.py` (WP02)
- [x] T013 `tests/test_core.py` (WP02)

### WP03 — Server, transports, profile gating, pagination wiring
**Goal**: The FastMCP app + CLI that ties everything together: transports, profile-based
capability advertisement/gating, and pagination of list methods. Provides shared test fixtures.
**Priority**: P0. **Independent test**: `uv run pytest tests/test_server.py`; `uv run mcpbin --help`.
**Depends on**: WP02. **Prompt**: [tasks/WP03-server-transports.md](tasks/WP03-server-transports.md) (~450 lines)

- [x] T014 `server.py` app + registry/profile registration (WP03)
- [x] T015 CLI flags + `main()` (WP03)
- [x] T016 transport run wiring (WP03)
- [x] T017 static `/` + `/mcp` mounting (WP03)
- [x] T018 capability gating → `-32601` (WP03)
- [x] T019 pagination wiring (WP03)
- [x] T020 `tests/conftest.py` fixtures (WP03)
- [x] T021 `tests/test_server.py` (WP03)

### WP04 — Echo tools
**Goal**: 7 echo tools returning inputs unchanged, each with `_meta`.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_echo.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP04-echo-tools.md](tasks/WP04-echo-tools.md) (~220 lines)

- [ ] T022 `tools/echo.py` 7 tools (WP04)
- [ ] T023 echo input schemas (WP04)
- [ ] T024 `tests/test_echo.py` (WP04)

### WP05 — Response-type tools
**Goal**: 6 tools covering every MCP content type + committed PNG asset.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_response_types.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP05-response-types.md](tasks/WP05-response-types.md) (~250 lines)

- [ ] T025 `tools/response_types.py` (WP05)
- [ ] T026 `assets/test.png` (WP05)
- [ ] T027 `return_empty` / `_meta` reconciliation (WP05)
- [ ] T028 `tests/test_response_types.py` (WP05)

### WP06 — Error tools
**Goal**: 7 error tools spanning JSON-RPC protocol codes, simulated parse, tool-level, unknown.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_errors.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP06-error-tools.md](tasks/WP06-error-tools.md) (~230 lines)

- [ ] T029 `tools/errors.py` 7 tools (WP06)
- [ ] T030 tool-level / unknown-code semantics (WP06)
- [ ] T031 `tests/test_errors.py` (WP06)

### WP07 — Delay tools
**Goal**: Timed tools + cancellation honoring `notifications/cancelled`.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_delays.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP07-delay-tools.md](tasks/WP07-delay-tools.md) (~250 lines)

- [ ] T032 `tools/delays.py` delay+fixed (WP07)
- [ ] T033 `delay_cancel` cancellation (WP07)
- [ ] T034 `tests/test_delays.py` (WP07)

### WP08 — Schema validation tools
**Goal**: 6 tools exercising required/optional/enum/nested/array/no-args schemas.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_schema.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP08-schema-tools.md](tasks/WP08-schema-tools.md) (~230 lines)

- [ ] T035 `tools/schema.py` 6 tools (WP08)
- [ ] T036 validation behavior + `_meta` (WP08)
- [ ] T037 `tests/test_schema.py` (WP08)

### WP09 — Notification tools
**Goal**: Server→client notifications incl. progress sequences and log levels.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_notifications.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP09-notification-tools.md](tasks/WP09-notification-tools.md) (~250 lines)

- [ ] T038 `tools/notifications.py` 4 list/update notifies (WP09)
- [ ] T039 progress (≥3) + log (all levels) (WP09)
- [ ] T040 `tests/test_notifications.py` (WP09)

### WP10 — Sampling tools
**Goal**: `sampling/createMessage` round-trips + graceful degradation.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_sampling.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP10-sampling-tools.md](tasks/WP10-sampling-tools.md) (~250 lines)

- [ ] T041 `tools/sampling.py` simple/system/max_tokens (WP10)
- [ ] T042 `sampling_unsupported` + degradation (WP10)
- [ ] T043 `tests/test_sampling.py` (WP10)

### WP11 — Protocol inspection tool
**Goal**: `inspect_session` exposing session metadata + incrementing requestCount.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_inspect.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP11-inspect-tool.md](tasks/WP11-inspect-tool.md) (~200 lines)

- [ ] T044 `tools/inspect.py` (WP11)
- [ ] T045 requestCount via session store (WP11)
- [ ] T046 `tests/test_inspect.py` (WP11)

### WP12 — Resources
**Goal**: Every resource shape incl. URI template, missing, and a large paginated family.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_resources.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP12-resources.md](tasks/WP12-resources.md) (~280 lines)

- [ ] T047 `resources.py` static + large family (WP12)
- [ ] T048 template + missing not-found (WP12)
- [ ] T049 `tests/test_resources.py` (WP12)

### WP13 — Prompts
**Goal**: 5 prompt shapes incl. multi-turn, embedded resource, no-description.
**Priority**: P1. **Independent test**: `uv run pytest tests/test_prompts.py`.
**Depends on**: WP03. **Prompt**: [tasks/WP13-prompts.md](tasks/WP13-prompts.md) (~230 lines)

- [ ] T050 `prompts.py` 5 shapes (WP13)
- [ ] T051 no_description + embedded_resource (WP13)
- [ ] T052 `tests/test_prompts.py` (WP13)

### WP14 — Reference frontend
**Goal**: Static, framework-free UI fetching the live catalog from `/mcp`, offline-capable.
**Priority**: P2. **Independent test**: manual quickstart (load `/`, kill `/mcp` → error state).
**Depends on**: WP03. **Prompt**: [tasks/WP14-frontend.md](tasks/WP14-frontend.md) (~300 lines)

- [ ] T053 `frontend/index.html` (WP14)
- [ ] T054 `frontend/app.js` (WP14)
- [ ] T055 `frontend/style.css` (WP14)

### WP15 — Integration, validation & docs
**Goal**: Cross-cutting validation (every result has `_meta`; pagination multipage; all profiles
gate correctly; catalog sizing) plus the README test checklist.
**Priority**: P2 (last). **Independent test**: `uv run pytest` (full suite green).
**Depends on**: WP04–WP14. **Prompt**: [tasks/WP15-integration-docs.md](tasks/WP15-integration-docs.md) (~320 lines)

- [ ] T056 `tests/test_meta_contract.py` (WP15)
- [ ] T057 `tests/test_pagination.py` (WP15)
- [ ] T058 `tests/test_profiles.py` (WP15)
- [ ] T059 `tests/test_integration.py` (WP15)
- [ ] T060 `README.md` test checklist + docs (WP15)

---

## Parallelization

- After **WP03**, the lane group **WP04–WP14** (11 WPs) is fully parallelizable — each owns a
  disjoint file set and depends only on WP03.
- **WP15** is the single join point; it depends on the feature lanes completing.
- Critical path: WP01 → WP02 → WP03 → (any feature lane) → WP15.

## Open decision carried from planning (research R11)

The documented catalog yields **42 tools (5 pages @ size 10)** and **5 prompt shapes** — below
the PRD's "50+ tools / 50+ prompts" *targets*, though FR-018 forbids synthetic padding. WP15's
`test_integration.py` asserts pagination works with the real catalog (multipage proven by
resources ≥100 and tools ≥40). If a hard 50+ is required, add genuinely distinct tool/prompt
variants in the relevant feature WP rather than padding — decide before/at WP15.
