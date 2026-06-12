# Quickstart: mcpbin

**Mission**: mcpbin-test-server-01KTYJ79

This doubles as the seed for the README "test checklist" (FR-017). It walks the 13
acceptance scenarios from `spec.md`.

## Run locally

```bash
# Prereqs: uv installed; Python 3.12+ resolved by uv from .python-version
uv sync                          # install fastmcp + dev deps from uv.lock
uv run mcpbin                     # stdio transport, full profile (defaults)
uv run mcpbin --transport http    # Streamable HTTP; UI at http://localhost:<port>/ , MCP at /mcp
uv run mcpbin --transport sse      # HTTP + SSE
uv run mcpbin --profile tools-only # capability-gated profile
```

## Verify (maps to acceptance scenarios)

Use any MCP client (or `pytest` in-memory client) connected over stdio, `full` profile:

1. **Echo** — call `echo` with mixed args → all returned unchanged; `_meta.tool == "echo"`,
   `_meta.received` equals the sent args. (Scenario 1, FR-001, FR-013)
2. **Content types** — call each `return_*` → text/image/resource/multiple/empty + an
   `isError` result; image base64 decodes to a PNG. (Scenario 2, FR-002)
3. **Errors** — call each `error_*` → documented codes; `error_tool_level` is `isError`
   (not a protocol error); `error_unknown_code` is outside `-32700…-32603`. (Scenario 3, FR-003)
4. **Delays/cancel** — `delay {seconds:2}` ≈2 s; `delay {seconds:99}` clamps to 30 s; send
   `notifications/cancelled` to `delay_cancel` → `isError`, `"cancelled by client"` within 1 s.
   (Scenario 4, FR-004, NFR-002/003)
5. **Schema** — `schema_required_fields` errors on missing field; `schema_enum` errors off-enum;
   `schema_no_args` ok with no args; nested/array round-trip. (Scenario 5, FR-005)
6. **Resources** — `resources/list` includes the template + `mcpbin://missing`; read
   text/markdown/blob; `dynamic/alpha|beta|gamma` distinct; unknown id + `missing` → not-found.
   (Scenario 6, FR-006)
7. **Prompts** — `prompts/list`; `simple` single user msg; `with_args` includes args;
   `multi_turn` alternates; `with_embedded_resource` has a resource block; `no_description`
   has no description. (Scenario 7, FR-007)
8. **Pagination** — list tools/resources/prompts → multiple opaque-cursor pages; final page
   has no `nextCursor`; a bad cursor → `-32602` `"invalid or expired cursor"`. (Scenario 8, FR-008)
9. **Notifications** — call each `notify_*` → matching notifications; `notify_progress` ≥3;
   `notify_log` hits all four levels. (Scenario 9, FR-009)
10. **Sampling** — `sampling_*` issue `createMessage` (with systemPrompt / maxTokens where
    named); without sampling capability `sampling_unsupported` degrades gracefully. (Scenario 10, FR-010)
11. **Profiles** — start each profile; omitted-capability list methods return `-32601`;
    `minimal` advertises no `listChanged`. (Scenario 11, FR-011)
12. **Inspect** — `inspect_session` returns the five fields; `requestCount` increments across
    calls. (Scenario 12, FR-012)
13. **UI** — open `/` over HTTP → catalog grouped by feature area, resources/prompts follow all
    cursors; stop `/mcp` → each section shows the single inline error, no JS exception; works
    offline after first load. (Scenario 13, FR-015, NFR-004)

## Build the Docker image (build-ready, not published — C-007)

```bash
docker build -t mcpbin:dev .
docker run --rm -p 8000:8000 mcpbin:dev --transport http
```

## Run tests

```bash
uv run pytest          # one module per feature area + test_meta_contract.py
```

**Done** when every checklist item passes on the `full` profile over stdio (SC-001, SC-002).
