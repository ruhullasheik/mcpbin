# PRD: mcpbin — MCP Test Server for Client Developers

## Overview

**mcpbin** is a diagnostic MCP server designed for MCP client developers. It mirrors the philosophy of [httpbin.org](https://httpbin.org) — deterministic, inspectable, self-hostable — but for the Model Context Protocol. Developers point their MCP client at mcpbin to verify protocol compliance, validate error handling, and explore edge cases without building throwaway servers.

---

## Problem Statement

MCP client developers have no standard test surface. Today they must:
- Build their own throwaway servers to test specific behaviors
- Use the `everything` demo server, which is unfocused and not designed for validation
- Guess whether a client bug is in their code or in the server they're testing against

There is no equivalent of httpbin — a well-known, stable, self-hostable server where every tool and resource has a documented, predictable response.

---

## Goals

- Give MCP client developers a single server to validate their implementation against
- Cover every major MCP protocol feature with testable, deterministic endpoints
- Be trivially self-hostable (Docker, npx, binary)
- Produce human-readable output that makes debugging easy
- Serve as a living reference implementation of correct MCP server behavior

## Non-Goals

- Not a proxy to httpbin or any HTTP service
- Not a general-purpose MCP server framework
- Not a load/performance testing tool
- Not a mock generator — responses are fixed and documented, not configurable at runtime

---

## Users

| User | Need |
|---|---|
| MCP client library authors | Validate full protocol compliance across all features |
| App developers integrating MCP | Smoke-test client setup before connecting to real servers |
| MCP spec contributors | Reference implementation for correct server behavior |
| SDK maintainers | Regression testing during SDK upgrades |

---

## Transport Support

mcpbin must support all standard MCP transports:

| Transport | Notes |
|---|---|
| **stdio** | Primary; used by Claude Desktop, most CLI clients |
| **HTTP + SSE** | For web-based and remote clients |
| **Streamable HTTP** | Newer transport per MCP 2025-03-26 spec |

A single binary should support all three via a startup flag (e.g., `--transport stdio`).

---

## Feature Areas

### 1. Echo Tools

Tools that return exactly what the client sent. Used to validate argument serialization and transport fidelity.

| Tool | Description |
|---|---|
| `echo` | Returns all arguments as-is in a JSON text response |
| `echo_string` | Accepts a single string, returns it |
| `echo_number` | Accepts a number, returns it |
| `echo_boolean` | Accepts a boolean, returns it |
| `echo_object` | Accepts an arbitrary object, returns it |
| `echo_array` | Accepts an array, returns it |
| `echo_all_types` | Accepts one arg of each primitive type, returns all |

**Why:** Validates that the client serializes tool arguments correctly over the wire.

---

### 2. Response Type Tools

Tools that return every possible MCP content type. Used to validate client-side response parsing.

| Tool | Returns |
|---|---|
| `return_text` | `content: [{type: "text", text: "..."}]` |
| `return_image` | `content: [{type: "image", data: "...", mimeType: "image/png"}]` — a small test PNG |
| `return_resource` | `content: [{type: "resource", resource: {...}}]` |
| `return_multiple` | Array of mixed content types in one response |
| `return_empty` | `content: []` — empty result |
| `return_isError` | `isError: true` with a text message — tool-level error, not protocol error |

**Why:** Validates content type parsing; catches clients that only handle text.

---

### 3. Error Tools

Tools that trigger protocol-level and application-level errors. Used to validate error handling paths.

| Tool | Behavior |
|---|---|
| `error_parse` | Returns JSON-RPC parse error (-32700). Because a real parse error occurs before routing, this tool simulates the response: it returns a well-formed JSON-RPC error object with code `-32700` as its text content, wrapped in a normal tool result. The `_meta.note` explains the simulation. This tests client-side parse-error *handling*, not server-side parse-error *detection*. |
| `error_invalid_request` | Returns invalid request error (-32600) |
| `error_method_not_found` | Returns method not found (-32601) |
| `error_invalid_params` | Returns invalid params (-32602) |
| `error_internal` | Returns internal error (-32603) |
| `error_tool_level` | Returns `isError: true` in tool result (not protocol error) |
| `error_unknown_code` | Returns a non-standard error code |

**Why:** Distinguishes protocol errors from tool errors; validates client resilience.

---

### 4. Delay Tools

Tools that respond after a configurable delay. Used to validate timeout handling and cancellation.

| Tool | Behavior |
|---|---|
| `delay` | Accepts `seconds: number`, responds after that delay (max 30s) |
| `delay_1s` | Fixed 1-second delay |
| `delay_5s` | Fixed 5-second delay |
| `delay_30s` | Fixed 30-second delay — tests client timeout behavior |
| `delay_cancel` | Waits up to 60 seconds but listens for `notifications/cancelled`. If a cancellation arrives before completion, the tool returns immediately with `isError: true` and message `"cancelled by client"`. If no cancellation arrives within 60 seconds, the tool returns normally with a text result. The `_meta` field always reports whether the result was cancelled or completed. |

**Why:** Validates that clients handle slow tools gracefully and support `notifications/cancelled`.

---

### 5. Schema Validation Tools

Tools with strict input schemas. Used to validate that clients send correct argument shapes.

| Tool | Schema |
|---|---|
| `schema_required_fields` | Has required fields — validates client sends them |
| `schema_optional_fields` | Has optional fields — validates client handles optionality |
| `schema_enum` | Field restricted to an enum — validates enum handling |
| `schema_nested` | Deeply nested object schema |
| `schema_array_items` | Array with typed items |
| `schema_no_args` | Tool with no inputSchema — validates clients handle this |

**Why:** Validates that client UI/tooling correctly reads and enforces JSON Schema.

---

### 6. Resources

Resources covering every resource shape. Used to validate `resources/list` and `resources/read`.

| Resource | Description |
|---|---|
| `mcpbin://text/plain` | Plain text resource |
| `mcpbin://text/markdown` | Markdown resource |
| `mcpbin://blob/binary` | Binary blob (base64) |
| `mcpbin://large/paginated` | Large resource list requiring pagination |
| `mcpbin://dynamic/{id}` | URI template resource — validates template handling. Valid IDs are `alpha`, `beta`, and `gamma`; each returns a short text resource with that name in the content. Any other `id` returns a not-found error (distinct from `mcpbin://missing` — the URI resolves but the content does not exist). |
| `mcpbin://missing` | A URI that is listed in `resources/list` but always returns a not-found error when read — simulates a resource that has been deleted or is temporarily unavailable |

**Why:** Validates resource listing, reading, URI templates, and error handling.

---

### 7. Prompts

Prompts covering every prompt shape. Used to validate `prompts/list` and `prompts/get`.

| Prompt | Description |
|---|---|
| `simple` | Single user message, no args |
| `with_args` | Prompt with required and optional arguments |
| `multi_turn` | Multiple messages (user + assistant alternating) |
| `with_embedded_resource` | Message containing an embedded resource |
| `no_description` | Prompt with no description field |

**Why:** Validates prompt listing, argument passing, and multi-turn message handling.

---

### 8. Pagination

Used to validate cursor-based pagination for tools, resources, and prompts.

The pagination feature area does not add tools — it is exercised by calling standard MCP list methods (`tools/list`, `resources/list`, `prompts/list`) against mcpbin's full tool/resource/prompt catalog. The catalog is intentionally large enough to require multiple pages.

Page size targets:
- `resources/list`: 100+ resources, page size 10
- `prompts/list`: 50+ prompts, page size 10
- `tools/list`: 50+ tools, page size 10

Pagination behavior:
- Cursors are opaque base64-encoded strings — clients must not parse or construct them
- Omitting `cursor` returns the first page
- An invalid cursor returns JSON-RPC error `-32602` (invalid params) with message `"invalid or expired cursor"`
- The final page omits the `nextCursor` field entirely (not `null`, not empty string — absent)

To reach the 50+ tool count, the full set of tools from all feature areas (echo, response types, errors, delays, schema, notifications, sampling, inspect) combined must meet the threshold. No synthetic padding tools are added.

---

### 9. Notifications (Server → Client)

Server-initiated notifications. Used to validate client notification handling.

| Tool | Triggers |
|---|---|
| `notify_resource_updated` | Sends `notifications/resources/updated` |
| `notify_resource_list_changed` | Sends `notifications/resources/list_changed` |
| `notify_prompt_list_changed` | Sends `notifications/prompts/list_changed` |
| `notify_tool_list_changed` | Sends `notifications/tools/list_changed` |
| `notify_progress` | Sends a sequence of `notifications/progress` messages then completes |
| `notify_log` | Sends `notifications/message` (log) at various levels |

**Why:** Validates that clients handle server-push notifications, not just request/response.

---

### 10. Sampling (Server → Client)

Used to validate that clients support `sampling/createMessage`.

| Tool | Behavior |
|---|---|
| `sampling_simple` | Makes a minimal `createMessage` request back to client |
| `sampling_with_system` | Includes a system prompt in the request |
| `sampling_max_tokens` | Requests response with specific `maxTokens` |
| `sampling_unsupported` | Called when client declares no sampling capability — returns graceful error |

**Why:** Sampling is a rarely-tested client capability; most clients don't implement it.

---

### 11. Capability Negotiation

mcpbin should expose multiple "profiles" selectable at startup via the `--profile` flag, each advertising a different capability subset. Clients should gracefully degrade when a capability is absent.

```
mcpbin --profile tools-only
mcpbin --profile no-sampling
mcpbin --profile minimal
mcpbin --profile full   # default if --profile is omitted
```

| Profile | Capabilities advertised in `initialize` response |
|---|---|
| `full` | `tools`, `resources`, `prompts`, `sampling`, pagination for all three (default) |
| `tools-only` | `tools` only — no resources, no prompts, no sampling |
| `no-sampling` | `tools`, `resources`, `prompts`, pagination — sampling omitted |
| `minimal` | `tools` only, no pagination (`listChanged` not advertised) |

When a profile omits a capability, the corresponding list methods (`resources/list`, etc.) must return JSON-RPC error `-32601` (method not found), not an empty list.

**Why:** Validates that clients don't assume capabilities that aren't advertised.

---

### 12. Protocol Inspection Tool

A special tool that returns metadata about the current session:

```
inspect_session → {
  protocolVersion: "2025-03-26",
  clientInfo: { name, version },
  negotiatedCapabilities: { ... },
  transport: "stdio" | "sse" | "http",
  requestCount: 42
}
```

**Why:** Lets client developers verify their handshake and capability negotiation succeeded.

---

## Hosting & Distribution

| Method | Command |
|---|---|
| uvx | `uvx mcpbin` |
| pip | `pip install mcpbin && mcpbin` |
| Docker | `docker run ghcr.io/mcpbin/mcpbin` |
| Hosted (frontend) | `https://mcpbin.dev` — web UI for browsing tools, resources, and docs |
| Hosted (MCP endpoint) | `https://mcpbin.dev/mcp` — live MCP server (Streamable HTTP transport) |

---

## Developer Experience

- Every tool has a `description` that states exactly what it does and what to expect
- Every tool response includes a `_meta` field documenting what was received and why the response looks the way it does
- The README includes a "test checklist" — a list of calls a compliant client should be able to make
- Structured logging to stderr so developers can see server-side behavior alongside client-side behavior

### `_meta` Field Schema

Every tool result must include a `_meta` object as the final text content block in the response. The schema is fixed across all tools:

```json
{
  "_meta": {
    "tool": "echo_string",
    "received": { "value": "hello" },
    "note": "Returned the string argument unchanged."
  }
}
```

| Field | Type | Description |
|---|---|---|
| `tool` | string | Name of the tool that was called |
| `received` | object | The exact arguments received from the client, as parsed by the server |
| `note` | string | Human-readable explanation of why the response looks the way it does |

Rules:
- `received` must always reflect the raw parsed input, even if the tool ignores it (e.g. `error_*` tools)
- `note` should be one sentence; reference the MCP spec section where relevant
- Tools that return `isError: true` still include `_meta` as a separate text content block alongside the error message

---

## Success Metrics

- MCP client library maintainers use mcpbin in their CI test suites
- Adopted as a recommended test tool in the official MCP documentation
- Zero ambiguity in tool behavior — every tool response is bit-for-bit reproducible

---

## Implementation Notes

- **Language:** Python 3.12+
- **Package manager:** `uv` (strict — no pip, no conda, no venv outside uv)
- **Framework:** FastMCP (`fastmcp`) — decorator-based, FastAPI-like ergonomics
- **Frontend:** Static HTML/CSS/JS — no Node.js, no build step, no framework
- **Distribution:** `uvx mcpbin` (via PyPI) and Docker
- **Runtime dependencies:** FastMCP only — no other third-party packages
- **Spec version:** Target MCP 2025-03-26 (latest as of June 2026)

---

## Project Structure

```
mcpbin/
├── pyproject.toml              # uv project manifest — dependencies, entry points, metadata
├── uv.lock                     # lockfile — committed to source control
├── .python-version             # pins Python version for uv
├── README.md
├── src/
│   └── mcpbin/
│       ├── __init__.py
│       ├── server.py           # FastMCP app — mounts MCP at /mcp, serves frontend at /
│       ├── tools/
│       │   ├── echo.py         # Echo tools (feature area 1)
│       │   ├── response_types.py  # Response type tools (feature area 2)
│       │   ├── errors.py       # Error tools (feature area 3)
│       │   ├── delays.py       # Delay tools (feature area 4)
│       │   ├── schema.py       # Schema validation tools (feature area 5)
│       │   ├── notifications.py   # Notification tools (feature area 9)
│       │   ├── sampling.py     # Sampling tools (feature area 10)
│       │   └── inspect.py      # Session inspection tool (feature area 12)
│       ├── resources.py        # MCP resources (feature area 6)
│       └── prompts.py          # MCP prompts (feature area 7)
└── frontend/
    ├── index.html              # Single-page UI — see Frontend Spec below
    ├── style.css               # Styling
    └── app.js                  # Fetches tool/resource/prompt metadata and renders docs
```

### Frontend Spec

The frontend is a static single-page app served at `/`. It has no build step and no framework — plain HTML, CSS, and vanilla JS only.

**Layout:**
- Fixed top navbar: mcpbin logo/name on the left, protocol version badge (`MCP 2025-03-26`) on the right
- Left sidebar: navigation list with three sections — Tools, Resources, Prompts — each collapsible, each item clickable
- Main content area: detail panel for the selected item

**Tools view (default on load):**
- `app.js` fetches the tool list by calling the MCP endpoint at `/mcp` (Streamable HTTP) and issuing a `tools/list` request
- Each tool renders as a card with: tool name (monospace), description, input schema displayed as a formatted JSON block
- Tools are grouped by feature area using a heading (Echo, Response Types, Errors, Delays, Schema, Notifications, Sampling, Inspect)

**Resources view:**
- Fetches `resources/list` (with pagination — follows all cursors to build the full list)
- Each resource shows: URI, name, description, MIME type

**Prompts view:**
- Fetches `prompts/list` (with pagination)
- Each prompt shows: name, description, arguments table (name / required / description)

**No interactive tool execution** — the frontend is a reference/documentation UI only, not a playground. There is no "run this tool" button.

**Error state:** If the MCP endpoint is unreachable, each section displays a single inline message: `"Could not reach MCP server at /mcp"`.

**No external dependencies** — no CDN fonts, no icon libraries, no analytics. Must render correctly offline once loaded.

### Key conventions
- All modules under `src/mcpbin/tools/` register tools directly onto the shared `FastMCP` app instance
- `server.py` imports all tool modules, mounts the MCP server at `/mcp`, and serves `frontend/` as static files at `/`
- Entry point: `mcpbin` CLI command maps to `mcpbin.server:main`
- `uv run mcpbin` starts the server locally; `uv run mcpbin --transport stdio` for stdio mode

---

## Acceptance Criteria

A feature area is considered complete when all items in its checklist pass using the `full` profile over stdio transport.

### 1. Echo Tools
- [ ] `echo` called with mixed argument types returns all arguments unchanged
- [ ] `echo_string` / `echo_number` / `echo_boolean` / `echo_object` / `echo_array` each return their input type unchanged
- [ ] `echo_all_types` accepts one arg of each primitive type and returns all of them
- [ ] Every response includes a valid `_meta` block with correct `tool` and `received` fields

### 2. Response Type Tools
- [ ] `return_text` returns exactly one `text` content block
- [ ] `return_image` returns a valid `image` content block with a decodable base64 PNG and `mimeType: "image/png"`
- [ ] `return_resource` returns a `resource` content block with a valid resource object
- [ ] `return_multiple` returns at least one block of each of three content types in a single response
- [ ] `return_empty` returns `content: []` with no content blocks
- [ ] `return_isError` returns `isError: true` with at least one text content block

### 3. Error Tools
- [ ] Each `error_*` tool returns the documented JSON-RPC error code in its response
- [ ] `error_tool_level` returns `isError: true` (not a protocol error)
- [ ] `error_parse` response includes a note in `_meta` clarifying the simulation
- [ ] `error_unknown_code` returns a non-standard code outside the `-32700`–`-32603` range

### 4. Delay Tools
- [ ] `delay` with `seconds: 2` responds in 2±0.5 seconds
- [ ] `delay_1s`, `delay_5s`, `delay_30s` respond within 1s, 5s, 30s respectively (±1s)
- [ ] `delay` with `seconds` exceeding 30 clamps to 30 seconds
- [ ] `delay_cancel` returns `isError: true` with message `"cancelled by client"` when a `notifications/cancelled` is sent before completion
- [ ] `delay_cancel` returns a normal result if no cancellation arrives within 60 seconds

### 5. Schema Validation Tools
- [ ] `schema_required_fields` returns an error when required fields are missing
- [ ] `schema_optional_fields` succeeds when optional fields are omitted
- [ ] `schema_enum` returns an error when a value outside the enum is passed
- [ ] `schema_nested` accepts a deeply nested object and returns it
- [ ] `schema_array_items` accepts a typed array and returns it
- [ ] `schema_no_args` succeeds when called with no arguments

### 6. Resources
- [ ] `resources/list` returns all resources including URI template entries
- [ ] `mcpbin://text/plain` and `mcpbin://text/markdown` return text content
- [ ] `mcpbin://blob/binary` returns a valid base64-encoded blob
- [ ] `mcpbin://dynamic/alpha`, `/beta`, `/gamma` each return distinct text content
- [ ] `mcpbin://dynamic/{unknown}` returns a not-found error
- [ ] `mcpbin://missing` is listed but returns a not-found error on read
- [ ] `mcpbin://large/paginated` requires multiple `resources/list` cursor pages to retrieve in full

### 7. Prompts
- [ ] `prompts/list` returns all prompts
- [ ] `simple` prompt returns a single user message with no arguments
- [ ] `with_args` prompt accepts required and optional arguments and includes them in messages
- [ ] `multi_turn` prompt returns alternating user/assistant messages
- [ ] `with_embedded_resource` prompt returns a message containing an embedded resource content block
- [ ] `no_description` prompt has no `description` field in the listing

### 8. Pagination
- [ ] `tools/list`, `resources/list`, `prompts/list` all require multiple pages to retrieve fully
- [ ] Each page response includes `nextCursor` except the final page
- [ ] Final page has no `nextCursor` field (not null, not empty — absent)
- [ ] An invalid cursor returns error `-32602` with message `"invalid or expired cursor"`

### 9. Notifications
- [ ] Each `notify_*` tool triggers the corresponding server-sent notification
- [ ] `notify_progress` sends at least 3 progress notifications before the tool result
- [ ] `notify_log` sends at least one log message at each level (debug, info, warning, error)

### 10. Sampling
- [ ] `sampling_simple` issues a `sampling/createMessage` request to the client and returns the response
- [ ] `sampling_with_system` includes a `systemPrompt` field in the createMessage request
- [ ] `sampling_max_tokens` includes `maxTokens` in the createMessage request
- [ ] `sampling_unsupported` returns a graceful error when the client does not advertise the sampling capability

### 11. Capability Profiles
- [ ] `--profile full` advertises tools, resources, prompts, sampling, and pagination
- [ ] `--profile tools-only` advertises only tools; `resources/list` returns `-32601`
- [ ] `--profile no-sampling` succeeds for all non-sampling operations; `sampling_simple` returns a graceful error
- [ ] `--profile minimal` advertises tools only with no `listChanged` in capabilities

### 12. Protocol Inspection
- [ ] `inspect_session` returns `protocolVersion`, `clientInfo`, `negotiatedCapabilities`, `transport`, and `requestCount`
- [ ] `requestCount` increments correctly across multiple calls in the same session

### Frontend
- [ ] Page loads and renders tool/resource/prompt lists by fetching from `/mcp`
- [ ] Tools are grouped by feature area with headings
- [ ] Resources and prompts lists follow all pagination cursors to display complete lists
- [ ] If `/mcp` is unreachable, each section shows the error message without a JS exception
- [ ] Page renders correctly with no network access after initial load (no external CDN deps)

---

## Open Questions

1. Should the hosted `mcpbin.dev` instance require an API key to prevent abuse?
2. Should there be a `--strict` mode that rejects any client behavior that is technically valid but unusual?
3. Should mcpbin validate client messages and return descriptive errors when the client sends malformed requests?
