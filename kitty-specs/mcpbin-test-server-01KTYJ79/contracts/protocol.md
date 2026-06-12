# Contract: Protocol Behaviors

**Mission**: mcpbin-test-server-01KTYJ79 · MCP spec **2025-03-26** (C-005)

Cross-cutting protocol contracts that are not single tools.

## Pagination (FR-008)

- Applies to `tools/list`, `resources/list`, `prompts/list`. **Page size = 10.**
- `cursor` omitted → first page.
- `nextCursor` is an **opaque base64 string**; clients must not parse/construct it.
- **Final page omits `nextCursor` entirely** — not `null`, not `""`, absent.
- Invalid/expired cursor → JSON-RPC error **`-32602`**, message **`"invalid or expired cursor"`**.
- Catalog sizes force multiple pages: resources ≥100; tools 42 (5 pages); prompts per R11.

## Error codes (FR-003)

| Code | Meaning | Surfaced by |
|---|---|---|
| `-32700` | Parse error (simulated as text) | `error_parse` |
| `-32600` | Invalid request | `error_invalid_request` |
| `-32601` | Method not found | `error_method_not_found`; omitted-capability list methods |
| `-32602` | Invalid params | `error_invalid_params`; invalid cursor |
| `-32603` | Internal error | `error_internal` |
| non-standard | outside `-32700…-32603` | `error_unknown_code` |
| tool-level | `isError: true` (not a protocol error) | `error_tool_level`, `return_isError`, `delay_cancel` (on cancel) |

## Capability profiles (FR-011)

Selected via `--profile {full,tools-only,no-sampling,minimal}` (default `full`).

| Profile | initialize advertises | Omitted list methods |
|---|---|---|
| `full` | tools, resources, prompts, sampling, pagination, listChanged | — |
| `tools-only` | tools | `resources/list`, `prompts/list` → `-32601` |
| `no-sampling` | tools, resources, prompts, pagination | sampling tools degrade gracefully |
| `minimal` | tools, **no `listChanged`** | `resources/list`, `prompts/list` → `-32601` |

Omitted capability ⇒ its list method returns `-32601`, **never** an empty list.

## Notifications (server→client, FR-009)

`notifications/resources/updated`, `notifications/resources/list_changed`,
`notifications/prompts/list_changed`, `notifications/tools/list_changed`,
`notifications/progress` (≥3 in a sequence), `notifications/message` (log; debug/info/warning/error).

## Sampling (server→client, FR-010)

`sampling/createMessage` issued to the client, optionally with `systemPrompt` and `maxTokens`.
Graceful `isError` result when the client/profile lacks the sampling capability.

## Transports (FR-014)

Single entry point `mcpbin` → `mcpbin.server:main`, `--transport {stdio,sse,http}` (default
`stdio`). HTTP transports also serve the static frontend at `/` and the MCP endpoint at `/mcp`.

## Session inspection (FR-012)

`inspect_session` returns `{protocolVersion: "2025-03-26", clientInfo, negotiatedCapabilities,
transport, requestCount}`; `requestCount` increments per request within a session.

## `_meta` envelope (FR-013)

Final text content block of every tool result; schema in `meta-schema.json`; present even on
`isError` and empty results.
