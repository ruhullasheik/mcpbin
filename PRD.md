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
| `error_parse` | Server returns JSON-RPC parse error (-32700) |
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
| `delay_cancel` | Long delay that respects cancellation notifications |

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
| `mcpbin://dynamic/{id}` | URI template resource — validates template handling |
| `mcpbin://missing` | A resource that returns a not-found error when read |

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

- Resource list with 100+ items, page size 10
- Prompt list with 50+ items
- Tool list with 50+ items
- Cursor must be opaque string — validates clients don't parse it
- Invalid cursor returns an error — validates client error handling on pagination

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

mcpbin should expose multiple "profiles" selectable at startup, each advertising a different capability subset. Clients should gracefully degrade when a capability is absent.

| Profile | Capabilities |
|---|---|
| `full` | All capabilities enabled (default) |
| `tools-only` | Only `tools` capability |
| `no-sampling` | Everything except sampling |
| `minimal` | Bare minimum — tools only, no pagination |

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
    ├── index.html              # Single-page UI — lists all tools, resources, prompts
    ├── style.css               # Styling
    └── app.js                  # Fetches tool/resource/prompt metadata and renders docs
```

### Key conventions
- All modules under `src/mcpbin/tools/` register tools directly onto the shared `FastMCP` app instance
- `server.py` imports all tool modules, mounts the MCP server at `/mcp`, and serves `frontend/` as static files at `/`
- Entry point: `mcpbin` CLI command maps to `mcpbin.server:main`
- `uv run mcpbin` starts the server locally; `uv run mcpbin --transport stdio` for stdio mode

---

## Open Questions

1. Should the hosted `mcpbin.dev` instance require an API key to prevent abuse?
2. Should there be a `--strict` mode that rejects any client behavior that is technically valid but unusual?
3. Should mcpbin validate client messages and return descriptive errors when the client sends malformed requests?
