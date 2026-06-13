# WP03 Review — Cycle 1 (Changes Requested)

Strong implementation overall: capability gating, pagination wiring, ctx assembly,
in-memory fixtures, CLI, and stderr logging are all correct and well-tested (60 tests
pass). One blocking correctness defect on the HTTP transport surface must be fixed
before approval, because it is part of the foundational contract that WP14 (frontend)
and WP15 (integration) depend on.

## Issue 1 (BLOCKING) — HTTP MCP endpoint is served at `/mcp/mcp`, not `/mcp`

`_build_http_app()` (src/mcpbin/server.py, ~line 346) builds the MCP ASGI app with an
internal route already at `/mcp`:

```python
mcp_app = app.http_app(path="/mcp", transport="http")
...
parent = Starlette(routes=[
    Mount("/mcp", app=mcp_app),          # <-- mounts the /mcp-rooted app under /mcp
    Mount("/", app=StaticFiles(...)),
], lifespan=mcp_app.lifespan)
```

Mounting an app whose internal route is `/mcp` under `Mount("/mcp", ...)`
double-prefixes the path. Verified by ASGI probe with `frontend/` present:

```
POST /mcp      -> 405   (handled by the StaticFiles "/" mount, NOT the MCP endpoint)
POST /mcp/mcp  -> 400   (the real MCP endpoint: route matched + request validated)
GET  /         -> 200   (frontend served correctly)
```

So the contract `MCP at /mcp` (contracts/protocol.md "Transports", DoD: "HTTP transport
serves `/` (frontend) and `/mcp`") is violated whenever the frontend is present.

This is currently latent only because `frontend/` does not exist yet: with no frontend,
`_build_http_app` takes the early-return branch and returns `mcp_app` directly (which
does serve `/mcp`). The bug activates the moment WP14 lands `frontend/`, and WP15's
integration test asserts pagination/`/mcp` against the real catalog — so it must be
correct now while this is the stable server contract.

**Fix** (one line): root the MCP app at `/` and let the mount supply the `/mcp` prefix:

```python
mcp_app = app.http_app(path="/", transport="http")
parent = Starlette(routes=[
    Mount("/mcp", app=mcp_app),
    Mount("/", app=StaticFiles(directory=str(frontend), html=True)),
], lifespan=mcp_app.lifespan)
```

(Equivalent alternative: keep `path="/mcp"` and mount `mcp_app` at `/`, but that
collides with the StaticFiles `/` mount, so prefer the form above.)

**Also add a regression test** so the HTTP path stops being untested. A minimal test
that creates a temporary `frontend/index.html`, builds the parent app via
`_build_http_app`, and asserts (via `httpx.ASGITransport` + the app lifespan) that
`POST /mcp` reaches the MCP endpoint (not StaticFiles) and `GET /` serves the frontend
would have caught this. The current suite never exercises `_build_http_app` with a
frontend present, which is exactly how this slipped through.

## Non-blocking note (no action required, just confirm intent)

- `minimal` profile still paginates `tools/list` at page size 10 even though
  `Profile.pagination is False`. This is CORRECT per FR-008 (pagination applies
  universally to all present list methods) and data-model.md (the `pagination/listChanged`
  column's "✗" for minimal is annotated "no `listChanged`"). The `Profile.pagination`
  flag is effectively only used for logging — acceptable, and a WP02 concern anyway.
- The documented fastmcp stdio quirk (`run_stdio_async` hardcodes
  `tools_changed=True`) does not affect the observable contract (in-memory client +
  HTTP honour the configured `notification_options`). Accepted as documented.
