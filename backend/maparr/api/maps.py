"""Map lifecycle: create/download, list, update, delete, import, integrity, storage."""

from __future__ import annotations

import asyncio
import datetime as dt
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import AdminDep, SessionDep
from ..models import Map, MapLayer
from ..schemas import (
    DownloadCreate,
    DownloadEstimate,
    IntegrityResult,
    MapDetail,
    MapImport,
    MapLayerOut,
    MapLayerUpdate,
    MapOut,
    StorageBreakdown,
)
from ..services import providers as prov_svc
from ..services.downloader import (
    STATUS_CANCELLED,
    STATUS_COMPLETE,
    STATUS_PAUSED,
    get_manager,
    map_to_out,
)
from ..services.estimator import estimate_download, human_size
from ..services.geometry import normalize_bbox, point_in_rings
from ..services.mbtiles import MBTilesReader
from ..services.metrics import DOWNLOADS_STARTED
from ..services.tile_server import clear_reader_pool
from ..services.webhooks import dispatch
from .regions import _to_region

router = APIRouter(prefix="/api/maps", tags=["maps"])


def _region_from_id(session: Session, region_id: str) -> dict | None:
    from ..services import geodata

    for c in geodata.countries():
        if _to_region({**c, "kind": "country"}).id == region_id:
            return {**c, "kind": "country"}
    for s in geodata.admin1():
        if _to_region({**s, "kind": "admin1"}).id == region_id:
            return {**s, "kind": "admin1"}
    return None


# --- Estimates -------------------------------------------------------------

@router.post("/estimate", response_model=DownloadEstimate)
def estimate(payload: DownloadCreate, session: SessionDep):
    provider = prov_svc.get_provider(payload.provider_id, session)
    if provider is None:
        raise HTTPException(status_code=404, detail="Unknown provider")
    if payload.min_zoom > payload.max_zoom:
        raise HTTPException(status_code=400, detail="min_zoom must be <= max_zoom")
    bbox = list(normalize_bbox(payload.bbox))
    if payload.mask_to_region:
        region = _region_from_id(session, payload.region_id)
        mask = region.get("rings") if region else None
    else:
        mask = None
    return estimate_download(bbox, payload.min_zoom, payload.max_zoom,
                             provider.estimated_bytes_per_tile, mask=mask)


# --- Create ----------------------------------------------------------------

@router.post("", response_model=MapOut, status_code=201)
def create_download(payload: DownloadCreate, session: SessionDep, admin: AdminDep):
    provider = prov_svc.get_provider(payload.provider_id, session)
    if provider is None:
        raise HTTPException(status_code=404, detail="Unknown provider")

    bbox = list(normalize_bbox(payload.bbox))
    if bbox[3] - bbox[1] < 0.0001 or bbox[2] - bbox[0] < 0.0001:
        raise HTTPException(status_code=400, detail="Region bounding box is too small")

    region = _region_from_id(session, payload.region_id)
    mask = region.get("rings") if region and payload.mask_to_region else None
    if payload.mask_to_region and region is None:
        # Custom regions (e.g. cities / free-form) have no mask.
        mask = None

    name = payload.name or f"{provider.name} · {payload.region_name or payload.region_id} " \
                            f"(z{payload.min_zoom}-{payload.max_zoom})"
    max_zoom = min(payload.max_zoom, provider.max_zoom)

    existing = session.query(Map).filter(
        Map.region_id == payload.region_id,
        Map.provider_id == provider.id,
        Map.min_zoom == payload.min_zoom,
        Map.max_zoom == max_zoom,
    ).first()
    if existing and existing.status in (STATUS_COMPLETE, STATUS_PAUSED, "downloading"):
        raise HTTPException(status_code=409, detail=f"Map already exists ({existing.name})")

    estimate = estimate_download(bbox, payload.min_zoom, max_zoom,
                                 provider.estimated_bytes_per_tile, mask=mask)
    row = Map(
        name=name,
        region_id=payload.region_id,
        region_name=payload.region_name,
        provider_id=provider.id,
        provider_name=provider.name,
        layer="baselayer" if provider.kind == "baselayer" else "overlay",
        format=provider.format,
        min_zoom=payload.min_zoom,
        max_zoom=max_zoom,
        bbox=bbox,
        mask=mask,
        status="pending",
        tiles_total=estimate["tiles"],
        bytes_total=estimate["bytes_estimate"],
        options=payload.options,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return map_to_out(row)


# --- List / detail ----------------------------------------------------------

@router.get("", response_model=list[MapOut])
def list_maps(session: SessionDep, q: str | None = Query(None, max_length=120),
              status_filter: str | None = Query(None, alias="status"),
              provider_id: str | None = None):
    query = session.query(Map)
    if q:
        query = query.filter(Map.name.ilike(f"%{q}%"))
    if status_filter:
        query = query.filter(Map.status == status_filter)
    if provider_id:
        query = query.filter(Map.provider_id == provider_id)
    rows = query.order_by(Map.created_at.desc()).all()
    out = []
    for row in rows:
        job = get_manager().get_job(row.id)
        if job is not None:
            row.tiles_done = job.tiles_done
            row.bytes_done = job.bytes_done
            row.speed = job.speed
            row.eta_seconds = job.eta_seconds
            row.status = job.status
        out.append(map_to_out(row))
    return out


@router.get("/storage", response_model=StorageBreakdown)
def storage_breakdown(session: SessionDep, admin: AdminDep):
    rows = session.query(Map).filter(Map.status.in_([STATUS_COMPLETE, "imported"])).all()
    by_region: dict[str, dict] = {}
    by_provider: dict[str, dict] = {}
    total = 0
    for m in rows:
        total += m.file_size
        region = by_region.setdefault(m.region_name or m.region_id,
                                      {"name": m.region_name or m.region_id, "bytes": 0, "maps": 0})
        region["bytes"] += m.file_size
        region["maps"] += 1
        prov = by_provider.setdefault(m.provider_name, {"name": m.provider_name, "bytes": 0, "maps": 0})
        prov["bytes"] += m.file_size
        prov["maps"] += 1
    return StorageBreakdown(
        total_bytes=total,
        total_human=human_size(total),
        maps=[{"name": k, **v} for k, v in sorted(by_region.items(), key=lambda kv: -kv[1]["bytes"])],
    )


@router.get("/{map_id}", response_model=MapDetail)
def get_map(map_id: str, session: SessionDep):
    return MapOut.model_validate(map_to_out(row).model_dump())


@router.patch("/{map_id}/layers/{layer_id}", response_model=MapLayerOut)
def update_layer(map_id: str, layer_id: str, payload: MapLayerUpdate,
                 session: SessionDep, admin: AdminDep):
    layer = session.query(MapLayer).filter(MapLayer.id == layer_id, MapLayer.map_id == map_id).first()
    if layer is None:
        raise HTTPException(status_code=404, detail="Layer not found")
    layer.enabled = payload.enabled
    if payload.max_zoom is not None:
        layer.max_zoom = payload.max_zoom
    session.commit()
    session.refresh(layer)
    return layer


def _parse_bounds(bounds: str) -> list[float]:
    try:
        parts = [float(x) for x in bounds.split(",")]
        if len(parts) == 4:
            return list(normalize_bbox(parts))
    except (ValueError, TypeError):
        pass
    return [-180.0, -85.0511, 180.0, 85.0511]


def _fire(event: str, payload: dict) -> None:
    async def _run():
        await dispatch(event, payload)

    asyncio.ensure_future(_run())
