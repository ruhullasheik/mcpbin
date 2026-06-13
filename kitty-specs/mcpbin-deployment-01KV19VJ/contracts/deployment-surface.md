# Contract: Live Deployment Surface

**Mission**: mcpbin-deployment-01KV19VJ

The hosted instance (HF Space base URL `https://<owner>-<space>.hf.space/`) must satisfy:

| Request | Expected |
|---|---|
| `GET /` | 200 · HTML app shell of the reference UI (contains the search box / `mcpbin` brand). |
| `GET /app.js`, `/style.css`, `/logo.svg` | 200 · the bundled static assets (served from packaged `mcpbin/frontend/`). |
| `POST /mcp` (JSON-RPC `initialize`, Accept `application/json, text/event-stream`) | A real MCP response — **not** 404/405. Subsequent `tools/list`, `tools/call`, `resources/list`, `prompts/list` work; tool results carry `_meta`. |
| UI behavior | Loads the full catalog via the relative `/mcp` fetch (root-served subdomain); tools grouped by feature area; search works; if `/mcp` is unreachable each section shows the inline error. |
| Profile | `full` (tools + resources + prompts + sampling + pagination). |
| Binding | container listens on `0.0.0.0:7860` (== Space `app_port`). |
| Cold start | first request after idle succeeds within ≤ 30 s (NFR-004). |

Out of scope: auth, custom domain, uptime guarantees.
