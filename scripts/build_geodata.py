#!/usr/bin/env python3
"""Build compact geodata bundles used by Maparr at runtime.

Reads Natural Earth vector geojson (public domain) and produces three compact
JSON files committed to ``backend/maparr/data/``:

- ``countries.json`` - country polygons, bboxes, centroids, areas
- ``admin1.json``    - first-level administrative divisions (states/provinces)
- ``cities.json``    - populated places for offline search + region picking

Usage:
    python scripts/build_geodata.py [--out DIR] [--raw-dir DIR]

The raw geojson files are only needed when regenerating and are gitignored.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

# Ring simplification: round coordinates to this many decimal places.
PRECISION = 4
EARTH_RADIUS_KM = 6371.0


def round_coord(x: float, y: float) -> list[float]:
    return [round(x, PRECISION), round(y, PRECISION)]


def simplify_ring(ring: list[list[float]]) -> list[list[float]]:
    """Drop consecutive duplicate coordinates (after rounding)."""
    out: list[list[float]] = []
    for pt in ring:
        rp = round_coord(pt[0], pt[1])
        if not out or out[-1] != rp:
            out.append(rp)
    # collapse 2-point rings
    if len(out) < 4:
        return []
    return out


def polygon_rings(geom: dict) -> list[list[list[float]]]:
    """Return a list of closed rings for Polygon / MultiPolygon geometries."""
    rings: list[list[list[float]]] = []
    if not geom or "coordinates" not in geom:
        return rings
    if geom.get("type") == "Polygon":
        rings = [simplify_ring(r) for r in geom["coordinates"]]
    elif geom.get("type") == "MultiPolygon":
        rings = [simplify_ring(r) for poly in geom["coordinates"] for r in poly]
    return [r for r in rings if r]


def geometry_bbox(rings: list[list[list[float]]]) -> list[float]:
    minx, miny, maxx, maxy = 180.0, 90.0, -180.0, -90.0
    for ring in rings:
        for x, y in ring:
            minx = min(minx, x)
            maxx = max(maxx, x)
            miny = min(miny, y)
            maxy = max(maxy, y)
    return [round(minx, PRECISION), round(miny, PRECISION), round(maxx, PRECISION), round(maxy, PRECISION)]


def geometry_area_km2(rings: list[list[list[float]]]) -> float:
    """Approximate planar area in km^2 (equirectangular with cos(lat) scaling)."""
    total = 0.0
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            dy = (y2 - y1) * math.pi / 180.0
            dx = (x2 - x1) * math.pi / 180.0
            cosy = math.cos(math.radians((y1 + y2) / 2.0))
            total += dy * dx * cosy
    area_deg2 = abs(total) / 2.0
    return round(area_deg2 * (EARTH_RADIUS_KM**2), 1)


def centroid_of(rings: list[list[list[float]]]) -> list[float]:
    """Area-weighted centroid estimate using the largest ring."""
    if not rings:
        return [0.0, 0.0]
    ring = max(rings, key=len)
    xsum = ysum = 0.0
    for x, y in ring:
        xsum += x
        ysum += y
    n = max(len(ring), 1)
    return [round(xsum / n, PRECISION), round(ysum / n, PRECISION)]


def build_countries(raw: Path) -> list[dict]:
    data = json.loads(raw.read_text())
    out = []
    for feat in data["features"]:
        props = feat.get("properties") or {}
        name = props.get("NAME") or props.get("NAME_EN") or props.get("SOVEREIGNT")
        if not name:
            continue
        rings = polygon_rings(feat.get("geometry"))
        if not rings:
            continue
        out.append(
            {
                "name": name,
                "iso": props.get("ADM0_A3") or props.get("ISO_A3") or props.get("WB_A2"),
                "names": [
                    n
                    for n in [
                        props.get("NAME"),
                        props.get("NAME_LONG"),
                        props.get("NAME_EN"),
                        props.get("NAME_ALT"),
                        props.get("NAME_SORT"),
                    ]
                    if n and isinstance(n, str)
                ],
                "continent": props.get("CONTINENT"),
                "subregion": props.get("SUBREGION"),
                "pop_est": props.get("POP_EST"),
                "bbox": geometry_bbox(rings),
                "centroid": centroid_of(rings),
                "area": geometry_area_km2(rings),
                "rings": rings,
            }
        )
    out.sort(key=lambda c: c["name"])
    return out


def build_admin1(raw: Path) -> list[dict]:
    data = json.loads(raw.read_text())
    out = []
    for feat in data["features"]:
        props = feat.get("properties") or {}
        # 50m/110m files use lowercase keys.
        name = props.get("NAME") or props.get("name")
        if not name:
            continue
        rings = polygon_rings(feat.get("geometry"))
        if not rings:
            continue
        out.append(
            {
                "name": name,
                "iso": props.get("ADM0_A3") or props.get("adm0_a3"),
                "country": props.get("ADMIN") or props.get("admin"),
                "fips": props.get("ADM1_A3") or props.get("fips"),
                "type": props.get("type_en") or props.get("type"),
                "bbox": geometry_bbox(rings),
                "centroid": centroid_of(rings),
                "area": geometry_area_km2(rings),
                "rings": rings,
            }
        )
    out.sort(key=lambda c: (c["iso"] or "", c["name"]))
    return out


def build_cities(raw: Path) -> list[dict]:
    data = json.loads(raw.read_text())
    out = []
    for feat in data["features"]:
        props = feat.get("properties") or {}
        name = props.get("NAME")
        if not name:
            continue
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates")
        if not coords:
            continue
        pop = props.get("POP_MAX") or props.get("POP_MIN") or 0
        out.append(
            {
                "n": name,
                "alt": props.get("NAME_ALT"),
                "la": round(coords[1], PRECISION),
                "lo": round(coords[0], PRECISION),
                "c": props.get("ADM0_A3"),
                "a1": props.get("ADM1NAME"),
                "p": pop or 0,
                "r": props.get("SCALERANK") or props.get("RANK") or 99,
            }
        )
    # Sort by population descending so top hits are the most relevant.
    out.sort(key=lambda c: -(c["p"] or 0))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("backend/maparr/data"))
    ap.add_argument("--raw-dir", type=Path, default=Path("backend/maparr/data/geojson"))
    args = ap.parse_args()

    out_dir = args.out
    raw_dir = args.raw_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    countries = build_countries(raw_dir / "ne_110m_admin_0_countries.geojson")
    admin1 = build_admin1(raw_dir / "ne_50m_admin_1_states_provinces.geojson")
    cities = build_cities(raw_dir / "ne_50m_populated_places.geojson")

    for name, rows in [
        ("countries.json", countries),
        ("admin1.json", admin1),
        ("cities.json", cities),
    ]:
        target = out_dir / name
        target.write_text(json.dumps(rows, separators=(",", ":")))
        print(f"{name}: {len(rows)} features, {target.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
