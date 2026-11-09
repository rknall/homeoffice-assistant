# Multi-stage build for HomeOffice Assistant
# Stage 1: Build frontend and plugin bundles
FROM oven/bun:1.4.4-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files and lockfile
COPY frontend/package.json frontend/bun.lock ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

# Copy plugins for building
COPY plugins/ /app/plugins/

# Build plugins and production bundle, then check every plugin with a
# frontend entry produced its bundle (plugins import only the React shim,
# so no plugin-specific install step is needed)
RUN bun run build:all \
    && for entry in /app/plugins/*/frontend/index.ts; do \
         test -f "$(dirname "$entry")/index.js" || exit 1; \
       done


# Stage 2: Install locked Python dependencies (no compilers needed: every
# locked package ships a wheel)
FROM python:3.14-slim AS python-builder

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


# Stage 3: Production image
FROM python:3.14-slim

WORKDIR /app

# Install runtime dependencies (curl for healthcheck)
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with a fixed uid (bind mounts must be owned by 1000)
RUN useradd --uid 1000 --create-home --shell /bin/bash appuser

# Locked virtualenv; stays root-owned and read-only for the app
COPY --from=python-builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Application code and version source (src/version.py reads pyproject.toml)
COPY pyproject.toml /app/
COPY src/ /app/src/
COPY alembic.ini /app/
COPY alembic/ /app/alembic/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /app/static

# Copy plugins (backend + built frontend)
COPY --from=frontend-builder /app/plugins /app/plugins

# Copy entrypoint script
COPY docker/docker-entrypoint.sh /app/

# Writable data paths only (database, logos, avatars)
RUN mkdir -p /app/data /app/static/avatars \
    && chown 1000:1000 /app/data /app/static/avatars

USER 1000:1000

# Environment defaults
ENV DATABASE_URL="sqlite:///./data/homeoffice_assistant.db"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health"]

# Run entrypoint script (runs migrations then starts uvicorn)
CMD ["/app/docker-entrypoint.sh"]
