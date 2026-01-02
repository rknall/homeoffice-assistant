# Multi-stage build for HomeOffice Assistant
# Stage 1: Build frontend
# Note: node:25-alpine has CVE-2025-64756 (glob package, HIGH severity)
# This only affects the build stage - vulnerable package is not in final image
FROM node:25-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Copy plugins for building
COPY plugins/ /app/plugins/

# Build plugins and production bundle
RUN npm run build:all


# Stage 2: Build Python dependencies
FROM python:3.14-slim AS python-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    dpkg-dev=1.22.21 \
    gcc=4:14.2.0-1 \
    g++=4:14.2.0-1 \
    libc6-dev=2.41-12 \
    make=4.4.1-2 \
    curl=8.14.1-2+deb13u2 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Build wheel
RUN pip install --no-cache-dir build==1.3.0 \
    && python -m build --wheel


# Stage 3: Production image
FROM python:3.14-slim

WORKDIR /app

# Install runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=8.14.1-2+deb13u2\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Install Python package from wheel
COPY --from=python-builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Allow appuser to install plugin dependencies at runtime
RUN chmod -R a+w /usr/local/lib/python3.14/site-packages

# Copy application code
COPY src/ /app/src/
COPY alembic.ini /app/
COPY alembic/ /app/alembic/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /app/static

# Copy plugins (backend + built frontend)
COPY --from=frontend-builder /app/plugins /app/plugins

# Copy entrypoint script
COPY docker-entrypoint.sh /app/

# Create data directory
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

# Environment defaults
ENV DATABASE_URL="sqlite:///./data/homeoffice_assistant.db"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run entrypoint script (runs migrations then starts uvicorn)
CMD ["/app/docker-entrypoint.sh"]
