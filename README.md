<p align="center">
  <img src="frontend/logo.svg" alt="mcpbin logo" width="96" height="96" />
</p>

<h1 align="center">mcpbin</h1>

<p align="center"><em>Like <a href="https://httpbin.org">httpbin</a> for REST APIs — a test server for exercising Model Context Protocol (MCP) clients.</em></p>

---

Just as **httpbin** gives REST/HTTP client developers a predictable server to test against,
**mcpbin** gives **MCP client developers** a deterministic, self-hostable MCP server to test
against. Point your client at mcpbin to verify protocol compliance, validate error handling,
and explore edge cases without building throwaway servers. Every tool, resource, and prompt
has a documented, reproducible response, and every tool result carries a `_meta` block
explaining what the server received and why the response looks the way it does.

Built on [FastMCP](https://github.com/jlowin/fastmcp); targets MCP spec **2025-03-26**.

## Live demo

A hosted instance runs on a free [Hugging Face Space](https://huggingface.co/spaces/ruhullasheik/mcpbin):

- **Web UI:** https://ruhullasheik-mcpbin.hf.space/
- **MCP endpoint:** connect your MCP client to `https://ruhullasheik-mcpbin.hf.space/mcp` (Streamable HTTP).

> The free Space **sleeps when idle** and wakes on the next request, so the first hit after a
> while can take up to ~30 s. It serves the **`full`** profile.

Want your own instance? See [`deploy/huggingface/SETUP.md`](deploy/huggingface/SETUP.md) for the
one-time setup runbook.

## Quick start

```bash
uv sync                         # install (FastMCP is the only runtime dependency)
uv run mcpbin                   # stdio transport, full profile (defaults)
uv run mcpbin --transport http  # Streamable HTTP: UI at http://localhost:8000/ , MCP at /mcp
uv run mcpbin --transport sse   # HTTP + SSE
uv run mcpbin --profile tools-only   # capability-gated profile
```

CLI flags:

- `--transport {stdio,sse,http}` — default `stdio`.
- `--profile {full,tools-only,no-sampling,minimal}` — default `full`.

Structured logs go to **stderr** so you can watch server-side behavior next to your
client.

## Capability profiles

| Profile | Advertises | Omitted list methods |
|---|---|---|
| `full` (default) | tools, resources, prompts, sampling, pagination, listChanged | — |
| `tools-only` | tools | `resources/list`, `prompts/list` → `-32601` |
| `no-sampling` | tools, resources, prompts, pagination | sampling tools degrade gracefully |
| `minimal` | tools (no `listChanged`) | `resources/list`, `prompts/list` → `-32601` |

## Reference UI

With an HTTP transport, open `http://localhost:8000/` for a static, framework-free UI that
fetches the live catalog from `/mcp` and documents every tool (grouped by feature area),
resource, and prompt. It is documentation-only — there is no "run this tool" button. If
`/mcp` is unreachable each section shows `Could not reach MCP server at /mcp`.

## Test checklist

A compliant MCP client should be able to make all of these calls against the `full`
profile over stdio:

### Echo (FR-001)
- [ ] `echo`, `echo_string`, `echo_number`, `echo_boolean`, `echo_object`, `echo_array`,
  `echo_all_types` return their input unchanged with a valid `_meta`.

### Response types (FR-002)
- [ ] `return_text` / `return_image` (decodable base64 PNG, `image/png`) /
  `return_resource` / `return_multiple` (≥3 content types) / `return_empty`
  (`content: []`) / `return_isError` (`isError: true`).

### Errors (FR-003)
- [ ] `error_invalid_request` (-32600), `error_method_not_found` (-32601),
  `error_invalid_params` (-32602), `error_internal` (-32603) raise coded protocol errors.
- [ ] `error_parse` returns a simulated -32700 JSON-RPC object as text (with a `_meta` note).
- [ ] `error_tool_level` returns `isError: true` (not a protocol error).
- [ ] `error_unknown_code` uses a code outside -32700..-32603.

### Delays (FR-004)
- [ ] `delay {seconds: 2}` responds in ~2s; `seconds > 30` clamps to 30.
- [ ] `delay_1s` / `delay_5s` / `delay_30s` respond after their fixed delay.
- [ ] `delay_cancel` returns `isError` + `"cancelled by client"` when sent
  `notifications/cancelled`, else a normal result.

### Schema (FR-005)
- [ ] `schema_required_fields` errors when a required field is missing;
  `schema_optional_fields` succeeds when optionals omitted; `schema_enum` errors off-enum;
  `schema_nested` / `schema_array_items` round-trip; `schema_no_args` succeeds with no args.

### Resources (FR-006)
- [ ] `resources/list` returns 100+ resources (multiple cursor pages) including
  `mcpbin://missing`.
- [ ] Read `mcpbin://text/plain`, `mcpbin://text/markdown`, `mcpbin://blob/binary`.
- [ ] `mcpbin://dynamic/{alpha,beta,gamma}` return distinct text; any other id and
  `mcpbin://missing` return not-found.

### Prompts (FR-007)
- [ ] `prompts/list`; `simple` (single user message), `with_args` (required+optional),
  `multi_turn` (alternating roles), `with_embedded_resource` (embedded resource block),
  `no_description` (no description field).

### Pagination (FR-008)
- [ ] `tools/list` and `resources/list` require multiple opaque-cursor pages; the final
  page omits `nextCursor`; an invalid cursor returns `-32602 "invalid or expired cursor"`.

### Notifications (FR-009)
- [ ] `notify_resource_updated`, `notify_resource_list_changed`,
  `notify_prompt_list_changed`, `notify_tool_list_changed`; `notify_progress` (≥3 progress
  notifications); `notify_log` (debug/info/warning/error).

### Sampling (FR-010)
- [ ] `sampling_simple` / `sampling_with_system` (systemPrompt) / `sampling_max_tokens`
  (maxTokens) issue `sampling/createMessage`; `sampling_unsupported` degrades gracefully
  when the client lacks sampling.

### Profiles & inspection (FR-011, FR-012)
- [ ] Each profile advertises the documented capabilities; omitted ones return `-32601`.
- [ ] `inspect_session` returns `protocolVersion`, `clientInfo`, `negotiatedCapabilities`,
  `transport`, and a `requestCount` that increments across calls.

## Catalog size

42 tools · 124 resources · 5 prompts — large enough that `tools/list` and
`resources/list` require multiple pages. (The PRD's "50+" was a target; the catalog uses
only real feature endpoints, no synthetic padding.)

## Docker

```bash
docker build -t mcpbin:dev .
docker run --rm -p 8000:8000 mcpbin:dev   # serves the UI + /mcp at http://localhost:8000
```

The image runs the Streamable HTTP transport bound to `0.0.0.0` and honors a platform-injected
`$PORT` (Cloud Run, Render, …), defaulting to `8000`.

## Development

```bash
uv run pytest        # full test suite (one module per feature area + cross-cutting checks)
```

The package is structured as a small FastMCP app (`src/mcpbin/`) with one module per
feature area under `tools/`, auto-discovered by `registry.py`; resources and prompts live
in `resources.py` / `prompts.py`; the static UI is in `frontend/`.

## Contributing

Contributions are welcome — bug fixes, new diagnostic tools/resources/prompts, docs, and UI
improvements. See [CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup and PR flow, and the
[Code of Conduct](CODE_OF_CONDUCT.md). CI runs the test suite on every pull request. To report
a security issue, see [SECURITY.md](SECURITY.md).
