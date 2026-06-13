# Implementation Plan: mcpbin Free Public Deployment

**Branch**: `main` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/mcpbin-deployment-01KV19VJ/spec.md`

## Summary

Ship the artifacts and automation that make mcpbin a free, public, hosted demo and keep
releases honest: a **Hugging Face Docker Space** (UI at `/`, MCP at `/mcp`), a **GitHub
Actions release workflow** that builds and attaches a correct, frontend-bundled wheel +
sdist on every `v*` tag, a **live smoke-check** script, and **README/docs** advertising the
live URL. No application code changes — this builds on the already-fixed root `Dockerfile`,
the `hatch_build.py` frontend-bundling fix, and the drafted `deploy/huggingface/` assets.
The only manual, human-gated step is the one-time Space creation (needs the maintainer's
Hugging Face account, C-005).

## Technical Context

**Language/Version**: No app code change (Python 3.12 package already built); deploy assets
are a Dockerfile, a GitHub Actions YAML workflow, a shell/Python smoke script, and Markdown
**Primary Dependencies**: Hugging Face Spaces (Docker SDK), GitHub Actions; runtime image
installs the published mcpbin (FastMCP only) — no new runtime deps (C-004)
**Storage**: None (stateless demo; in-memory session store inherited)
**Testing**: existing `uv run pytest` (171 tests) as the CI gate + a packaged-wheel
frontend-bundled assertion; a live smoke check (UI 200 + `/mcp` initialize) post-deploy
**Target Platform**: Hugging Face Docker Space (Linux container), free CPU tier (C-001)
**Project Type**: single project + ops/deploy assets (no new source tree)
**Performance Goals**: not a perf effort; cold-start ≤ 30 s after sleep (NFR-004)
**Constraints**: $0 cost (NFR-001); reproducible from a pinned tag (NFR-002); correct
release artifacts every time (NFR-003); no secrets in repo/logs, CI uses only `GITHUB_TOKEN`
(NFR-005, C-006); `full` profile over Streamable HTTP (C-003); reuse fixed Dockerfile/assets,
no regressions (C-007)
**Scale/Scope**: one public demo instance; one release workflow; low traffic

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**SKIPPED** — no charter (`spec-kitty charter context --action plan` → `mode: missing`). No
governance gates to evaluate. If a charter is added later, re-run this gate.

## Project Structure

### Documentation (this feature)

```
kitty-specs/mcpbin-deployment-01KV19VJ/
├── plan.md              # This file
├── research.md          # Phase 0 — HF Space subpath/proxy, GH release action, CI bundled-check, cold start
├── data-model.md        # Phase 1 — entities: Space config, deploy image, workflow, artifacts, live URL, smoke check
├── quickstart.md        # Phase 1 — maintainer runbook: create Space → deploy → get URL → verify
├── contracts/           # Phase 1 — deployment-surface, release-workflow, smoke-check contracts
│   ├── deployment-surface.md
│   ├── release-workflow.md
│   └── smoke-check.md
└── tasks/               # Phase 2 (/spec-kitty.tasks) — NOT created here
```

### Repository changes (target files)

```
mcpbin/
├── .github/
│   └── workflows/
│       └── release.yml          # NEW — on v* tag: checkout, uv sync, pytest gate, uv build,
│                                 #       assert wheel bundles mcpbin/frontend, gh release upload
├── deploy/
│   └── huggingface/
│       ├── README.md            # EXISTS — HF Space front-matter (app_port 7860); refine if needed
│       ├── Dockerfile           # EXISTS — self-contained Space image (pinned tag); refine if needed
│       └── SETUP.md             # EXISTS — maintainer runbook; align with quickstart
├── scripts/
│   └── smoke_check.py           # NEW — verify a live base URL: GET / == 200 + app shell;
│                                 #       POST /mcp initialize reaches MCP (not 404/405)
├── Dockerfile                   # EXISTS (fixed) — generic container deploy; do not regress
└── README.md                    # EDIT — add "Live demo" section with URL + connect line
```

**Structure Decision**: Deploy/ops assets live outside `src/` (in `.github/`, `deploy/`,
`scripts/`) so the Python package is untouched (C-004). The HF Space is self-contained
(installs a pinned mcpbin tag) per `deploy/huggingface/`; the release workflow guarantees the
pinned tag's artifacts are correct (closing the v0.1.0 stale-artifact gap). The smoke check is
a standalone script usable locally and in the maintainer runbook.

## Complexity Tracking

*No Charter Check violations (charter skipped). Table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0 — Research (see research.md)

1. **HF Space serving model** — how a Docker Space exposes the container (single `app_port`,
   base-path/proxy behavior) and whether the UI's relative `/mcp` fetch works behind it
   (FR-001, FR-002, scenario 1/2).
2. **Reproducible install in the Space image** — installing a pinned tag's source so the
   frontend is bundled (vs the broken release wheel); git vs source-archive (FR-003, NFR-002).
3. **Release-on-tag workflow** — trigger (`push: tags: v*`), permissions (`contents: write`
   via `GITHUB_TOKEN`), build (`uv build`), and upload-to-release mechanism (FR-005, C-006).
4. **CI "frontend bundled" assertion** — how to fail the workflow if the built wheel lacks
   `mcpbin/frontend/` (NFR-003) and how to gate on the test suite (FR-006).
5. **Live smoke check** — minimal, dependency-light way to assert UI 200 + `/mcp` initialize,
   tolerant of cold start (FR-007, NFR-004).
6. **Cost & cold-start facts** — confirm $0 free-tier path and the sleep/wake window to
   document (NFR-001, NFR-004, FR-009).

## Phase 1 — Design & Contracts (see data-model.md, contracts/, quickstart.md)

- `data-model.md` — the deploy entities and their fields/relationships.
- `contracts/deployment-surface.md` — required URL behaviors of the live instance.
- `contracts/release-workflow.md` — the workflow's trigger, gates, and outputs.
- `contracts/smoke-check.md` — inputs/exit-codes/assertions of the verification.
- `quickstart.md` — the end-to-end maintainer runbook (create → deploy → verify).

## ⛔ Stop point

This plan ends after Phase 1 artifacts. Work-package breakdown is the next phase —
run `/spec-kitty.tasks` explicitly.
