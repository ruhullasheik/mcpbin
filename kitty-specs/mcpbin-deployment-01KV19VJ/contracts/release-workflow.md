# Contract: Release Workflow

**Mission**: mcpbin-deployment-01KV19VJ · File: `.github/workflows/release.yml`

## Trigger
- `on: push:` with `tags: ['v*']`. (Optionally `workflow_dispatch` for manual re-runs.)

## Permissions
- `contents: write` — to create/update the GitHub Release. Uses the built-in `GITHUB_TOKEN`
  only; **no external secrets** (C-006, NFR-005).

## Job steps (ubuntu-latest)
1. `actions/checkout`.
2. Install uv (`astral-sh/setup-uv`), pinned Python 3.12.
3. `uv sync` (frozen).
4. **Gate:** `uv run pytest -q` — must pass or the job fails before any publish (FR-006).
5. `uv build` → `dist/*.whl` + `dist/*.tar.gz`.
6. **Assertion:** the wheel contains `mcpbin/frontend/index.html`, else fail (NFR-003).
7. Publish: attach `dist/*` to the Release for the triggering tag — create it if absent,
   else upload with `--clobber` (idempotent), via `gh`.

## Outputs / guarantees
- Every `v*` tag yields a GitHub Release whose wheel installs and **serves the UI**.
- Re-running the workflow for a tag replaces the artifacts cleanly (no manual fixups).
- No secrets are printed; logs contain no tokens.

## Non-goals
- No PyPI/TestPyPI upload (C-002). No Docker image push. No deploy to the Space (the Space
  rebuilds from its pinned tag independently).
