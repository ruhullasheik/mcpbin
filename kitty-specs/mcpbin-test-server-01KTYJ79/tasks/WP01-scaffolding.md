---
work_package_id: WP01
title: Project scaffolding & packaging
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- C-006
- C-007
- C-008
- NFR-005
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning/base branch devs/ruhulla; completed work merges into devs/ruhulla. Execution worktree is allocated per computed lane from lanes.json.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: pyproject.toml
execution_mode: code_change
owned_files:
- pyproject.toml
- .python-version
- Dockerfile
- .dockerignore
- src/mcpbin/__init__.py
- uv.lock
tags: []
---

# WP01 — Project scaffolding & packaging

## Objective

Stand up the `uv`-managed Python 3.12 package skeleton for mcpbin so that every later
work package has a place to add code, the package imports cleanly, and a Docker image can
be built. No MCP behavior yet — just the scaffold and packaging metadata.

## Context

- Plan: [../plan.md](../plan.md) — see "Source Code" tree and Technical Context.
- Constraints: Python 3.12+ (C-001), `uv` exclusively (C-002), FastMCP is the **only**
  third-party runtime dependency (C-003), PRD layout + entry point `mcpbin` →
  `mcpbin.server:main` (C-006), build-ready-not-published distribution (C-007), commit
  `uv.lock` + `.python-version` (C-008).
- This WP creates `src/mcpbin/__init__.py` only. `server.py` and all other modules are
  created by later WPs; do **not** create them here.

## Implement command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Subtasks

### T001 — `pyproject.toml`
- Build backend: `hatchling`.
- `[project]`: name `mcpbin`, version (dynamic or `0.1.0`), `requires-python = ">=3.12"`,
  description, license, README reference.
- `dependencies = ["fastmcp"]` — pin a concrete minimum once resolved (T005). **No other
  runtime deps** (C-003).
- Optional dev group (`[dependency-groups]` or `[project.optional-dependencies] dev`):
  `pytest`, `pytest-asyncio` (delay/sampling tests are async). Dev deps are allowed; they
  are not runtime deps, so C-003 holds.
- `[project.scripts]`: `mcpbin = "mcpbin.server:main"` (C-006). This references a module that
  doesn't exist yet — that's fine; it's only invoked after WP03.
- Package discovery: `src/` layout (`[tool.hatch.build.targets.wheel] packages = ["src/mcpbin"]`).
- **Package data**: ensure `frontend/` and `src/mcpbin/assets/` ship in the wheel
  (`[tool.hatch.build] include` / `force-include` for `frontend/`). The frontend lives at
  repo root, so map it into the package or document its runtime path — note this for WP03/WP14.

### T002 — `.python-version`
- Pin a concrete `3.12.x` (e.g. `3.12`). Committed (C-008).

### T003 — `src/mcpbin/__init__.py`
- Expose `__version__` (string, matching pyproject). Keep minimal — no imports of submodules
  that don't exist yet (avoid import errors before WP02/03 land).

### T004 — `Dockerfile` + `.dockerignore`
- Multi-stage or single-stage image using a `uv` base (e.g. `ghcr.io/astral-sh/uv:python3.12-...`).
- Copy project, `uv sync --frozen`, set entrypoint to `mcpbin`. Default `CMD` should run an
  HTTP transport so the container is reachable (e.g. `["--transport", "http"]`). The image
  must **build**; it is not published (C-007).
- `.dockerignore`: exclude `.git`, `.venv`, `.worktrees`, `kitty-specs`, `__pycache__`, etc.

### T005 — Generate `uv.lock`
- Run `uv lock` (or `uv sync`) to produce a committed `uv.lock` (C-008). Verify it resolves
  `fastmcp` + dev deps on Python 3.12.

### T006 — Import smoke check
- `uv run python -c "import mcpbin; print(mcpbin.__version__)"` succeeds.

## Branch Strategy

Planning/base branch: **devs/ruhulla**. Final merge target: **devs/ruhulla**. Execution
worktrees are allocated per computed lane from `lanes.json` during implement; do not create
branches manually.

## Definition of Done

- [ ] `uv sync` succeeds from a clean checkout; `uv.lock` and `.python-version` committed.
- [ ] `uv run python -c "import mcpbin"` works (NFR-005 single-command spirit).
- [ ] `docker build -t mcpbin:dev .` succeeds (C-007).
- [ ] Only `fastmcp` is a runtime dependency (C-003); dev deps isolated.
- [ ] `pyproject.toml` declares the `mcpbin` entry point (C-006) and ships `frontend/` +
      `assets/` as package data.
- [ ] No files outside `owned_files` are modified.

## Risks & reviewer guidance

- **Package-data for `frontend/`**: it lives at repo root, not under `src/mcpbin/`. Reviewer:
  confirm the chosen include strategy actually puts the frontend into the wheel, or that WP03
  resolves it via a documented filesystem path. Flag the chosen approach for WP14.
- **FastMCP version**: pin the resolved version range so later WPs build against a known API
  (this is the anchor for the research.md "verify-on-impl" items).
- Don't scaffold empty placeholder modules for later WPs — it would collide with their
  ownership.
