"""FastAPI main application setup."""

from __future__ import annotations

import contextlib

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST

from .config import get_settings
from .db import init_db
from .services.logging import setup_logging
from .services.maintenance import get_maintenance
from .services.metrics import generate_metrics


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title="Maparr",
        description="Self-hosted offline map manager for home servers.",
        version="0.1.0",
        license_info={"name": "Apache-2.0", "identifier": "Apache-2.0"},
    )
    app.state.settings = settings
    app.state.maintenance = get_maintenance()

    # --- Static/metrics/health are registered before API.
    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "service": "maparr", "version": "0.1.0"}

    @app.get("/metrics", tags=["meta"])
    def metrics():
        return Response(content=generate_metrics(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/index.html")

    # --- Startup / shutdown
    @app.on_event("startup")
    async def startup():
        init_db()
        get_maintenance().start()

    @app.on_event("shutdown")
    async def shutdown():
        await get_maintenance().stop()
        from .services.downloader import get_manager

        with contextlib.suppress(Exception):
            await get_manager().shutdown()

    # --- API routes
    from .api import api_router

    app.include_router(api_router)

    # --- Static files (frontend build) - catch-all last
    static = StaticFiles(directory="frontend/dist", html=True, check_dir=False)
    app.mount("/", static, name="static")

    return app


def run():
    uvicorn.run(create_app, host="0.0.0.0", port=8000, log_config=None)


if __name__ == "__main__":
    run()
