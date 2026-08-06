"""GPX import/export and stored tracks."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from ..deps import SessionDep, UserDep
from ..models import GpxTrack
from ..schemas import GpxImportResult
from ..services.gpx import export_gpx, parse_gpx

router = APIRouter(prefix="/api/gpx", tags=["gpx"])

MAX_GPX_BYTES = 50 * 1024 * 1024


@router.post("/import", response_model=GpxImportResult)
async def import_gpx(file: UploadFile, session: SessionDep, user: UserDep):
    content = await file.read()
    if len(content) > MAX_GPX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
    try:
        parsed = parse_gpx(content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid GPX: {exc}")

    name = (file.filename or "import").rsplit(".", 1)[0]
    for kind, items in (("track", parsed["tracks"]), ("route", parsed["routes"])):
        for item in items:
            track = GpxTrack(user_id=user.id, name=item["name"], track_type=kind,
                             data=item, points=item["count"])
            session.add(track)
    for wp in parsed["waypoints"]:
        track = GpxTrack(user_id=user.id, name=wp["name"], track_type="waypoint",
                         data=wp, points=1)
        session.add(track)
    session.commit()
    return parsed


@router.get("/tracks", response_model=list[dict])
def list_tracks(session: SessionDep, user: UserDep):
    rows = session.query(GpxTrack).filter(GpxTrack.user_id == user.id).order_by(
        GpxTrack.created_at.desc()).limit(200).all()
    return [{"id": r.id, "name": r.name, "track_type": r.track_type, "points": r.points,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.delete("/tracks/{track_id}", status_code=204)
def delete_track(track_id: str, session: SessionDep, user: UserDep):
    track = session.get(GpxTrack, track_id)
    if track is None or track.user_id != user.id:
        raise HTTPException(status_code=404, detail="Track not found")
    session.delete(track)
    session.commit()
    return None


@router.get("/export", response_class=PlainTextResponse)
def export(user: UserDep, session: SessionDep,
           include_tracks: bool = True, include_waypoints: bool = True):
    tracks = []
    waypoints = []
    for r in session.query(GpxTrack).filter(GpxTrack.user_id == user.id).all():
        if r.track_type in ("track", "route") and include_tracks:
            tracks.append(r.data)
        elif r.track_type == "waypoint" and include_waypoints:
            waypoints.append(r.data)
    return PlainTextResponse(
        content=export_gpx("Maparr export", tracks, waypoints),
        media_type="application/gpx+xml",
        headers={"Content-Disposition": 'attachment; filename="maparr-export.gpx"'},
    )