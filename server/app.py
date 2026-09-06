"""
server/app.py
───────────────
FastAPI application factory for tode web server.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import server.config  # noqa: F401 — puts src/ on sys.path before any imports
from server.routes.frames import router as frames_router
from server.routes.health import router as health_router
from server.routes.projects import router as projects_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="tode API",
        description="REST API for the tode computer vision annotation platform",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(frames_router)

    # Serve the web UI from server/static/
    _static = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(_static):
        app.mount("/", StaticFiles(directory=_static, html=True), name="static")

    return app


app = create_app()
