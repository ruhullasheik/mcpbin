# Hugging Face Space (Docker SDK) image for mcpbin.
#
# Self-contained: installs mcpbin from the tagged GitHub source archive, so the
# bundled reference frontend (frontend/ -> mcpbin/frontend) ships in the wheel via
# the project's build hook. No git, no PyPI release needed.
#
# HF Spaces route external traffic to the port declared as `app_port` in README.md
# (7860 here). FastMCP reads FASTMCP_HOST / FASTMCP_PORT, so we bind 0.0.0.0:7860.
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=7860

# Pin to a release tag for reproducibility. Bump this to redeploy a newer version.
ARG MCPBIN_REF=v0.1.0
RUN pip install "https://github.com/ruhullasheik/mcpbin/archive/refs/tags/${MCPBIN_REF}.tar.gz"

EXPOSE 7860
CMD ["mcpbin", "--transport", "http"]
