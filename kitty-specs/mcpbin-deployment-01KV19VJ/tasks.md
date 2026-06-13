# Tasks: mcpbin Free Public Deployment

**Mission**: mcpbin-deployment-01KV19VJ · **Branch**: `main` · **Date**: 2026-06-13
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

## Overview

Three independent, parallelizable work packages — each owns a disjoint set of files, so all
can be implemented at once after none-blocking. No application code changes; this layers
deploy/ops assets on top of the already-fixed `Dockerfile` and `hatch_build.py`.

```
WP01 release CI         (.github/workflows/release.yml)
WP02 smoke check        (scripts/smoke_check.py)
WP03 HF Space + docs    (deploy/huggingface/*, README.md)
        — all independent (disjoint files); no dependency edges —
```

MVP = WP01 (correct release artifacts) + WP03 (deployable Space). WP02 hardens verification.

The one human-gated step (creating the HF Space with the maintainer's account) is **not** a
work package — it's the post-merge runbook in `quickstart.md` (C-005).

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Release workflow skeleton: `v*` tag trigger, `contents: write`, checkout, uv, Python 3.12 | WP01 | [P] | [D] |
| T002 | Test gate (`uv run pytest`) → `uv build` → assert wheel bundles `mcpbin/frontend/` | WP01 | | [D] |
| T003 | Publish: idempotent `gh release` create-or-upload of `dist/*` with `GITHUB_TOKEN` | WP01 | | [D] |
| T004 | `smoke_check.py`: stdlib CLI scaffold (base-url arg, timeout, exit codes) | WP02 | [D] |
| T005 | Check 1 `GET /` 200 + app shell; Check 2 `POST /mcp` initialize reaches MCP; cold-start retries | WP02 | | [D] |
| T006 | Local verification run against `uv run mcpbin --transport http` | WP02 | | [D] |
| T007 | Validate/refine HF Space `Dockerfile` (port 7860, FASTMCP env, pinned tag); confirm frontend bundles | WP03 | [D] |
| T008 | HF Space `README.md` front-matter (`app_port: 7860`) + align `SETUP.md` runbook | WP03 | | [D] |
| T009 | Root `README.md` "Live demo" section: URL placeholder + connect line + cold-start/profile note (FR-009) | WP03 | | [D] |

---

## Work Packages

### WP01 — Release automation (CI)
**Goal**: On every `v*` tag, automatically build + gate + attach correct, frontend-bundled
artifacts to the GitHub Release (close the v0.1.0 stale-artifact gap).
**Priority**: P0. **Independent test**: workflow lints; dry-run logic verified; a test tag
produces a Release with a wheel containing `mcpbin/frontend/`.
**Depends on**: none. **Prompt**: [tasks/WP01-release-ci.md](tasks/WP01-release-ci.md) (~180 lines)

- [x] T001 workflow skeleton (trigger/permissions/setup) (WP01)
- [x] T002 test gate + build + bundled assertion (WP01)
- [x] T003 idempotent gh release publish (WP01)

### WP02 — Live smoke check
**Goal**: A stdlib-only script that verifies a live base URL (UI 200 + `/mcp` initialize),
tolerant of cold start; usable locally and post-deploy.
**Priority**: P1. **Independent test**: `python scripts/smoke_check.py http://localhost:8000`
passes against a locally running server; exits non-zero on a dead URL.
**Depends on**: none. **Prompt**: [tasks/WP02-smoke-check.md](tasks/WP02-smoke-check.md) (~170 lines)

- [x] T004 CLI scaffold + exit codes (WP02)
- [x] T005 the two checks + cold-start retries (WP02)
- [x] T006 local verification run (WP02)

### WP03 — Hugging Face Space + live-demo docs
**Goal**: Finalize the deployable HF Docker Space assets and advertise the live demo in the
README; reproducible from a pinned tag with the frontend bundled.
**Priority**: P0. **Independent test**: `docker build -f deploy/huggingface/Dockerfile` (or a
documented equiv) yields a container that serves `/` (UI) and `/mcp` on port 7860; README has
a "Live demo" section.
**Depends on**: none. **Prompt**: [tasks/WP03-hf-space-docs.md](tasks/WP03-hf-space-docs.md) (~200 lines)

- [x] T007 validate/refine Space Dockerfile (WP03)
- [x] T008 Space README front-matter + SETUP alignment (WP03)
- [x] T009 root README "Live demo" section + cold-start/profile note (WP03)

---

## Parallelization
- All three WPs touch disjoint files → fully parallel. No dependency edges.
- Critical path is a single WP (any of them); WP15-style integration is unnecessary at this size.

## Notes
- Reuse the already-fixed root `Dockerfile` and existing `deploy/huggingface/` assets; do not
  regress the v0.1.0 startup/packaging fixes (C-007).
- Go-live (HF account + Space creation) is manual and lives in `quickstart.md`, not a WP (C-005).
