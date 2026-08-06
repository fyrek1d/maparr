"""Geographic data loading and region lookup (Natural Earth, public domain).

Loads the compact bundles produced by ``scripts/build_geodata.py`` and offers
name search, country -> states traversal, and bbox / geometry access.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import get_settings

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _load(name: str) -> list[dict]:
    path = DATA_DIR / name
    if not path.exists():
        return []
    return json.loads(path.read_text())


@lru_cache(maxsize=1)
def countries() -> list[dict]:
    return _load("countries.json")


@lru_cache(maxsize=1)
def admin1() -> list[dict]:
    return _load("admin1.json")


@lru_cache(maxsize=1)
def cities() -> list[dict]:
    return _load("cities.json")


@lru_cache(maxsize=1)
def admin1_by_iso() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for f in admin1():
        out.setdefault(f["iso"] or "", []).append(f)
    return out


@lru_cache(maxsize=1)
def countries_by_iso() -> dict[str, dict]:
    return {c["iso"]: c for c in countries() if c.get("iso")}


def find_country(iso: str | None = None, name: str | None = None) -> dict | None:
    if iso:
        return countries_by_iso().get(iso.upper())
    if name:
        name = name.lower()
        for c in countries():
            for n in (c.get("name") or "", *c.get("names") or []):
                if n and n.lower() == name:
                    return c
    return None


def search_regions(query: str, limit: int = 20) -> list[dict]:
    """Search countries, admin1 divisions and cities by name."""
    q = query.strip().lower()
    if not q:
        return []
    results: list[dict] = []

    # Country + admin1 prefix / substring matches.
    for c in countries():
        names = _name_variants(c)
        if any(n.startswith(q) for n in names) or any(q in n for n in names):
            results.append({
                "name": c["name"],
                "slug": c["name"].lower().replace(" ", "-"),
                "kind": "country",
                "iso": c.get("iso", ""),
                "country": "",
                "bbox": c["bbox"],
                "centroid": c.get("centroid", []),
                "area_km2": c.get("area", 0.0),
                "population": c.get("pop_est") or 0.0,
            })
            if len(results) >= limit:
                # prefer countries where exact prefix matched
                break

    # States for matching country (only if the country matched above to avoid noise)
    matched_isos = {r["iso"] for r in results if r["kind"] == "country"}
    for iso in list(matched_isos)[:5]:
        for st in admin1_by_iso().get(iso, []):
            if st["name"].lower().startswith(q) or q in st["name"].lower():
                results.append({
                    "name": st["name"],
                    "slug": st["name"].lower().replace(" ", "-"),
                    "kind": "admin1",
                    "iso": st.get("iso", ""),
                    "country": st.get("country", ""),
                    "bbox": st["bbox"],
                    "centroid": st.get("centroid", []),
                    "area_km2": st.get("area", 0.0),
                    "population": 0.0,
                })

    # Cities (top matches by population).
    for city in cities():
        name = city["n"]
        if name.lower().startswith(q) or q in name.lower():
            results.append({
                "name": name,
                "slug": name.lower().replace(" ", "-"),
                "kind": "city",
                "iso": city.get("c", ""),
                "country": city.get("c", "") or "",
                "bbox": _city_bbox(city),
                "centroid": [city["lo"], city["la"]],
                "area_km2": 0.0,
                "population": city.get("p") or 0.0,
            })
        if len(results) >= limit:
            return results
    return results[:limit]


def _city_bbox(city: dict, radius_deg: float = 0.15) -> list[float]:
    radius_deg = max(0.02, min(2.0, radius_deg))
    return [city["lo"] - radius_deg, city["la"] - radius_deg,
            city["lo"] + radius_deg, city["la"] + radius_deg]


def _name_variants(obj: dict) -> list[str]:
    n = obj.get("name") or ""
    extras = [x for x in obj.get("names") or [] if isinstance(x, str)]
    return list(dict.fromkeys([n, *extras]))


def region_rings(region: dict | None) -> list[list[list[float]]] | None:
    if not region:
        return None
    rings = region.get("rings")
    return rings if rings else None


def country_children(country_name: str) -> list[dict]:
    c = find_country(name=country_name)
    if not c:
        return []
    return admin1_by_iso().get(c.get("iso") or "", [])


def region_info(region: dict) -> dict[str, Any]:
    """Convert a geodata record into the standard RegionOut shape."""
    return region