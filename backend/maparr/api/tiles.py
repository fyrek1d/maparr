"""Tile serving endpoints (function fully offline after download)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from ..config import get_settings
from ..deps import SessionDep
from ..services.tile_server import find_tile, get_cache

router = APIRouter(prefix="/api/tiles", tags=["tiles"])


def _respond(session, z, x, y, map_id=None):
    settings = get_settings()
    result = find_tile(session, z, x, y, map_id=map_id, cache=get_cache())
    if result is None:
        return Response(status_code=404)
    headers = {
        "Content-Type": result.content_type,
        "Cache-Control": f"public, max-age={settings.tile_max_age}",
        "X-Maparr-Map": result.map_id or "",
    }
    return Response(content=result.data, media_type=result.content_type, headers=headers)


@router.get("/{map_id}/{z}/{x}/{y}", include_in_schema=False)
@router.get("/{map_id}/{z}/{x}/{y}.{ext}", include_in_schema=False)
def tile_for_map(map_id: str, z: int, x: int, y: int, session: SessionDep, ext: str = "png"):
    return _respond(session, z, x, y, map_id=map_id)


@router.get("/{z}/{x}/{y}", include_in_schema=False)
@router.get("/{z}/{x}/{y}.{ext}", include_in_schema=False)
def tile_auto(z: int, x: int, y: int, session: SessionDep, ext: str = "png"):
    return _respond(session, z, x, y)
