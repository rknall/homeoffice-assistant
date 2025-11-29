# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""FastAPI application entry point."""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure avatar directory exists
os.makedirs("static/avatars", exist_ok=True)

app = FastAPI(
    title="Travel Manager",
    description="Self-hosted business trip management with expense tracking",
    version="0.1.0",
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
from src.api.v1.router import api_router

app.include_router(api_router, prefix="/api/v1")

# Mount static files for production frontend (if directory exists)
static_path = Path("static")
if static_path.exists():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    # Serve index.html for root
    @app.get("/")
    async def serve_root():
        return FileResponse("static/index.html")

    # Catch-all route for SPA - must be last
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Serve static files if they exist
        file_path = static_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse("static/index.html")
