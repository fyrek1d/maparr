"""Active download jobs (for the admin downloads dashboard)."""

from __future__ import annotations

from fastapi import APIRouter

from ..db import get_db_session
from ..deps import AdminDep
from ..models import Map
from ..schemas import MapOut
from ..services.downloader import get_manager, map_to_out

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


@router.get("/active", response_model=list[MapOut])
def active_downloads(admin: AdminDep):
    """Return maps that are currently queued or in-progress, with live progress."""
    session = get_db_session()
    try:
        job_ids = [j.map_id for j in get_manager().list_jobs()]
        rows = session.query(Map).filter(Map.id.in_(job_ids)).all() if job_ids else []
        rows += (
            session.query(Map)
            .filter(Map.status.in_(["pending", "downloading", "paused"]), Map.id.notin_(job_ids))
            .all()
        )
        seen = set()
        results = []
        for row in rows:
            if row.id in seen:
                continue
            seen.add(row.id)
            job = get_manager().get_job(row.id)
            if job is not None:
                row.tiles_done = job.tiles_done
                row.bytes_done = job.bytes_done
                row.speed = job.speed
                row.eta_seconds = job.eta_seconds
            results.append(map_to_out(row))
        return results
    finally:
        session.close()