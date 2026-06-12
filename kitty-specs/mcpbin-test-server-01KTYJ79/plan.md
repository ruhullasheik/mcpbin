# Implementation Plan: mcpbin — Diagnostic MCP Test Server

**Branch**: `devs/ruhulla` | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/mcpbin-test-server-01KTYJ79/spec.md`

## Summary

Build mcpbin, an "httpbin for MCP": a deterministic diagnostic MCP server that lets MCP
*client* developers validate protocol compliance against documented, reproducible
endpoints. Implementation is a single Python 3.12+ package built on **FastMCP**, with
tools registered per feature area, MCP resources and prompts, four startup capability
**profiles**, three **transports** (stdio / HTTP+SSE / Streamable HTTP), a cross-cutting
`_meta` envelope on every tool result, and a static framework-free reference UI served at
`/`. Distribution is build-ready (Dockerfile + packaging) but unpublished.

The technical risk areas are concentrated where FastMCP's high-level API may not directly
expose low-level protocol behavior the PRD demands: opaque-cursor pagination semantics,
returning raw JSON-RPC error codes from a tool, attaching `_meta` to an *empty* result,
per-profile capability gating that returns `-32601`, cancellation handling, and
session-scoped `requestCount`. Phase 0 research resolves each before design.

## Technical Context

**Language/Version**: Python 3.12+ (committed `.python-version` pins a concrete 3.12.x)
**Primary Dependencies**: FastMCP (`fastmcp`) — the only third-party runtime dependency (C-003)
**Package manager**: `uv` exclusively; `uv.lock` + `.python-version` committed (C-002, C-008)
**Storage**: None — all responses are static/computed; per-session state is in-memory only
**Testing**: `pytest` (dev-only dependency) driving FastMCP's in-memory client for protocol
assertions; delay/cancellation tests use async timing; UI smoke is a manual quickstart step
**Target Platform**: Cross-platform CLI/server (Linux/macOS/Windows); Docker image for hosting
**Project Type**: Single project — Python package + co-located static `frontend/`
**Performance Goals**: Not a perf tool (non-goal). Timing accuracy only: `delay seconds:2`
in 2±0.5 s (NFR-002); cancellation reaction <1 s (NFR-003)
**Constraints**: Determinism / byte-for-byte reproducibility excluding `requestCount`
(NFR-001); offline-capable static UI, zero external/CDN deps (NFR-004, C-004); single-command
local start (NFR-005); MCP spec 2025-03-26 (C-005)
**Scale/Scope**: ~50+ tools, ~100+ resources, ~50+ prompts (to exercise pagination, FR-018);
4 profiles; 3 transports; 12 feature areas; 1 reference UI

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**SKIPPED** — no charter exists (`.kittify/charter/charter.md` not found). `spec-kitty charter
context --action plan` returned `mode: missing`. No governance gates to evaluate; no
violations to track. If a charter is added later, re-run this gate.

## Project Structure

### Documentation (this feature)

```
kitty-specs/mcpbin-test-server-01KTYJ79/
├── plan.md              # This file
├── research.md          # Phase 0 output — resolves FastMCP capability unknowns
├── data-model.md        # Phase 1 output — entities: Tool, Resource, Prompt, Profile, Session, _meta, Cursor
├── quickstart.md        # Phase 1 output — run + verify walkthrough mapped to acceptance scenarios
├── contracts/           # Phase 1 output — MCP method/tool/resource/prompt contracts
│   ├── tools.md         # Tool catalog: name, inputSchema, result shape, _meta, per feature area
│   ├── resources.md     # Resource catalog + URI templates + not-found behavior
│   ├── prompts.md       # Prompt catalog + argument tables + message shapes
│   ├── protocol.md      # Pagination, error codes, profiles/capabilities, notifications, sampling, inspect
│   └── meta-schema.json # JSON Schema for the fixed _meta envelope
└── tasks/               # Phase 2 (/spec-kitty.tasks) — NOT created here
```

### Source Code (repository root)

```
mcpbin/
├── pyproject.toml              # uv manifest: deps (fastmcp), entry point mcpbin -> mcpbin.server:main, pytest dev dep
├── uv.lock                     # committed lockfile (C-008)
├── .python-version             # committed, pins 3.12.x (C-008)
├── Dockerfile                  # build-ready image (C-007)
├── .dockerignore
├── README.md                   # includes the "test checklist" (FR-017)
├── src/
│   └── mcpbin/
│       ├── __init__.py
│       ├── server.py           # FastMCP app; CLI (--transport, --profile); mounts /mcp + static /; main()
│       ├── _meta.py            # build_meta(tool, received, note) helper; final-text-block convention (FR-013)
│       ├── profiles.py         # profile definitions + capability gating -> -32601 for omitted (FR-011)
│       ├── session.py          # per-session state: requestCount, negotiated caps, transport (FR-012)
│       ├── pagination.py       # opaque base64 cursor encode/decode; invalid -> -32602 (FR-008)
│       ├── errors.py           # JSON-RPC error helpers / codes (shared by error tools + protocol)
│       ├── assets/
│       │   └── test.png        # tiny deterministic PNG for return_image (FR-002)
│       ├── tools/
│       │   ├── __init__.py     # register_all(app, profile) aggregator
│       │   ├── echo.py         # FR-001
│       │   ├── response_types.py  # FR-002
│       │   ├── errors.py       # FR-003
│       │   ├── delays.py       # FR-004 (incl. cancellation)
│       │   ├── schema.py       # FR-005
│       │   ├── notifications.py   # FR-009
│       │   ├── sampling.py     # FR-010
│       │   └── inspect.py      # FR-012
│       ├── resources.py        # FR-006 (text/markdown/blob/paginated/template/missing)
│       └── prompts.py          # FR-007
├── frontend/
│   ├── index.html              # navbar + sidebar (Tools/Resources/Prompts) + detail panel (FR-015)
│   ├── style.css               # no external fonts/icons
│   └── app.js                  # fetch /mcp (Streamable HTTP), follow cursors, group by feature area, error state
└── tests/
    ├── conftest.py             # in-memory FastMCP client fixtures per profile
    ├── test_echo.py            # …one module per feature area, asserting acceptance scenarios + _meta
    ├── test_response_types.py
    ├── test_errors.py
    ├── test_delays.py
    ├── test_schema.py
    ├── test_resources.py
    ├── test_prompts.py
    ├── test_pagination.py
    ├── test_notifications.py
    ├── test_sampling.py
    ├── test_profiles.py
    ├── test_inspect.py
    └── test_meta_contract.py   # cross-cutting: every tool result carries valid _meta (FR-013)
```

**Structure Decision**: Single Python project (Technical Context "Project Type: single").
Tools are split one module per PRD feature area under `src/mcpbin/tools/`, each exposing a
`register(app, profile)` function; `tools/__init__.py:register_all` calls them. Cross-cutting
concerns (`_meta`, pagination, profiles, session, errors) are small dedicated modules so each
feature module stays focused and the protocol behavior is tested in isolation. The static
`frontend/` lives at repo root and is served by `server.py`. Tests mirror feature areas plus a
cross-cutting `_meta` contract test. This layout matches the PRD's prescribed structure (C-006)
while adding the cross-cutting modules and a `tests/` tree the PRD's tree omitted.

## Complexity Tracking

*No Charter Check violations to justify (charter skipped). Table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0 — Research (see research.md)

Open technical unknowns dispatched to research, each resolved with Decision / Rationale /
Alternatives in `research.md`:

1. **FastMCP transport selection** — how a single entry point selects stdio vs HTTP+SSE vs
   Streamable HTTP via `--transport` (FR-014, C-005).
2. **Per-profile capability gating** — how to advertise capability subsets at `initialize` and
   make omitted list methods return `-32601` rather than empty (FR-011).
3. **Opaque cursor pagination** — whether FastMCP exposes cursor hooks or pagination must be
   implemented at the protocol layer; encoding + `-32602` invalid-cursor behavior (FR-008).
4. **Raw JSON-RPC error emission from tools** — how `error_*` tools surface protocol error
   codes; confirm the `error_parse` simulation approach (FR-003).
5. **`_meta` on results, including empty results** — can `_meta` ride on a result with
   `content: []`; resolve the spec's flagged `return_empty` reconciliation (FR-013, FR-002).
6. **Cancellation** — how a tool observes `notifications/cancelled` to make `delay_cancel`
   return within 1 s (FR-004, NFR-003).
7. **Server→client notifications & progress** — emitting `notifications/*`, progress, and log
   levels from inside a tool via FastMCP Context (FR-009).
8. **Sampling round-trip** — issuing `sampling/createMessage` to the client and graceful
   degradation when the capability is absent (FR-010).
9. **Session `requestCount`** — accessing/incrementing per-session state across calls (FR-012).
10. **Deterministic tiny PNG** — a fixed, decodable base64 PNG asset for `return_image` (FR-002).
11. **Catalog sizing** — confirm real feature tools/resources/prompts reach the pagination
    thresholds without synthetic padding (FR-018).

## Phase 1 — Design & Contracts (see data-model.md, contracts/, quickstart.md)

- `data-model.md` — entities Tool, Resource, Prompt, Profile, Session, `_meta` block, Cursor;
  fields, validation rules from requirements, and the profile→capability matrix.
- `contracts/` — the MCP "API contracts": full tool catalog with input schemas and result
  shapes, resource catalog (incl. templates + not-found), prompt catalog, and a protocol
  contract doc (pagination, error codes, profiles, notifications, sampling, inspect), plus a
  JSON Schema for the `_meta` envelope.
- `quickstart.md` — clone → `uv run mcpbin` → connect a client → walk the 13 acceptance
  scenarios → build the Docker image; doubles as the seed for the README test checklist.

## ⛔ Stop point

This plan ends after Phase 1 artifacts. Work-package breakdown is the next phase —
run `/spec-kitty.tasks` explicitly.
