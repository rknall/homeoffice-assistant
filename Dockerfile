# Multi-stage build for Travel Manager
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build production bundle
RUN npm run build


# Stage 2: Build Python dependencies
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Build wheel
RUN pip install --no-cache-dir build \
    && python -m build --wheel


# Stage 3: Production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Install Python package from wheel
COPY --from=python-builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Copy application code
COPY src/ /app/src/
COPY alembic.ini /app/
COPY alembic/ /app/alembic/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /app/static

# Create data directory
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

# Environment defaults
ENV DATABASE_URL="sqlite:///./data/travel_manager.db"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn, serving both API and static frontend
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
