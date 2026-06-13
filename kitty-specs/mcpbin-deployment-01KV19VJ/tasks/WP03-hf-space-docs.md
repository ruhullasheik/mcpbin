---
work_package_id: WP03
title: Hugging Face Space + live-demo docs
dependencies: []
requirement_refs:
- C-001
- C-003
- C-004
- C-005
- C-007
- FR-001
- FR-002
- FR-003
- FR-004
- FR-008
- FR-009
- NFR-001
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-deployment-01KV19VJ
base_commit: 17c0b491a6d6dbd0b14d46a10b1cd14f5f52e252
created_at: '2026-06-13T20:24:40.005183+00:00'
subtasks:
- T007
- T008
- T009
shell_pid: "20072"
agent: "claude:opus:implementer:implementer"
history:
- date: '2026-06-13'
  author: tasks
  action: created
authoritative_surface: deploy/huggingface/
execution_mode: code_change
owned_files:
- deploy/huggingface/Dockerfile
- deploy/huggingface/README.md
- deploy/huggingface/SETUP.md
- README.md
tags: []
---

# WP03 — Hugging Face Space + live-demo docs

## Objective

Finalize the deployable Hugging Face Docker Space assets (already drafted) so a fresh build
reproducibly serves the UI at `/` and MCP at `/mcp` on port 7860 from a pinned tag, and
advertise the live demo in the project README.

## Context
- Contract: [../contracts/deployment-surface.md](../contracts/deployment-surface.md). Research
  R1 (HF serving), R2 (reproducible install), R6 (cost/cold-start) in [../research.md](../research.md).
- These files **already exist** (drafted earlier): `deploy/huggingface/{Dockerfile,README.md,SETUP.md}`.
  Validate and refine them; don't regress. The root `Dockerfile` and `hatch_build.py` fixes are
  the baseline (C-007) — do not modify the root `Dockerfile` here (not owned).

## Implement command
```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Scope — ONLY these owned files
- `deploy/huggingface/Dockerfile`, `deploy/huggingface/README.md`, `deploy/huggingface/SETUP.md`, `README.md` (root)

## Subtasks

### T007 — Validate/refine the Space Dockerfile (FR-001/002/003, NFR-002)
- Confirm: base `python:3.12-slim`; installs from the pinned source archive
  `https://github.com/ruhullasheik/mcpbin/archive/refs/tags/${MCPBIN_REF}.tar.gz` (so the
  frontend bundles — R2); `ENV FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=7860`; `EXPOSE 7860`;
  `CMD ["mcpbin","--transport","http"]`.
- **Verify the frontend actually bundles via this path.** Locally (no Docker needed):
  `uv run --no-project --with "https://github.com/ruhullasheik/mcpbin/archive/refs/tags/v0.1.0.tar.gz" python -c "from mcpbin import server, os; d=server._resolve_frontend_dir(); print(d, os.path.isfile(os.path.join(str(d),'index.html')))"`
  → expect a real dir + `True`. If Docker is available, build the Space image and curl `/` and
  `POST /mcp`. Record the method used.

### T008 — Space README front-matter + SETUP (FR-004, C-005)
- `deploy/huggingface/README.md`: valid HF Space front-matter — `sdk: docker`,
  `app_port: 7860` (must match the container bind port, FR-002), `license: mit`, title/emoji,
  short description; body links back to the repo.
- `deploy/huggingface/SETUP.md`: step-by-step maintainer runbook (create Docker Space → add
  the two files → push → get URL → verify with `scripts/smoke_check.py`). Note that Space
  creation is a manual maintainer step (C-005) and how to bump `MCPBIN_REF` to redeploy.

### T009 — Root README "Live demo" (FR-008, FR-009)
- Add a **Live demo** section near the top of the root `README.md`:
  - The live URL (use a clear placeholder like `https://<your-space>.hf.space/` until the
    maintainer creates it) and a one-line "connect your MCP client to `<url>/mcp`".
  - A short note (FR-009): free-tier Space **sleeps when idle and wakes on the next request**
    (first hit may take up to ~30 s), and the public instance serves the **`full`** profile.
  - Link to `deploy/huggingface/SETUP.md` for self-hosting your own instance.
- Keep it concise; don't duplicate the whole test checklist.

## Branch Strategy
Planning/base **main**; merge target **main**; worktree per lane from `lanes.json`.

## Definition of Done
- [ ] Space `Dockerfile` binds `0.0.0.0:7860`, installs the pinned tag, and the bundled
      frontend resolves (verified by the documented method).
- [ ] Space `README.md` front-matter has `sdk: docker` + `app_port: 7860` matching the bind port.
- [ ] `SETUP.md` is a complete, correct maintainer runbook referencing the smoke check.
- [ ] Root `README.md` has a Live demo section with URL placeholder, connect line, and the
      cold-start/profile note.
- [ ] Root `Dockerfile`/`hatch_build.py` NOT modified (no regression); no files outside
      `owned_files` modified.

## Risks & reviewer guidance
- **verify-on-impl (R1):** the `.hf.space` subdomain serves at root, so the UI's relative
  `/mcp` fetch works — note this assumption in SETUP. Reviewer: confirm `app_port` (7860) ==
  the container's `FASTMCP_PORT`.
- The live URL is a placeholder until the maintainer creates the Space (C-005); make that
  obvious so the README isn't misleading. Reviewer: check the placeholder is clearly marked.

## Activity Log

- 2026-06-13T20:24:43Z – claude:opus:implementer:implementer – shell_pid=20072 – Assigned agent via action command
