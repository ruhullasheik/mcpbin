# Contract: Tool Catalog

**Mission**: mcpbin-test-server-01KTYJ79

Every tool result ends with a `_meta` block (see `meta-schema.json`). 42 named tools.
"received" = raw parsed args. Behaviors are deterministic (NFR-001) except where noted.

## Feature area: echo (FR-001) — 7 tools

| Tool | inputSchema | Result |
|---|---|---|
| `echo` | free-form object (any args) | All args returned as JSON text, unchanged. |
| `echo_string` | `{value: string}` (required) | The string, unchanged. |
| `echo_number` | `{value: number}` (required) | The number, unchanged. |
| `echo_boolean` | `{value: boolean}` (required) | The boolean, unchanged. |
| `echo_object` | `{value: object}` (required) | The object, unchanged. |
| `echo_array` | `{value: array}` (required) | The array, unchanged. |
| `echo_all_types` | `{string, number, boolean, object, array}` | All five returned together. |

## Feature area: response_types (FR-002) — 6 tools

| Tool | inputSchema | Result content |
|---|---|---|
| `return_text` | none | one `text` block. |
| `return_image` | none | one `image` block: base64 of committed `assets/test.png`, `mimeType: image/png`. |
| `return_resource` | none | one `resource` block with a valid embedded resource object. |
| `return_multiple` | none | ≥3 mixed blocks (text + image + resource). |
| `return_empty` | none | `content: []` (no substantive blocks); `_meta` still present (see research R5). |
| `return_isError` | none | `isError: true` + ≥1 text block + `_meta`. |

## Feature area: errors (FR-003) — 7 tools

| Tool | Result |
|---|---|
| `error_parse` | Simulated: text content is a well-formed JSON-RPC error object with code `-32700`; `_meta.note` explains the simulation (real parse errors precede routing). |
| `error_invalid_request` | JSON-RPC protocol error `-32600`. |
| `error_method_not_found` | JSON-RPC protocol error `-32601`. |
| `error_invalid_params` | JSON-RPC protocol error `-32602`. |
| `error_internal` | JSON-RPC protocol error `-32603`. |
| `error_tool_level` | Normal result with `isError: true` (NOT a protocol error). |
| `error_unknown_code` | Non-standard code outside `-32700…-32603`. |

All error tools still emit `_meta` with the raw received input.

## Feature area: delays (FR-004) — 5 tools

| Tool | inputSchema | Behavior |
|---|---|---|
| `delay` | `{seconds: number}` | Responds after `min(seconds, 30)` s (clamp at 30). |
| `delay_1s` | none | Fixed 1 s. |
| `delay_5s` | none | Fixed 5 s. |
| `delay_30s` | none | Fixed 30 s. |
| `delay_cancel` | none | Waits ≤60 s; on `notifications/cancelled` returns <1 s with `isError: true`, message `"cancelled by client"`; else normal result. `_meta` reports `cancelled` vs `completed`. |

## Feature area: schema (FR-005) — 6 tools

| Tool | inputSchema | Behavior |
|---|---|---|
| `schema_required_fields` | required fields | Error if a required field is missing. |
| `schema_optional_fields` | optional fields | Succeeds when optionals omitted. |
| `schema_enum` | `{value: enum[...]}` | Error if value outside enum. |
| `schema_nested` | deeply nested object | Accepts + returns the nested object. |
| `schema_array_items` | typed array | Accepts + returns the typed array. |
| `schema_no_args` | none (no inputSchema) | Succeeds with no args. |

## Feature area: notifications (FR-009) — 6 tools

| Tool | Emits |
|---|---|
| `notify_resource_updated` | `notifications/resources/updated`. |
| `notify_resource_list_changed` | `notifications/resources/list_changed`. |
| `notify_prompt_list_changed` | `notifications/prompts/list_changed`. |
| `notify_tool_list_changed` | `notifications/tools/list_changed`. |
| `notify_progress` | ≥3 `notifications/progress` then a result. |
| `notify_log` | `notifications/message` at debug, info, warning, error (≥1 each). |

## Feature area: sampling (FR-010) — 4 tools

| Tool | Behavior |
|---|---|
| `sampling_simple` | Minimal `sampling/createMessage` to client; returns the response. |
| `sampling_with_system` | Includes `systemPrompt`. |
| `sampling_max_tokens` | Includes `maxTokens`. |
| `sampling_unsupported` | When client lacks sampling capability → graceful `isError` result. |

Under `no-sampling`/`tools-only`/`minimal` profiles, sampling tools degrade gracefully.

## Feature area: inspect (FR-012) — 1 tool

| Tool | Result |
|---|---|
| `inspect_session` | `{protocolVersion, clientInfo:{name,version}, negotiatedCapabilities, transport, requestCount}`; `requestCount` increments across calls in a session. |
