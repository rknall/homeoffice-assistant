# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.database import SessionLocal
from src.plugins import PluginRegistry

logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs("static/avatars", exist_ok=True)
os.makedirs("plugins", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup: Initialize plugin system
    logger.info("Initializing plugin system...")
    registry = PluginRegistry.get_instance()
    registry.set_app(app)

    db = SessionLocal()
    try:
        await registry.load_all_plugins(db)
        logger.info(f"Loaded {len(registry.get_enabled_plugins())} enabled plugins")
    except Exception as e:
        logger.error(f"Error loading plugins: {e}")
    finally:
        db.close()

    yield

    # Shutdown: Cleanup
    logger.info("Shutting down plugin system...")

app = FastAPI(
    title="HomeOffice Assistant",
    description="Self-hosted personal productivity and work management assistant",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include API router after it's created
from src.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")

# Mount plugin assets directory (for frontend plugin bundles)
plugins_path = Path("plugins")
if plugins_path.exists():
    app.mount(
        "/plugins",
        StaticFiles(directory="plugins"),
        name="plugins",
    )

# Mount static files for production frontend (if directory exists)
static_path = Path("static")
if static_path.exists():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    # Serve index.html for root
    @app.get("/")
    async def serve_root() -> FileResponse:
        """Serve the main SPA entry point."""
        return FileResponse("static/index.html")

    # Catch-all route for SPA - must be last
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str) -> FileResponse:
        """Serve SPA assets or fall back to index.html for client-side routing."""
        # Serve static files if they exist
        file_path = static_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse("static/index.html")
