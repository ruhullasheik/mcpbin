---
work_package_id: WP01
title: Release automation (CI)
dependencies: []
requirement_refs:
- C-002
- C-006
- FR-005
- FR-006
- NFR-003
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-deployment-01KV19VJ
base_commit: 17c0b491a6d6dbd0b14d46a10b1cd14f5f52e252
created_at: '2026-06-13T20:24:12.343334+00:00'
subtasks:
- T001
- T002
- T003
shell_pid: '22516'
history:
- date: '2026-06-13'
  author: tasks
  action: created
authoritative_surface: .github/workflows/release.yml
execution_mode: code_change
owned_files:
- .github/workflows/release.yml
tags: []
---

# WP01 — Release automation (CI)

## Objective

Add a GitHub Actions workflow so that pushing a `v*` tag automatically builds, gates, and
attaches a **correct, frontend-bundled** wheel + sdist to that tag's GitHub Release — making
the v0.1.0 "wheel shipped without the UI / had to re-upload by hand" problem impossible to
recur.

## Context
- Plan: [../plan.md](../plan.md). Contract: [../contracts/release-workflow.md](../contracts/release-workflow.md).
- Research R3 (release-on-tag) + R4 (bundled assertion + test gate) in [../research.md](../research.md).
- Builds on the existing `pyproject.toml`/`uv.lock`/`hatch_build.py`; no app code change.

## Implement command
```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Scope — ONLY this owned file
- `.github/workflows/release.yml`

## Subtasks

### T001 — Workflow skeleton
- `name: release`; `on: push: { tags: ['v*'] }` (optionally add `workflow_dispatch:` for manual re-runs).
- `permissions: { contents: write }` (needed for the Release; uses built-in `GITHUB_TOKEN` only — no external secrets, C-006/NFR-005).
- Single job on `ubuntu-latest`: `actions/checkout@v4`, then install uv via `astral-sh/setup-uv@v6` pinned to Python 3.12, then `uv sync --frozen`.

### T002 — Gate, build, assert
- **Gate:** `uv run pytest -q` — the job must fail here if tests fail, before any publish (FR-006).
- **Build:** `uv build` → `dist/*.whl` + `dist/*.tar.gz`.
- **Assert frontend bundled (NFR-003):** fail the job if the wheel lacks `mcpbin/frontend/`:
  ```bash
  python - <<'PY'
  import glob, sys, zipfile
  whl = glob.glob("dist/*.whl")[0]
  names = zipfile.ZipFile(whl).namelist()
  ok = any(n.startswith("mcpbin/frontend/") and n.endswith("index.html") for n in names)
  sys.exit(0 if ok else "FAIL: wheel does not bundle mcpbin/frontend/")
  PY
  ```

### T003 — Publish (idempotent)
- Attach `dist/*` to the Release for the triggering tag using `gh` (preinstalled on runners),
  authenticated via `GITHUB_TOKEN`. Make it idempotent so re-runs/re-tags replace cleanly:
  ```bash
  TAG="${GITHUB_REF_NAME}"
  if gh release view "$TAG" >/dev/null 2>&1; then
    gh release upload "$TAG" dist/* --clobber
  else
    gh release create "$TAG" dist/* --generate-notes
  fi
  ```
  with `env: { GH_TOKEN: ${{ secrets.GITHUB_TOKEN }} }`.
- Do **not** publish to PyPI (out of scope, C-002).

## Branch Strategy
Planning/base **main**; merge target **main**; worktree per lane from `lanes.json`.

## Definition of Done
- [ ] Workflow triggers only on `v*` tags; declares `contents: write`; no external secrets.
- [ ] Tests run and gate the build; `uv build` produces wheel + sdist.
- [ ] The bundled-frontend assertion fails the job when `mcpbin/frontend/` is absent.
- [ ] Publish step is idempotent (create-or-clobber) and uses `GITHUB_TOKEN`.
- [ ] No tokens/secrets echoed in logs; no files outside `owned_files` modified.

## Risks & reviewer guidance
- **verify-on-impl (R3):** confirm the create-vs-upload guard works (a brand-new tag has no
  release yet → create; re-run → upload --clobber). Reviewer: read the YAML and confirm the
  trigger is tags-only (not every push) and permissions are minimal.
- Pin action versions. Keep `GITHUB_TOKEN` usage; never add a PAT.
- Can't fully run Actions locally; review by inspection + (optionally) `act`/a throwaway tag
  on a fork. Note the verification method in the PR.
