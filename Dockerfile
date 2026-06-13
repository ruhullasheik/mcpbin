# mcpbin — build-ready (unpublished) image, uv-managed (C-002, C-007).
# Uses the official uv image with Python 3.12 (C-001).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# uv runtime configuration.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Resolve dependencies first for better layer caching, using the committed lockfile.
# hatch_build.py is the custom build backend hook; it must be present before the
# project itself is built (the second `uv sync` below).
COPY pyproject.toml uv.lock README.md LICENSE hatch_build.py ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the project source and the reference frontend, then install the project.
# frontend/ is authored by a later work package (WP14); the assembled image is
# built once the full mission has landed, so both directories are present. The
# hatch build hook ships frontend/ into the wheel as package data.
COPY src ./src
COPY frontend ./frontend
RUN uv sync --frozen --no-dev

# Serve the Streamable HTTP transport, reachable from outside the container.
# FastMCP reads FASTMCP_HOST / FASTMCP_PORT; bind to all interfaces and honour a
# platform-injected $PORT (Cloud Run, Render, Koyeb, Fly, …), defaulting to 8000.
ENV FASTMCP_HOST=0.0.0.0
EXPOSE 8000
CMD ["sh", "-c", "exec env FASTMCP_PORT=\"${PORT:-8000}\" mcpbin --transport http"]
