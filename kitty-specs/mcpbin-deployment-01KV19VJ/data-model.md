# Phase 1 Data Model: mcpbin Deployment

**Mission**: mcpbin-deployment-01KV19VJ · **Date**: 2026-06-13

No runtime data. "Entities" are the deploy/ops artifacts and their fields.

## Entity: Hugging Face Space

| Field | Value / rule |
|---|---|
| SDK | `docker` |
| `app_port` | `7860` (must equal the container's bind port) |
| files | Space `README.md` (front-matter + description) + Space `Dockerfile` |
| base URL | `https://<owner>-<space>.hf.space/` (UI at `/`, MCP at `/mcp`) |
| visibility | public |
| hardware | free CPU basic ($0) |

## Entity: Deployment image (Space Dockerfile)

| Field | Value / rule |
|---|---|
| base | `python:3.12-slim` |
| install | `pip install https://github.com/ruhullasheik/mcpbin/archive/refs/tags/${MCPBIN_REF}.tar.gz` |
| `MCPBIN_REF` | pinned release tag (e.g. `v0.1.0`); bump to redeploy |
| env | `FASTMCP_HOST=0.0.0.0`, `FASTMCP_PORT=7860` |
| command | `mcpbin --transport http` |
| invariant | running container serves the bundled frontend at `/` and MCP at `/mcp` |

## Entity: Release workflow (`.github/workflows/release.yml`)

| Field | Value / rule |
|---|---|
| trigger | `push` of tags matching `v*` |
| permissions | `contents: write` (built-in `GITHUB_TOKEN` only; no external secrets) |
| gate | `uv run pytest -q` passes **before** publishing |
| build | `uv build` → wheel + sdist |
| assertion | wheel must contain `mcpbin/frontend/index.html` else fail |
| output | wheel + sdist attached to the tag's GitHub Release (idempotent / `--clobber`) |

## Entity: Release artifacts

| Field | Rule |
|---|---|
| wheel | `mcpbin-<ver>-py3-none-any.whl`, **bundles `mcpbin/frontend/`** |
| sdist | `mcpbin-<ver>.tar.gz` |
| location | attached to the GitHub Release for the triggering tag |

## Entity: Live URL

| Field | Rule |
|---|---|
| value | the Space base URL; MCP endpoint = base + `/mcp` |
| advertised in | project `README.md` "Live demo" section + a one-line connect instruction |

## Entity: Smoke check (`scripts/smoke_check.py`)

| Field | Rule |
|---|---|
| input | base URL (arg/env), optional retry budget |
| check 1 | `GET /` → 200 + body contains app shell marker |
| check 2 | `POST /mcp` initialize → MCP response (status 200, not 404/405) |
| cold start | retries with backoff up to ~30 s |
| exit | `0` on all-pass, non-zero otherwise; stdlib-only |

## Relationships

- The **Space** runs the **deployment image**, which installs the artifact built for the
  pinned **release tag**; the **release workflow** guarantees that tag's **artifacts** are
  correct (frontend-bundled). The **smoke check** validates the resulting **live URL**, which
  the README advertises.
