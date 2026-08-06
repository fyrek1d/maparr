"""Fully offline geocoding backed by the bundled Natural Earth dataset.

Forward search matches place names (cities, admin1 divisions, countries);
reverse search finds the nearest named place plus the containing country/state.
No network access is ever required.
"""

from __future__ import annotations

import unicodedata

from .geodata import admin1, cities, countries, search_regions
from .geometry import haversine_km, point_in_rings


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


class Geocoder:
    def __init__(self) -> None:
        self._cities: list[dict] | None = None
        self._countries: list[dict] | None = None
        self._admin1: list[dict] | None = None

    def _load(self) -> tuple[list, list, list]:
        if self._cities is None:
            self._cities = cities()
            self._countries = countries()
            self._admin1 = admin1()
        return self._cities, self._countries, self._admin1

    # -- forward ---------------------------------------------------------
    def search(self, query: str, limit: int = 12) -> list[dict]:
        q = _fold(query)
        if not q:
            return []
        cities, countries, admin1 = self._load()

        results: list[dict] = []
        seen: set[str] = set()

        def add(r: dict, key: str) -> None:
            if key not in seen:
                seen.add(key)
                results.append(r)

        # Cities ranked by population, prefix matches first.
        for c in cities:
            name = _fold(c["n"])
            alt = _fold(c.get("alt") or "")
            is_prefix = name.startswith(q) or (alt and alt.startswith(q))
            is_sub = q in name or (alt and q in alt)
            if not (is_prefix or is_sub):
                continue
            add({
                "name": c["n"],
                "kind": "city",
                "display_name": _display_city(c),
                "lat": c["la"],
                "lon": c["lo"],
                "bbox": None,
                "population": c.get("p") or 0,
                "country": c.get("c") or "",
                "admin1": c.get("a1") or "",
            }, f"c:{c['lo']},{c['la']}")

        # Countries.
        for c in countries:
            variants = [c["name"], *[n for n in c.get("names") or [] if n]]
            folded = [_fold(v) for v in variants]
            if not (any(v.startswith(q) for v in folded) or any(q in v for v in folded)):
                continue
            add({
                "name": c["name"],
                "kind": "country",
                "display_name": c["name"],
                "lat": (c.get("centroid") or [0, 0])[1],
                "lon": (c.get("centroid") or [0, 0])[0],
                "bbox": c.get("bbox"),
                "population": c.get("pop_est") or 0,
                "country": "",
                "admin1": "",
            }, f"co:{c['iso']}")

        # Admin1 divisions.
        for st in admin1:
            name = _fold(st["name"])
            if not (name.startswith(q) or q in name):
                continue
            add({
                "name": st["name"],
                "kind": "admin1",
                "display_name": f"{st['name']}, {st.get('country') or ''}".strip(", "),
                "lat": (st.get("centroid") or [0, 0])[1],
                "lon": (st.get("centroid") or [0, 0])[0],
                "bbox": st.get("bbox"),
                "population": 0,
                "country": st.get("country") or "",
                "admin1": st.get("name") or "",
            }, f"a1:{st['name']}|{st.get('iso')}")

        # Rank: prefix city matches and higher population first.
        def rank(r: dict) -> tuple:
            is_city_prefix = r["kind"] == "city" and _fold(r["name"]).startswith(q)
            return (r["kind"] != "city", not is_city_prefix, -(r["population"] or 0))

        results.sort(key=rank)
        return results[:limit]

    # -- reverse -----------------------------------------------------------
    def reverse(self, lat: float, lon: float, max_distance_km: float = 250.0,
                limit: int = 5) -> list[dict]:
        cities, countries, admin1 = self._load()
        found: list[dict] = []
        for c in cities:
            dist = haversine_km(lat, lon, c["la"], c["lo"])
            if dist <= max_distance_km:
                found.append({
                    "name": c["n"],
                    "kind": "city",
                    "display_name": _display_city(c),
                    "lat": c["la"],
                    "lon": c["lo"],
                    "distance_km": round(dist, 1),
                })
        found.sort(key=lambda r: r["distance_km"])

        # Containing country / state.
        region = self._reverse_region(lat, lon)
        for r in found[:3]:
            r["region"] = region

        if not found:
            return [{"name": region["name"] if region else "Unknown region",
                     "kind": region["kind"] if region else "unknown",
                     "display_name": region["display_name"] if region else "Unknown",
                     "lat": lat, "lon": lon, "distance_km": 0.0, "region": region}]
        return found[:limit]

    def _reverse_region(self, lat: float, lon: float) -> dict | None:
        for st in self._admin1:
            if point_in_rings(lon, lat, st.get("rings") or []):
                return {"name": st["name"], "kind": "admin1",
                        "display_name": f"{st['name']}, {st.get('country') or ''}".strip(", ")}
        for c in self._countries:
            if point_in_rings(lon, lat, c.get("rings") or []):
                return {"name": c["name"], "kind": "country", "display_name": c["name"]}
        return None


def _display_city(c: dict) -> str:
    parts = [c["n"]]
    if c.get("a1"):
        parts.append(c["a1"])
    return ", ".join(parts)


_geocoder: Geocoder | None = None


def get_geocoder() -> Geocoder:
    global _geocoder
    if _geocoder is None:
        _geocoder = Geocoder()
    return _geocoder
