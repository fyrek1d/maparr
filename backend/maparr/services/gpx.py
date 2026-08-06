"""GPX import / export helpers."""

from __future__ import annotations

import io
from typing import Any

import gpxpy
import gpxpy.gpx


def parse_gpx(content: bytes | str) -> dict[str, Any]:
    """Parse GPX XML into a lightweight dict of tracks, routes and waypoints."""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    gpx = gpxpy.parse(io.StringIO(content))
    tracks, routes, waypoints = [], [], []

    for trk in gpx.tracks:
        points = []
        for seg in trk.segments:
            for p in seg.points:
                points.append([p.latitude, p.longitude, p.elevation or 0.0, p.time.isoformat() if p.time else None])
        tracks.append({"name": trk.name or "Track", "points": points, "count": len(points)})

    for rte in gpx.routes:
        points = [[p.latitude, p.longitude, p.elevation or 0.0,
                   p.time.isoformat() if p.time else None] for p in rte.points]
        routes.append({"name": rte.name or "Route", "points": points, "count": len(points)})

    for wp in gpx.waypoints:
        waypoints.append({
            "name": wp.name or "Waypoint",
            "lat": wp.latitude,
            "lon": wp.longitude,
            "elevation": wp.elevation or 0.0,
            "description": wp.description or "",
        })

    return {"tracks": tracks, "routes": routes, "waypoints": waypoints}


def export_gpx(name: str, tracks: list[dict], waypoints: list[dict]) -> str:
    """Serialize stored tracks/waypoints back into a GPX XML document."""
    gpx = gpxpy.gpx.GPX()
    gpx.name = name or "Maparr export"
    for t in tracks:
        trk = gpxpy.gpx.GPXTrack(name=t.get("name", "Track"))
        seg = gpxpy.gpx.GPXTrackSegment()
        for pt in t.get("points") or []:
            lat, lon = pt[0], pt[1]
            seg.points.append(gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon))
        trk.segments.append(seg)
        gpx.tracks.append(trk)
    for wp in waypoints:
        gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(
            latitude=wp["lat"], longitude=wp["lon"],
            name=wp.get("name", "Waypoint"), description=wp.get("description", ""),
        ))
    return gpx.to_xml()
