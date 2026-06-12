# Feature Specification: mcpbin — Diagnostic MCP Test Server

**Mission**: mcpbin-test-server-01KTYJ79
**Created**: 2026-06-12
**Mission type**: software-dev
**Source**: PRD.md (in repo root)

## Summary

mcpbin is a diagnostic MCP server for MCP *client* developers — the "httpbin for the
Model Context Protocol". Developers point their client at mcpbin to verify protocol
compliance, validate error handling, and explore edge cases without building throwaway
servers. Every tool, resource, and prompt has a documented, deterministic, bit-for-bit
reproducible response. A bundled static reference UI documents the catalog.

This mission delivers all 12 PRD feature areas, three transports, four capability
profiles, the cross-cutting `_meta` contract, and a build-ready (but not published)
distribution.

---

## User Scenarios & Testing

### Primary actors

| Actor | Goal |
|---|---|
| MCP client library author | Validate full protocol compliance across every MCP feature in CI |
| App developer integrating MCP | Smoke-test client wiring before connecting to a real server |
| MCP spec contributor | Use a reference implementation of correct server behavior |
| SDK maintainer | Run regression tests during SDK upgrades |

### Acceptance scenarios

1. **Echo round-trip** — Given a connected client, when it calls `echo` with mixed
   argument types, then mcpbin returns every argument unchanged plus a `_meta` block
   naming the tool and echoing the received arguments.
2. **Content-type coverage** — Given a client that wants to exercise its response
   parser, when it calls the response-type tools, then it receives at least one of each
   MCP content type (text, image, resource, multiple, empty) and a tool-level error
   result (`isError: true`).
3. **Error discrimination** — Given a client testing error handling, when it calls each
   `error_*` tool, then it can distinguish JSON-RPC protocol errors (codes
   `-32700`…`-32603`, plus a non-standard code) from tool-level errors (`isError: true`).
4. **Timeout & cancellation** — Given a client testing slow tools, when it calls the
   delay tools, then responses arrive after the documented delay; and when it sends
   `notifications/cancelled` to `delay_cancel` before completion, then the tool returns
   `isError: true` with message `"cancelled by client"`.
5. **Schema enforcement** — Given a client that surfaces tool schemas, when it inspects
   the schema tools, then it sees required fields, optional fields, enums, nested
   objects, typed arrays, and a no-args tool, each behaving per its declared schema.
6. **Resource shapes** — Given a client testing resources, when it lists and reads
   resources, then it can read text/markdown/binary resources, resolve a URI template
   (`mcpbin://dynamic/{id}` for alpha/beta/gamma), and observe a not-found error for an
   unknown template id and for `mcpbin://missing`.
7. **Prompt shapes** — Given a client testing prompts, when it lists and gets prompts,
   then it receives single-message, arg-bearing, multi-turn, embedded-resource, and
   no-description prompts.
8. **Pagination** — Given the full catalog, when a client lists tools/resources/prompts,
   then it must follow multiple opaque cursors; the final page omits `nextCursor`
   entirely; and an invalid cursor returns `-32602` with message
   `"invalid or expired cursor"`.
9. **Server→client push** — Given a client that handles notifications, when it calls the
   `notify_*` tools, then it receives the corresponding server-sent notifications,
   including ≥3 progress notifications and log messages at every level.
10. **Sampling** — Given a client that advertises sampling, when it calls the `sampling_*`
    tools, then mcpbin issues `sampling/createMessage` back to the client; and when the
    client does not advertise sampling, then `sampling_unsupported` returns a graceful
    error.
11. **Capability negotiation** — Given a chosen `--profile`, when a client initializes,
    then the advertised capabilities match the profile, and list methods for omitted
    capabilities return `-32601` (not an empty list).
12. **Session inspection** — Given an active session, when a client calls
    `inspect_session`, then it receives protocol version, client info, negotiated
    capabilities, transport, and a `requestCount` that increments across calls.
13. **Reference UI** — Given the server running over HTTP, when a developer opens the
    web UI, then it renders the live tool/resource/prompt catalog grouped by feature
    area by fetching `/mcp`; and when `/mcp` is unreachable, then each section shows a
    single inline error without a JS exception.

### Edge cases

- `delay` with `seconds` > 30 clamps to 30; `delay_cancel` returns a normal result if no
  cancellation arrives within 60 s.
- `error_parse` cannot trigger a real pre-routing parse error, so it returns a simulated,
  well-formed JSON-RPC `-32700` object as text content with a `_meta.note` explaining the
  simulation.
- `return_empty` returns `content: []` with zero blocks (but still must carry `_meta` —
  see assumptions).
- Tools that ignore their input (`error_*`) still report the raw parsed input in
  `_meta.received`.
- The UI must render correctly fully offline after first load (no CDN/external deps).

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Provide echo tools (`echo`, `echo_string`, `echo_number`, `echo_boolean`, `echo_object`, `echo_array`, `echo_all_types`) that return their inputs unchanged. | Draft |
| FR-002 | Provide response-type tools (`return_text`, `return_image`, `return_resource`, `return_multiple`, `return_empty`, `return_isError`) covering every MCP content type, where `return_image` yields a decodable base64 PNG with `mimeType: image/png`. | Draft |
| FR-003 | Provide error tools (`error_parse`, `error_invalid_request`, `error_method_not_found`, `error_invalid_params`, `error_internal`, `error_tool_level`, `error_unknown_code`) emitting the documented JSON-RPC codes; `error_unknown_code` uses a code outside `-32700`…`-32603`; `error_parse` is simulated per its PRD note. | Draft |
| FR-004 | Provide delay tools (`delay` with clamped `seconds` ≤ 30, `delay_1s`, `delay_5s`, `delay_30s`, `delay_cancel`) where `delay_cancel` honors `notifications/cancelled` and always reports cancelled-vs-completed in `_meta`. | Draft |
| FR-005 | Provide schema tools (`schema_required_fields`, `schema_optional_fields`, `schema_enum`, `schema_nested`, `schema_array_items`, `schema_no_args`) with the declared input-schema shapes and matching validation behavior. | Draft |
| FR-006 | Provide resources covering plain text, markdown, binary blob (base64), a large paginated list, a URI template `mcpbin://dynamic/{id}` (valid: alpha/beta/gamma; others not-found), and `mcpbin://missing` (listed but always not-found on read). | Draft |
| FR-007 | Provide prompts: `simple`, `with_args` (required + optional), `multi_turn` (alternating user/assistant), `with_embedded_resource`, and `no_description` (no description field in listing). | Draft |
| FR-008 | Support cursor-based pagination for `tools/list`, `resources/list`, `prompts/list` with opaque base64 cursors, page size 10, absent `nextCursor` on the final page, and `-32602` + `"invalid or expired cursor"` on a bad cursor. | Draft |
| FR-009 | Provide notification tools (`notify_resource_updated`, `notify_resource_list_changed`, `notify_prompt_list_changed`, `notify_tool_list_changed`, `notify_progress`, `notify_log`) that emit the corresponding server→client notifications; `notify_progress` sends ≥3 progress messages; `notify_log` emits ≥1 message at debug/info/warning/error. | Draft |
| FR-010 | Provide sampling tools (`sampling_simple`, `sampling_with_system`, `sampling_max_tokens`, `sampling_unsupported`) that issue `sampling/createMessage` to the client, including system prompt and maxTokens where specified, and degrade gracefully when sampling is not advertised. | Draft |
| FR-011 | Support four startup profiles via `--profile` (`full` default, `tools-only`, `no-sampling`, `minimal`) that advertise the documented capability subsets; list methods for omitted capabilities return `-32601`; `minimal` advertises no `listChanged`. | Draft |
| FR-012 | Provide `inspect_session` returning `protocolVersion`, `clientInfo`, `negotiatedCapabilities`, `transport`, and a per-session `requestCount` that increments across calls. | Draft |
| FR-013 | Include a `_meta` object as the final text content block of every tool result with fixed schema `{tool, received, note}`; `received` always reflects raw parsed input (even when ignored); `isError` results still carry `_meta`. | Draft |
| FR-014 | Support three transports — stdio, HTTP+SSE, Streamable HTTP — selectable via a `--transport` startup flag from a single binary/entry point. | Draft |
| FR-015 | Serve a static, framework-free reference UI at `/` that fetches the live catalog from `/mcp`, groups tools by feature area, follows all pagination cursors for resources/prompts, shows a single inline error per section when `/mcp` is unreachable, and renders offline after first load. | Draft |
| FR-016 | Every tool exposes a human-readable `description` stating what it does and what to expect; structured logs are emitted to stderr. | Draft |
| FR-017 | Ship a README "test checklist" enumerating the calls a compliant client should be able to make against mcpbin. | Draft |
| FR-018 | The combined catalog across all feature areas reaches the pagination thresholds (≥50 tools, ≥100 resources, ≥50 prompts) using only real feature tools — no synthetic padding. | Draft |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|---|---|---|---|
| NFR-001 | Determinism — identical requests produce identical responses. | Byte-for-byte identical tool results across repeated calls (excluding inherently dynamic fields: `requestCount`, timestamps if any). | Draft |
| NFR-002 | Delay accuracy — timed tools respond within tolerance. | `delay seconds:2` responds in 2 ± 0.5 s; `delay_1s/5s/30s` within their target ± 1 s. | Draft |
| NFR-003 | Cancellation latency — `delay_cancel` reacts to cancellation promptly. | Returns within 1 s of receiving `notifications/cancelled`. | Draft |
| NFR-004 | Offline UI — reference UI works without network after first load. | Zero external/CDN requests; full render with network disabled post-load. | Draft |
| NFR-005 | Self-hostable startup — a developer can launch mcpbin from a clean checkout. | Single command (`uv run mcpbin`) starts the server; documented in README. | Draft |
| NFR-006 | Documentation completeness — every catalog item is discoverable and explained. | 100% of tools/resources/prompts have a non-empty description; every tool result has a valid `_meta`. | Draft |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Implementation language is Python 3.12+. | Draft |
| C-002 | Package/dependency management uses `uv` exclusively (no pip, conda, or non-uv venv). | Draft |
| C-003 | MCP server framework is FastMCP (`fastmcp`); it is the only third-party runtime dependency. | Draft |
| C-004 | Frontend is static HTML/CSS/vanilla JS — no Node.js, no build step, no framework, no external deps. | Draft |
| C-005 | Target MCP spec version is 2025-03-26. | Draft |
| C-006 | Project layout follows the PRD structure (`src/mcpbin/...`, `frontend/`, `pyproject.toml`, `uv.lock`, `.python-version`); entry point `mcpbin` → `mcpbin.server:main`. | Draft |
| C-007 | Distribution is build-ready (Dockerfile + PyPI packaging config) but this mission does not publish to PyPI/ghcr nor deploy mcpbin.dev. | Draft |
| C-008 | `uv.lock` and `.python-version` are committed to source control. | Draft |

---

## Success Criteria

- SC-001 — A compliant MCP client can complete every item in the README test checklist
  against the `full` profile over stdio with zero failures.
- SC-002 — Every documented feature-area acceptance scenario (1–13 above) passes under
  the `full` profile over stdio.
- SC-003 — The same tool call issued twice returns identical results (excluding
  `requestCount` and any explicitly dynamic field).
- SC-004 — Listing tools, resources, and prompts each requires following more than one
  page of opaque cursors, and the final page carries no `nextCursor`.
- SC-005 — Switching profiles changes advertised capabilities such that omitted
  capabilities' list methods return `-32601`, validated for all four profiles.
- SC-006 — The reference UI renders the complete catalog grouped by feature area, and
  degrades to a single inline error per section when the MCP endpoint is unreachable —
  with no uncaught client-side exceptions.
- SC-007 — A new developer can clone the repo and start mcpbin with a single documented
  command, and can build the Docker image successfully.

---

## Key Entities

| Entity | Description |
|---|---|
| Tool | A named, schema-bearing callable returning MCP content blocks plus a `_meta` block. Grouped by feature area (echo, response types, errors, delays, schema, notifications, sampling, inspect). |
| Resource | An addressable item (static URI or URI template) returning text, markdown, or binary content; some are intentionally missing/not-found. |
| Prompt | A named message template, optionally with arguments, producing one or more user/assistant messages. |
| `_meta` block | Fixed `{tool, received, note}` object appended to every tool result documenting the call. |
| Profile | A named capability subset advertised at `initialize` (`full`, `tools-only`, `no-sampling`, `minimal`). |
| Session | Per-connection state holding negotiated capabilities, transport, and a `requestCount`. |
| Cursor | Opaque base64 pagination token; clients must not parse or construct it. |

---

## Assumptions

- The three PRD "Open Questions" are **out of scope** for this mission and recorded below:
  hosted API-key gating, a `--strict` mode, and client-message validation. They may be
  revisited in a future mission.
- Distribution is build-ready but unpublished (per C-007): a Dockerfile and packaging
  metadata are produced and the image builds, but no artifact is pushed and no site is
  deployed.
- `_meta` for `return_empty`: the PRD requires `content: []` (zero blocks) AND a `_meta`
  block on every result. These are reconciled by treating the empty-content requirement
  as "no *substantive* content blocks"; the `_meta` text block is the documentation
  envelope and is still present. (Flagged for confirmation during planning if FastMCP
  cannot attach `_meta` without a content block.)
- All acceptance is measured against the `full` profile over stdio unless a criterion
  explicitly names another profile/transport.
- "Bit-for-bit reproducible" excludes inherently dynamic fields such as `requestCount`.
- Target Python is 3.12+ as the PRD states "Python 3.12+"; the committed `.python-version`
  pins a concrete 3.12.x at planning time.

## Out of Scope

- Proxying to httpbin or any HTTP service.
- A general-purpose MCP server framework or runtime-configurable mock responses.
- Load/performance testing.
- Actual PyPI/ghcr publishing and mcpbin.dev deployment (build-ready only).
- `--strict` mode, client-message validation, and hosted API-key gating (PRD open
  questions, deferred).
- Interactive "run this tool" execution in the reference UI (documentation-only UI).
