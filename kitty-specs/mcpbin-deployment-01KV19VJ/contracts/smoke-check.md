# Contract: Smoke Check

**Mission**: mcpbin-deployment-01KV19VJ · File: `scripts/smoke_check.py`

## Invocation
```
python scripts/smoke_check.py <base-url>          # e.g. https://<owner>-mcpbin.hf.space
python scripts/smoke_check.py http://localhost:8000
```
- Optional: `--timeout <s>` (default ~30) for cold-start retry budget.
- **Stdlib only** (`urllib`) — no extra installs; runs anywhere Python 3.12 is present.

## Assertions
| # | Check | Pass condition |
|---|---|---|
| 1 | `GET <base>/` | HTTP 200 and body contains the app shell marker (`id="search"` or `mcpbin`). |
| 2 | `POST <base>/mcp` JSON-RPC `initialize` (Accept `application/json, text/event-stream`) | Response is a real MCP reply — status 200 and **not** 404/405; body parses as JSON-RPC / SSE with a `result` (or a valid MCP error), proving the endpoint is live. |

## Behavior
- Retries checks with backoff until they pass or the timeout elapses (absorbs cold start).
- Prints a concise PASS/FAIL line per check.
- Exit code `0` only if **both** checks pass; non-zero otherwise (usable as a CI/gate step).

## Used by
- FR-007 acceptance; the maintainer runbook's final "verify" step (quickstart.md).
