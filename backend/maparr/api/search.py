"""Offline search endpoints (places, reverse geocoding)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..deps import SessionDep
from ..schemas import ReverseGeocodeResult, SearchResult
from ..services.geocoder import get_geocoder
from ..services.metrics import GEOSEARCH_REQUESTS

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
def search(q: str = Query(min_length=1, max_length=120),
           limit: int = Query(12, ge=1, le=50), session: SessionDep = None):
    GEOSEARCH_REQUESTS.inc()
    return [SearchResult(**r) for r in get_geocoder().search(q, limit=limit)]


@router.get("/reverse", response_model=list[ReverseGeocodeResult])
def reverse_geocode(lat: float, lon: float,
                    max_dist: float = Query(250.0, ge=1, le=20000),
                    limit: int = Query(5, ge=1, le=20), session: SessionDep = None):
    return [ReverseGeocodeResult(**r) for r in get_geocoder().reverse(lat, lon, max_dist, limit)]