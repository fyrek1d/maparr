"""Scheduled maintenance tasks (integrity, backups, cleanup)."""

from __future__ import annotations

from fastapi import APIRouter

from ..deps import AdminDep, SessionDep

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.get("/status")
def status(session: SessionDep, admin: AdminDep):
    from ..services.maintenance import get_maintenance

    return get_maintenance().tick()


@router.post("/integrity", response_model=list[dict])
def run_integrity(map_id: str | None = None, session: SessionDep = None, admin: AdminDep = None):
    from ..services.maintenance import get_maintenance

    return get_maintenance().integrity_check(map_id=map_id)


@router.post("/prune-backups")
def prune_backups(keep_days: int | None = None, session: SessionDep = None, admin: AdminDep = None):
    from ..services.backup import prune_backups

    return {"removed": prune_backups(keep_days=keep_days)}


@router.post("/cleanup-temp")
def cleanup_temp(session: SessionDep = None, admin: AdminDep = None):
    from ..services.maintenance import get_maintenance

    return get_maintenance().tick()