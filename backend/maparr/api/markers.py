"""Custom named markers (pins)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..deps import SessionDep, UserDep
from ..models import Marker, User
from ..schemas import MarkerCreate, MarkerOut, MarkerUpdate

router = APIRouter(prefix="/api/markers", tags=["markers"])


def _share(marker: Marker, user: User) -> bool:
    return marker.user_id == user.id or user.role == "admin"


@router.get("", response_model=list[MarkerOut])
def list_markers(session: SessionDep, user: UserDep):
    return session.query(Marker).filter(Marker.user_id == user.id).order_by(Marker.created_at.desc()).all()


@router.post("", response_model=MarkerOut, status_code=201)
def create_marker(payload: MarkerCreate, session: SessionDep, user: UserDep):
    marker = Marker(**payload.model_dump(), user_id=user.id)
    session.add(marker)
    session.commit()
    session.refresh(marker)
    return marker


@router.patch("/{marker_id}", response_model=MarkerOut)
def update_marker(marker_id: str, payload: MarkerUpdate, session: SessionDep, user: UserDep):
    marker = session.get(Marker, marker_id)
    if marker is None or not _share(marker, user):
        raise HTTPException(status_code=404, detail="Marker not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(marker, field, value)
    session.commit()
    session.refresh(marker)
    return marker


@router.delete("/{marker_id}", status_code=204)
def delete_marker(marker_id: str, session: SessionDep, user: UserDep):
    marker = session.get(Marker, marker_id)
    if marker is None or not _share(marker, user):
        raise HTTPException(status_code=404, detail="Marker not found")
    session.delete(marker)
    session.commit()
    return None