"""Region browsing and search backed by the bundled geographic data."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from ..deps import SessionDep
from ..schemas import RegionOut
from ..services import geodata
from ..services.geometry import normalize_bbox

router = APIRouter(prefix="/api/regions", tags=["regions"])


def _to_region(feature: dict, slug: str | None = None) -> RegionOut:
    centroid = feature.get("centroid") or [0.0, 0.0]
    return RegionOut(
        id=uuid.uuid5(uuid.NAMESPACE_URL, f"region:{slug or feature['name']}:{feature.get('iso','')}").hex,
        slug=slug or feature["name"].lower().replace(" ", "-"),
        name=feature["name"],
        kind=feature.get("kind", "custom"),
        iso=feature.get("iso") or "",
        parent_id=feature.get("parent_id") or "",
        bbox=feature.get("bbox") or [],
        centroid=centroid,
        area_km2=feature.get("area") or feature.get("area_km2") or 0.0,
        population=feature.get("pop_est") or feature.get("population") or 0.0,
        meta={"source": feature.get("source", "natural-earth"),
              "country": feature.get("country") or "",
              "admin1": feature.get("admin1") or ""},
    )


@router.get("/search")
def search_regions(q: str = Query(min_length=1, max_length=120), limit: int = Query(20, le=100),
                   session: SessionDep = None):
    results = geodata.search_regions(q, limit=limit)
    return [_to_region(r, slug=r.get("slug")) for r in results]


@router.get("/countries", response_model=list[RegionOut])
def countries(session: SessionDep = None):
    out = []
    for c in geodata.countries():
        out.append(_to_region({**c, "kind": "country"}))
    return out


@router.get("/countries/{iso}/states", response_model=list[RegionOut])
def country_states(iso: str, session: SessionDep = None):
    country = geodata.find_country(iso=iso)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    states = geodata.admin1_by_iso().get(iso.upper(), [])
    return [_to_region({**s, "kind": "admin1", "parent_id": ""}) for s in states]


@router.get("/cities")
def cities_in(west: float, south: float, east: float, north: float,
              limit: int = Query(500, le=2000), session: SessionDep = None):
    """Return bundled cities inside a bounding box."""
    w, s, e, n = normalize_bbox([west, south, east, north])
    out = []
    for c in geodata.cities():
        if w <= c["lo"] <= e and s <= c["la"] <= n:
            out.append({
                "name": c["n"],
                "lat": c["la"],
                "lon": c["lo"],
                "iso": c.get("c", ""),
                "admin1": c.get("a1", ""),
                "population": c.get("p") or 0,
            })
    out.sort(key=lambda c: -(c["population"] or 0))
    return out[:limit]
