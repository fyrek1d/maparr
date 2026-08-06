"""Pure geometry helpers: bounding boxes, point-in-polygon, tile math."""

from __future__ import annotations

import math
from typing import Iterable

LON_MIN, LON_MAX = -180.0, 180.0
LAT_MIN, LAT_MAX = -85.0511, 85.0511
EARTH_RADIUS_KM = 6371.0088

# Clamp to Web Mercator valid range.
MERCATOR_LAT = 85.0511287798066


def clamp_lon(lon: float) -> float:
    return max(LON_MIN, min(LON_MAX, lon))


def clamp_lat(lat: float) -> float:
    return max(-MERCATOR_LAT, min(MERCATOR_LAT, lat))


def normalize_bbox(bbox: Iterable[float]) -> tuple[float, float, float, float]:
    """Return (west, south, east, north), clamped to valid ranges."""
    w, s, e, n = [float(v) for v in bbox]
    w, e = clamp_lon(min(w, e)), clamp_lon(max(w, e))
    s, n = clamp_lat(min(s, n)), clamp_lat(max(s, n))
    return w, s, e, n


def bbox_width_deg(bbox: Iterable[float]) -> float:
    w, s, e, n = normalize_bbox(bbox)
    return e - w


def bbox_area_km2(bbox: Iterable[float]) -> float:
    w, s, e, n = normalize_bbox(bbox)
    lat = math.radians((s + n) / 2.0)
    dy = (n - s) * 111.32
    dx = (e - w) * 111.32 * math.cos(lat)
    return dx * dy


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    lat, lon = clamp_lat(lat), clamp_lon(lon)
    lat_rad = math.radians(lat)
    n = 1 << zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return int(x), int(y)


def tile_to_lat_lon(x: int, y: int, zoom: int) -> tuple[float, float]:
    """Return (lat, lon) of the north-west corner of a tile."""
    n = 1 << zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def tile_to_bbox(x: int, y: int, zoom: int) -> tuple[float, float, float, float]:
    """Return (west, north, east, south) of a tile."""
    n = 1 << zoom
    lon0 = x / n * 360.0 - 180.0
    lon1 = (x + 1) / n * 360.0 - 180.0
    lat0 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lat1 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return lon0, lat1, lon1, lat0


def tiles_in_bbox(bbox: Iterable[float], zoom: int) -> tuple[int, int, int, int]:
    """Return (xmin, ymin, xmax, ymax) inclusive for tiles intersecting a bbox.

    ``ymin`` is the smaller tile row (northernmost).
    """
    w, s, e, n = normalize_bbox(bbox)
    x0, y0 = lat_lon_to_tile(n, w, zoom)
    x1, y1 = lat_lon_to_tile(s, e, zoom)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def count_tiles(bbox: Iterable[float], min_zoom: int, max_zoom: int) -> int:
    total = 0
    for z in range(min_zoom, max_zoom + 1):
        x0, y0, x1, y1 = tiles_in_bbox(bbox, z)
        total += (x1 - x0 + 1) * (y1 - y0 + 1)
    return total


def count_tiles_by_zoom(bbox: Iterable[float], min_zoom: int, max_zoom: int) -> dict[int, int]:
    out: dict[int, int] = {}
    for z in range(min_zoom, max_zoom + 1):
        x0, y0, x1, y1 = tiles_in_bbox(bbox, z)
        out[z] = (x1 - x0 + 1) * (y1 - y0 + 1)
    return out


def point_in_rings(lon: float, lat: float, rings: list[list[list[float]]]) -> bool:
    """Ray-casting point-in-polygon over an unordered list of rings.

    Returns True if the point is inside an even number of enclosing rings.
    The first ring of each polygon is the outer boundary; subsequent rings are
    holes. Because 110m/50m data has few holes, we use parity: inside if the
    point is inside an odd number of rings.
    """
    inside = False
    for ring in rings:
        if _point_in_ring(lon, lat, ring):
            inside = not inside
    return inside


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_bbox(lon: float, lat: float, bbox: Iterable[float]) -> bool:
    w, s, e, n = normalize_bbox(bbox)
    return w <= lon <= e and s <= lat <= n


def tile_center(bbox: Iterable[float], z: int, x: int, y: int) -> tuple[float, float]:
    _, _nw_lat, _nw_lon, _ = tile_to_bbox(x, y, z)
    lat0, lon0, lat1, lon1 = tile_to_bbox(x, y, z)
    return (lon0 + lon1) / 2.0, (lat0 + lat1) / 2.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
