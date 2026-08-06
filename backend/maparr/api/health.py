"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from ..services.metrics import TILE_CACHE_HITS, TILE_CACHE_MISSES

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "uptime_seconds": 0.0,  # Replace with actual uptime if available
        "database": "ok",  # Placeholder, would check DB connection
        "storage": "ok",  # Placeholder, would check disk space
        "tile_cache": {
            "hits": int(TILE_CACHE_HITS._value.get()),
            "misses": int(TILE_CACHE_MISSES._value.get()),
            "hit_rate": 0.0,  # Calculate if possible
        },
    }

