# Feature Specification: mcpbin Free Public Deployment

**Mission**: mcpbin-deployment-01KV19VJ
**Created**: 2026-06-13
**Mission type**: software-dev
**Source**: deploy brief + prior mcpbin build (mission #1, v0.1.0)

## Summary

Make mcpbin available as a **free, public, hosted instance** so MCP client developers can
point a client at a live URL without installing anything — and make future releases
produce correct, downloadable artifacts automatically. The hosted instance runs on a
**Hugging Face Docker Space** serving the reference web UI at `/` and the Streamable HTTP
MCP endpoint at `/mcp`. A **GitHub Actions release workflow** builds and attaches a correct
wheel + sdist to the GitHub Release whenever a `v*` tag is pushed (preventing the stale/
broken-artifact problem seen with v0.1.0). The live endpoint is smoke-verified, and the
README advertises the live URL.

Scope is deliberately bounded: **Hugging Face Space only**, **GitHub-release artifacts only**
(no PyPI), and **deploy-ready + verified** — the one-time HF Space creation is performed by
the maintainer (it needs their Hugging Face account), with mcpbin providing exact steps and
verifying the result.

---

## User Scenarios & Testing

### Primary actors

| Actor | Goal |
|---|---|
| MCP client developer (external) | Point a client at a public mcpbin URL and exercise the protocol with zero local setup |
| Maintainer (repo owner) | Stand up the free hosted instance and have releases produce correct artifacts automatically |
| Contributor cutting a release | Push a `v*` tag and trust that the GitHub Release gets correct, installable artifacts |

### Acceptance scenarios

1. **Public UI loads** — Given the hosted instance is live, when a developer opens the
   Space's base URL, then the searchable reference UI renders the full catalog (tools
   grouped by feature area, resources, prompts) fetched from `/mcp`.
2. **Public MCP endpoint works** — Given the hosted instance, when an MCP client connects to
   `<base-url>/mcp` over Streamable HTTP and initializes, then it can list and call tools,
   list resources/prompts, and receive `_meta` on results.
3. **Container is externally reachable** — Given the deployment image, when it starts, then
   it binds all interfaces on the platform-provided port (not loopback/fixed) and answers
   external requests.
4. **Release artifacts are correct** — Given a `v*` tag is pushed, when the release workflow
   runs, then a wheel and sdist are built and attached to that tag's GitHub Release, and the
   wheel **bundles the frontend** (installing it serves the UI).
5. **Cold start recovers** — Given the free Space has slept due to inactivity, when a request
   arrives, then the instance wakes and serves correctly within a documented cold-start
   window.
6. **Live verification** — Given the instance is up, when the maintainer runs the documented
   smoke check against the live URL, then UI and `/mcp` both pass.
7. **Discoverability** — Given the README, when a reader looks for the demo, then the live
   URL and a one-line connect instruction are present.

### Edge cases

- The deploy image must not crash on startup (the v0.1.0 Docker `CMD` used non-existent
  flags — regression must stay fixed).
- If `/mcp` is unreachable from the UI, each section shows the inline error (inherited
  behavior must survive hosting, e.g. behind the Space proxy/subpath).
- The release workflow must build the wheel so it includes the frontend even when built via
  the sdist path (the v0.1.0 wheel shipped without it).
- Secrets (if any) must never be committed; the maintainer's HF/login credentials stay out
  of the repo and CI logs.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Provide a deployable Hugging Face Docker Space definition (Space `README.md` front-matter + Space `Dockerfile`) that runs mcpbin and serves the UI at `/` and MCP at `/mcp`. | Draft |
| FR-002 | The deployment image must bind all interfaces on the platform-assigned port (via `FASTMCP_HOST`/`FASTMCP_PORT`), with the Space's declared `app_port` and the container's bind port kept in agreement. | Draft |
| FR-003 | The Space image must install mcpbin reproducibly from a pinned source reference (release tag) such that the bundled frontend is present in the running container. | Draft |
| FR-004 | Provide a step-by-step maintainer runbook to create the Space, add the two files, deploy, and obtain the live URL. | Draft |
| FR-005 | Provide a GitHub Actions workflow that, on push of a `v*` tag, builds the wheel + sdist and uploads them to that tag's GitHub Release (creating the release if absent). | Draft |
| FR-006 | The release workflow must run the test suite (or at least a build + frontend-bundled assertion) as a gate before publishing artifacts. | Draft |
| FR-007 | Provide a smoke-verification procedure/script that checks a live base URL: UI returns HTTP 200 and contains the app shell, and `/mcp` accepts an MCP `initialize` (not a 404/405). | Draft |
| FR-008 | Update the project README to advertise the live demo URL and a one-line "connect your client to `<url>/mcp`" instruction. | Draft |
| FR-009 | Document the cold-start/sleep behavior and the active capability profile of the public instance so users know what to expect. | Draft |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|---|---|---|---|
| NFR-001 | Cost — the hosted instance and CI run at no cost. | $0 on the free Hugging Face Space tier and GitHub Actions free minutes for a public repo. | Draft |
| NFR-002 | Reproducible deploy — a fresh Space build yields a working instance from the pinned reference. | A from-scratch Space build serves UI + `/mcp` with no manual post-build fixes. | Draft |
| NFR-003 | Release reliability — tagged releases always carry correct artifacts. | 100% of `v*`-tag runs attach a wheel whose install serves the UI; verified by an automated check in the workflow. | Draft |
| NFR-004 | Cold-start latency — a slept instance recovers quickly. | First request after sleep returns a successful response within ≤ 30 s. | Draft |
| NFR-005 | No secrets in repo/logs — credentials never committed or printed. | Zero secrets in tracked files; CI uses only the built-in `GITHUB_TOKEN`; no tokens echoed. | Draft |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Hosting target is a **Hugging Face Docker Space** only (no Cloud Run/Render/etc. in this mission). | Draft |
| C-002 | Distribution is **GitHub-release artifacts only** — no PyPI/TestPyPI publishing in this mission. | Draft |
| C-003 | The public instance serves the **`full`** capability profile over Streamable HTTP. | Draft |
| C-004 | No new runtime dependencies; mcpbin still depends only on FastMCP (inherited from the build mission). | Draft |
| C-005 | The one-time Space creation (HF account, Space repo) is a **manual maintainer step**; automation covers config, CI, verification, and docs only. | Draft |
| C-006 | CI runs on GitHub Actions using only the repository's built-in `GITHUB_TOKEN` (no external secrets) for the artifact-only release. | Draft |
| C-007 | Reuse the already-fixed root `Dockerfile` and `deploy/huggingface/` assets where possible; do not regress the v0.1.0 startup/packaging fixes. | Draft |

---

## Success Criteria

- SC-001 — A person with no mcpbin install can open the public URL and successfully list and
  call a tool through the rendered UI's catalog and via a direct `/mcp` client.
- SC-002 — Pushing a `v*` tag results, with no manual steps, in a GitHub Release whose
  attached wheel installs and serves the web UI.
- SC-003 — Rebuilding the Space from scratch produces a working instance with no manual
  post-build fixes (reproducible).
- SC-004 — The README lets a new reader reach the live demo and connect a client in under a
  minute, with no ambiguity about the endpoint.
- SC-005 — The entire hosted + release setup incurs no monetary cost.

---

## Key Entities

| Entity | Description |
|---|---|
| Hugging Face Space | The hosted unit: a Docker Space with `README.md` front-matter (`app_port`) + `Dockerfile`; exposes a public base URL. |
| Deployment image | The container that installs mcpbin from a pinned tag and runs the HTTP transport bound to `0.0.0.0:<port>`. |
| Release workflow | A GitHub Actions workflow triggered by `v*` tags that builds + gates + uploads artifacts. |
| Release artifacts | The wheel + sdist attached to a GitHub Release; the wheel must bundle the frontend. |
| Live URL | The public base URL of the Space (UI at `/`, MCP at `/mcp`) advertised in the README. |
| Smoke check | A scripted verification that the live UI and `/mcp` respond correctly. |

---

## Assumptions

- The maintainer has (or will create) a free Hugging Face account; the agent cannot create
  accounts or push to an HF Space on the maintainer's behalf (C-005).
- The repository is public, so GitHub Actions minutes and HF free tier apply at no cost.
- The live instance is a best-effort demo (free tier): it may sleep when idle and is not an
  SLA-backed service; this is acceptable and documented (NFR-004, FR-009).
- The Space pins a release tag (e.g. `v0.1.0`) for reproducibility; bumping the pin redeploys.
- The frontend-bundling and Docker startup fixes already merged to `main` are the baseline;
  this mission builds on them and must not regress them.
- "Verified by me" means local verification (Docker run / build assertions) plus a live smoke
  check **after** the maintainer creates the Space; the live step is gated on that manual action.

## Out of Scope

- PyPI / TestPyPI publishing (deferred to a future mission).
- Additional hosting targets (Cloud Run, Render, Fly, Koyeb, self-hosted VM).
- A custom domain (e.g. mcpbin.dev), TLS management beyond what the Space provides, CDN, or
  analytics.
- Authentication / API-key gating / abuse protection for the public instance.
- Autoscaling, high availability, uptime monitoring, or alerting.
- Automated creation of the Hugging Face account or Space (manual maintainer step).
