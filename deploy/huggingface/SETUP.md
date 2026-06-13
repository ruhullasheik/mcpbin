# Deploy mcpbin to a Hugging Face Space (free)

This folder contains a ready-to-use **Docker Space** for mcpbin. It runs the live MCP
server (Streamable HTTP at `/mcp`) and the reference web UI at `/`, free, with no card.

The Space is self-contained: its `Dockerfile` installs mcpbin from the tagged GitHub
source archive, so you do **not** need to push the whole repo or publish to PyPI.

> Creating the Space is a **manual maintainer step** — it lives under your own Hugging
> Face account, so it cannot be automated from this repo. Follow the steps below once;
> after that, redeploys are a one-line `MCPBIN_REF` bump (see *Updating the version*).

## Steps

1. **Create the Space**
   - Go to <https://huggingface.co/new-space>.
   - Owner: your account · Space name: `mcpbin`.
   - **SDK: Docker** → "Blank" template. Visibility: Public. Hardware: free CPU basic.

2. **Add the two files to the Space repo** (clone it, copy these in, push):
   ```bash
   git clone https://huggingface.co/spaces/<your-username>/mcpbin
   cd mcpbin
   cp /path/to/mcpbin/deploy/huggingface/README.md   ./README.md
   cp /path/to/mcpbin/deploy/huggingface/Dockerfile  ./Dockerfile
   git add README.md Dockerfile
   git commit -m "mcpbin Space: Docker, port 7860"
   git push
   ```
   (Or paste the two files via the Space's web "Files" editor.)

3. **Wait for the build.** HF builds the Dockerfile and starts the container. When it goes
   green:
   - UI: `https://<your-username>-mcpbin.hf.space/`
   - MCP endpoint: `https://<your-username>-mcpbin.hf.space/mcp`

4. **Verify the live Space.** From a checkout of this repo, run the smoke check against the
   Space's base URL:
   ```bash
   python scripts/smoke_check.py https://<your-username>-mcpbin.hf.space/
   ```
   It confirms `GET /` returns the UI shell and `POST /mcp` answers a real MCP `initialize`
   (not 404/405). The first request may take up to ~30 s if the Space was asleep.

## Point an MCP client at it

Streamable HTTP endpoint: `https://<your-username>-mcpbin.hf.space/mcp`

The `.hf.space` subdomain serves the container **at root**, so the UI's relative `/mcp`
fetch resolves to that same endpoint — no path prefix or rewrite is needed.

## Notes

- **Port:** HF routes to the port set by `app_port: 7860` in `README.md`; the container
  binds `0.0.0.0:7860` via `FASTMCP_HOST`/`FASTMCP_PORT`. Keep the two in sync if you change it.
- **Sleeping:** free Spaces sleep after inactivity and wake on the next request; the first
  hit after idle can take up to ~30 s of cold start before it responds.
- **Updating the version:** bump `ARG MCPBIN_REF=v0.1.0` in the `Dockerfile` to a newer tag
  (or a commit SHA / `main`) and push; HF rebuilds.
- **Profile:** this serves the default `full` profile. To demo capability gating, change the
  `CMD` to e.g. `["mcpbin","--transport","http","--profile","tools-only"]`.
