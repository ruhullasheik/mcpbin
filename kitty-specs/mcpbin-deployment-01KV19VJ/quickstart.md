# Quickstart: Deploy mcpbin (maintainer runbook)

**Mission**: mcpbin-deployment-01KV19VJ

End-to-end path to a free public instance + verified release automation. The only manual,
account-gated step is creating the Space (C-005).

## A. Release automation (one-time, automatic thereafter)
1. Merge `.github/workflows/release.yml` to `main`.
2. Cut a release by pushing a tag: `git tag v0.1.1 && git push origin v0.1.1`.
3. The workflow runs tests, builds, asserts the wheel bundles the frontend, and attaches
   `dist/*` to the `v0.1.1` GitHub Release — no manual upload. (Re-runs are idempotent.)

## B. Create the Hugging Face Space (manual, needs your HF account)
1. <https://huggingface.co/new-space> → name `mcpbin`, **SDK: Docker**, Public, free CPU.
2. Add two files to the Space repo (from `deploy/huggingface/`):
   ```bash
   git clone https://huggingface.co/spaces/<you>/mcpbin && cd mcpbin
   cp <repo>/deploy/huggingface/README.md  ./README.md
   cp <repo>/deploy/huggingface/Dockerfile ./Dockerfile
   git add README.md Dockerfile && git commit -m "mcpbin Space" && git push
   ```
   (`Dockerfile` pins `ARG MCPBIN_REF=v0.1.0` — bump to redeploy a newer tag.)
3. Wait for the build to go green.

## C. Verify the live instance
```bash
python scripts/smoke_check.py https://<you>-mcpbin.hf.space
```
Expect both checks PASS (UI 200 + `/mcp` initialize). Open the URL in a browser to see the UI.

## D. Advertise it
- The README "Live demo" section points to `https://<you>-mcpbin.hf.space/` and tells users
  to connect their client to `https://<you>-mcpbin.hf.space/mcp`.

## Acceptance mapping
- A → FR-005/FR-006/NFR-003 (correct artifacts on tag).
- B → FR-001/FR-002/FR-003/FR-004 (deployable, reachable, reproducible, documented).
- C → FR-007/NFR-004 + scenarios 1/2/6 (live UI + `/mcp`, cold-start tolerant).
- D → FR-008/SC-004 (discoverable).

## Notes
- Free Space sleeps when idle and wakes on the next request (first hit ≤ ~30 s); serves the
  `full` profile (FR-009).
- Local equivalent: `uv run mcpbin --transport http` then
  `python scripts/smoke_check.py http://localhost:8000`.
