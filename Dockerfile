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
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the project source and the reference frontend, then install the project.
# frontend/ is authored by a later work package (WP14); the assembled image is
# built once the full mission has landed, so both directories are present. The
# hatch build hook ships frontend/ into the wheel as package data.
COPY src ./src
COPY frontend ./frontend
RUN uv sync --frozen --no-dev

# Default HTTP transport so the container is reachable.
EXPOSE 8000
ENTRYPOINT ["mcpbin"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
