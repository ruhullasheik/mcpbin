# Deploy mcpbin to a Hugging Face Space (free)

This folder contains a ready-to-use **Docker Space** for mcpbin. It runs the live MCP
server (Streamable HTTP at `/mcp`) and the reference web UI at `/`, free, with no card.

The Space is self-contained: its `Dockerfile` installs mcpbin from the tagged GitHub
source archive, so you do **not** need to push the whole repo or publish to PyPI.

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

## Point an MCP client at it

Streamable HTTP endpoint: `https://<your-username>-mcpbin.hf.space/mcp`

## Notes

- **Port:** HF routes to the port set by `app_port: 7860` in `README.md`; the container
  binds `0.0.0.0:7860` via `FASTMCP_HOST`/`FASTMCP_PORT`. Keep the two in sync if you change it.
- **Sleeping:** free Spaces sleep after inactivity and wake on the next request (a few
  seconds of cold start).
- **Updating the version:** bump `ARG MCPBIN_REF=v0.1.0` in the `Dockerfile` to a newer tag
  (or a commit SHA / `main`) and push; HF rebuilds.
- **Profile:** this serves the default `full` profile. To demo capability gating, change the
  `CMD` to e.g. `["mcpbin","--transport","http","--profile","tools-only"]`.
