# Phase 0 Research: mcpbin Deployment

**Mission**: mcpbin-deployment-01KV19VJ · **Date**: 2026-06-13

Decisions resolving the Phase 0 unknowns. Items to confirm against the live platform during
implementation are marked **⚠ verify-on-impl**.

---

## R1. Hugging Face Docker Space serving model (FR-001, FR-002)

- **Decision**: Run as a **Docker SDK Space**. HF serves each Space on its **own subdomain**
  `https://<owner>-<space>.hf.space/` at the **domain root** (not a subpath) and routes all
  traffic to the single container port declared by `app_port` in the Space `README.md`
  front-matter. We set `app_port: 7860` and bind the container to `0.0.0.0:7860`
  (`FASTMCP_HOST`/`FASTMCP_PORT`). The UI's existing **relative** `fetch("/mcp")` therefore
  resolves to `https://<owner>-<space>.hf.space/mcp` — no code change, no base-path rewrite.
- **Rationale**: Relative paths + root-served subdomain means the UI and `/mcp` coexist with
  no origin/subpath juggling. mcpbin already serves `/` (static) and `/mcp` from one ASGI app.
- **Alternatives**: Gradio/Static SDK (rejected — not a custom ASGI server); reverse-proxy /
  subpath mount (rejected — unnecessary on a dedicated subdomain).
- **⚠ verify-on-impl**: confirm the live `.hf.space` subdomain serves at root (the embedded
  iframe preview on `huggingface.co/spaces/...` is a separate view; the canonical client URL
  is the `.hf.space` subdomain). Confirm HF doesn't inject a base path.

## R2. Reproducible install so the frontend ships (FR-003, NFR-002)

- **Decision**: The Space `Dockerfile` installs from the **GitHub source archive of a pinned
  tag**: `pip install https://github.com/ruhullasheik/mcpbin/archive/refs/tags/<TAG>.tar.gz`.
  Building from the source tree (top-level `frontend/` present) triggers the `hatch_build.py`
  hook, bundling `mcpbin/frontend/` into the wheel. `ARG MCPBIN_REF` pins the tag; bumping it
  redeploys.
- **Rationale**: Avoids the broken pre-fix release **wheel** (which lacked the frontend), needs
  no git in the image, and is fully reproducible from an immutable tag.
- **Alternatives**: install the release wheel URL (rejected — historical wheels may lack the
  frontend; the source-archive path always rebuilds correctly); `pip install git+…` (works but
  needs `git` in the image — heavier).
- **Status**: already implemented in `deploy/huggingface/Dockerfile`; this mission validates +
  refines it.

## R3. Release-on-tag GitHub Actions workflow (FR-005, C-006)

- **Decision**: `.github/workflows/release.yml` triggered by `on: push: tags: ['v*']`, with
  `permissions: contents: write`. Steps: `actions/checkout` → install uv (`astral-sh/setup-uv`)
  → `uv sync` → **gate** (`uv run pytest -q`) → `uv build` → **bundled assertion** (R4) →
  `gh release create <tag> dist/* --generate-notes` *or* `gh release upload <tag> dist/* --clobber`
  if the release already exists. Auth uses the built-in `GITHUB_TOKEN` (no external secrets).
- **Rationale**: `gh` is preinstalled on GitHub-hosted runners and `--clobber` makes re-runs
  idempotent (so a re-tag or re-run replaces artifacts cleanly — directly fixes the v0.1.0
  manual re-upload pain). `contents: write` is the only elevated permission needed.
- **Alternatives**: `softprops/action-gh-release` (fine; third-party action — `gh` keeps it
  dependency-free); Trusted-Publisher/PyPI (explicitly out of scope, C-002).
- **⚠ verify-on-impl**: exact idempotent path (create-if-missing-else-upload) — a small shell
  guard around `gh release view`.

## R4. CI "frontend bundled" assertion + test gate (FR-006, NFR-003)

- **Decision**: After `uv build`, run a stdlib check that the wheel contains
  `mcpbin/frontend/index.html` and fail the job otherwise:
  `python -c "import zipfile,glob,sys; w=glob.glob('dist/*.whl')[0]; names=zipfile.ZipFile(w).namelist(); sys.exit(0 if any(n.startswith('mcpbin/frontend/') for n in names) else 'frontend missing from wheel')"`.
  The test suite (`uv run pytest -q`) runs **before** build as the correctness gate.
- **Rationale**: NFR-003 demands every tagged release carry a UI-bearing wheel; this makes the
  regression impossible to ship silently.
- **Alternatives**: trust the build (rejected — the v0.1.0 wheel proved that fails); install
  the wheel and probe `_resolve_frontend_dir` (heavier; the zip check is sufficient).

## R5. Live smoke check (FR-007, NFR-004)

- **Decision**: `scripts/smoke_check.py`, **stdlib-only** (`urllib`), takes a base URL and:
  (a) `GET /` → expect HTTP 200 whose body contains the app shell marker (e.g. `id="search"`
  / `mcpbin`); (b) `POST /mcp` with a JSON-RPC `initialize` (Accept `application/json,
  text/event-stream`) → expect a real MCP response (status 200, **not** 404/405). Retries with
  backoff for up to ~30 s to absorb cold start; exits non-zero on failure. Usable locally
  (against `http://localhost:8000`) and against the live `.hf.space` URL.
- **Rationale**: Dependency-light (no extra installs), doubles as the FR-007 acceptance gate
  and the maintainer's post-deploy check; cold-start tolerance satisfies NFR-004.
- **Alternatives**: full FastMCP `Client` round-trip (richer but adds deps/complexity for a
  smoke check — the raw `initialize` POST is enough to prove the endpoint is live).

## R6. Cost & cold-start facts (NFR-001, NFR-004, FR-009)

- **Decision/Finding**: HF **free CPU basic** Spaces and **GitHub Actions on a public repo**
  are **$0**. Free Spaces **sleep after a period of inactivity** and **wake on the next
  request** (a cold start of seconds); document "first hit after idle may take up to ~30 s,
  then it's responsive," plus that the public instance serves the `full` profile.
- **⚠ verify-on-impl**: current free-tier sleep timing/labels change on HF; confirm the exact
  wording/threshold at deploy time and reflect it in `FR-009` docs.

---

## Summary

| # | Area | Decision | Verify-on-impl |
|---|---|---|---|
| R1 | HF serving | Docker Space, `app_port: 7860`, root subdomain, relative `/mcp` works | subdomain serves at root |
| R2 | Install | pip from pinned tag source archive → frontend bundled | — (implemented) |
| R3 | Release CI | `v*` tag → pytest gate → `uv build` → `gh release` w/ `GITHUB_TOKEN`, idempotent | create-vs-upload guard |
| R4 | CI assert | fail if wheel lacks `mcpbin/frontend/` | — |
| R5 | Smoke | stdlib `urllib` script: `/`==200 + `/mcp` initialize, cold-start retries | — |
| R6 | Cost/cold | $0 free tier; sleeps + wakes ~≤30 s; document | exact HF sleep wording |
