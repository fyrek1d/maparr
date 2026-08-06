"""API router to aggregate all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from . import (
    auth,
    bookmarks,
    downloads,
    gpx,
    health,
    maintenance,
    maps,
    markers,
    onboarding,
    providers,
    regions,
    search,
    settings,
    tiles,
    users,
    webhooks,
)

api_router = APIRouter()  # sub-routers already carry their own /api prefixes

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(regions.router)
api_router.include_router(providers.router)
api_router.include_router(maps.router)
api_router.include_router(downloads.router)
api_router.include_router(tiles.router)
api_router.include_router(search.router)
api_router.include_router(bookmarks.router)
api_router.include_router(markers.router)
api_router.include_router(gpx.router)
api_router.include_router(webhooks.router)
api_router.include_router(settings.router)
api_router.include_router(maintenance.router)
api_router.include_router(onboarding.router)
api_router.include_router(health.router)
