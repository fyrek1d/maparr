"""Map data provider registry.

Built-in providers are documented, license vetted, and offline-friendly where
noted. Providers requiring an API key read their key from ``MAPARR_PROVIDER_KEYS_<ID>``
(environment) or from the admin-managed provider key settings.

See ``docs/providers.md`` for the full matrix and licensing notes.
"""

from __future__ import annotations

import os
from typing import Any

from ..settings_store import get_custom_providers


class Provider:
    """A single tile source that Maparr can download from."""

    def __init__(self, **kw: Any) -> None:
        self.id: str = kw["id"]
        self.name: str = kw["name"]
        self.url_template: str = kw["url_template"]
        self.attribution: str = kw.get("attribution", "")
        self.license: str = kw.get("license", "")
        self.license_url: str = kw.get("license_url", "")
        self.offline_allowed: bool = kw.get("offline_allowed", True)
        self.license_note: str = kw.get("license_note", "")
        self.kind: str = kw.get("kind", "baselayer")  # baselayer | overlay
        self.format: str = kw.get("format", "png")
        self.min_zoom: int = kw.get("min_zoom", 0)
        self.max_zoom: int = kw.get("max_zoom", 19)
        self.subdomains: list[str] = kw.get("subdomains", [])
        self.requires_key: bool = kw.get("requires_key", False)
        self.key_env: str = kw.get("key_env", "")
        self.description: str = kw.get("description", "")
        self.estimated_bytes_per_tile: int = kw.get("estimated_bytes_per_tile", 16000)
        self.builtin: bool = kw.get("builtin", True)
        self.user_agent: str = kw.get("user_agent", "")

    @property
    def resolution_order(self) -> list[str]:
        """Subdomains like ``a``, ``b``, ``c`` used in the ``{s}`` token."""
        if not self.subdomains:
            return [""]
        return self.subdomains

    @property
    def env_key(self) -> str:
        return f"MAPARR_PROVIDER_KEYS_{self.id.upper().replace('-', '_')}"

    def has_key_from_env(self) -> bool:
        return bool(os.environ.get(self.env_key, ""))

    def needs_key(self) -> bool:
        return self.requires_key and not self.has_key_from_env()

    def resolved_template(self, api_key: str | None = None) -> str:
        tpl = self.url_template
        if "{key}" in tpl:
            key = api_key or os.environ.get(self.env_key, "")
            tpl = tpl.replace("{key}", key)
        return tpl

    def to_dict(self, has_key: bool = False) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "format": self.format,
            "min_zoom": self.min_zoom,
            "max_zoom": self.max_zoom,
            "subdomains": self.subdomains,
            "attribution": self.attribution,
            "license": self.license,
            "license_url": self.license_url,
            "offline_allowed": self.offline_allowed,
            "license_note": self.license_note,
            "requires_key": self.requires_key,
            "has_key": has_key or (self.requires_key and self.has_key_from_env()),
            "estimated_bytes_per_tile": self.estimated_bytes_per_tile,
            "builtin": self.builtin,
            "url_template": self.resolved_template(),
        }

    def render(self, z: int, x: int, y: int, sub: int = 0, api_key: str | None = None) -> str:
        """Build a concrete tile URL for z/x/y."""
        subs = self.resolution_order
        s = subs[sub % len(subs)] if subs and subs[0] else ""
        url = self.resolved_template(api_key)
        url = url.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
        url = url.replace("{s}", s)
        return url


def _p(**kw: Any) -> Provider:
    return Provider(**kw)


def builtin_providers() -> list[Provider]:
    return [
        _p(
            id="osm-standard",
            name="OpenStreetMap (Standard)",
            description="The default OSM basemap. Detailed street-level map of the world.",
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            attribution="© OpenStreetMap contributors",
            license="ODbL",
            license_url="https://www.openstreetmap.org/copyright",
            offline_allowed=True,
            license_note="Requires attribution. Tile usage policy applies to bulk downloads.",
            kind="baselayer",
            format="png",
            min_zoom=0,
            max_zoom=19,
            subdomains=[],
            estimated_bytes_per_tile=15000,
        ),
        _p(
            id="osm-hot",
            name="OpenStreetMap (Humanitarian HOT)",
            description="Humanitarian-focused OSM tiles, lightly styled for relief work.",
            url_template="https://tile-{s}.openstreetmap.fr/hot/{z}/{x}/{y}.png",
            attribution="© OpenStreetMap contributors",
            license="ODbL",
            license_url="https://www.openstreetmap.org/copyright",
            offline_allowed=True,
            license_note="Community tile server; be polite with download concurrency.",
            kind="baselayer",
            format="png",
            min_zoom=0,
            max_zoom=19,
            subdomains=["a", "b", "c"],
            estimated_bytes_per_tile=14000,
        ),
        _p(
            id="carto-voyager",
            name="CartoDB Voyager",
            description="Clean, modern carto basemap with a neutral palette.",
            url_template="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
            attribution="© OpenStreetMap contributors © CARTO",
            license="CC BY 4.0 / ODbL",
            license_url="https://carto.com/attributions",
            offline_allowed=True,
            license_note="Requires attribution. Optionally add an API key for higher limits.",
            kind="baselayer",
            format="png",
            min_zoom=0,
            max_zoom=20,
            subdomains=["a", "b", "c", "d"],
            requires_key=False,
            estimated_bytes_per_tile=22000,
        ),
        _p(
            id="carto-positron",
            name="CartoDB Positron (Light)",
            description="Minimal light basemap ideal for light/print maps.",
            url_template="https://{s}.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}{r}.png",
            attribution="© OpenStreetMap contributors © CARTO",
            license="CC BY 4.0 / ODbL",
            license_url="https://carto.com/attributions",
            offline_allowed=True,
            license_note="Requires attribution.",
            kind="baselayer",
            format="png",
            min_zoom=0,
            max_zoom=20,
            subdomains=["a", "b", "c", "d"],
            estimated_bytes_per_tile=12000,
        ),
        _p(
            id="opentopomap",
            name="OpenTopoMap (Topographic)",
            description="Topographic basemap with contours, relief and hillshading.",
            url_template="https://tile.opentopomap.org/{z}/{x}/{y}.png",
            attribution="© OpenStreetMap contributors, SRTM — ODbL/CC BY-SA",
            license="CC BY-SA / ODbL",
            license_url="https://opentopomap.org/credits",
            offline_allowed=True,
            license_note="Use sparingly; heavily rate-limited public tile server.",
            kind="baselayer",
            format="png",
            min_zoom=0,
            max_zoom=17,
            estimated_bytes_per_tile=45000,
        ),
        _p(
            id="cyclosm",
            name="CycleOSM (Cycling)",
            description="Cycling-focused basemap with cycle routes and infrastructure.",
            url_template="https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
            attribution="© OpenStreetMap contributors",
            license="ODbL",
            license_url="https://www.openstreetmap.org/copyright",
            offline_allowed=True,
            kind="baselayer",
            format="png",
            min_zoom=0,
            max_zoom=18,
            subdomains=["a", "b", "c"],
            estimated_bytes_per_tile=25000,
        ),
        _p(
            id="waymarked-hiking",
            name="Waymarked Trails — Hiking",
            description="Overlay of hiking routes drawn from OpenStreetMap.",
            url_template="https://tile.waymarkedtrails.org/hiking/{z}/{x}/{y}.png",
            attribution="© Waymarked Trails © OpenStreetMap contributors",
            license="ODbL",
            license_url="https://hiking.waymarkedtrails.org/#about",
            offline_allowed=True,
            kind="overlay",
            format="png",
            min_zoom=0,
            max_zoom=18,
            estimated_bytes_per_tile=12000,
        ),
        _p(
            id="waymarked-cycling",
            name="Waymarked Trails — Cycling",
            description="Overlay of cycling routes drawn from OpenStreetMap.",
            url_template="https://tile.waymarkedtrails.org/cycling/{z}/{x}/{y}.png",
            attribution="© Waymarked Trails © OpenStreetMap contributors",
            license="ODbL",
            license_url="https://cycling.waymarkedtrails.org",
            offline_allowed=True,
            kind="overlay",
            format="png",
            min_zoom=0,
            max_zoom=16,
            estimated_bytes_per_tile=12000,
        ),
        _p(
            id="waymarked-mtb",
            name="Waymarked Trails — MTB",
            description="Overlay of mountain-bike routes from OpenStreetMap.",
            url_template="https://tile.waymarkedtrails.org/mtb/{z}/{x}/{y}.png",
            attribution="© Waymarked Trails © OpenStreetMap contributors",
            license="ODbL",
            license_url="https://mtb.waymarkedtrails.org",
            offline_allowed=True,
            kind="overlay",
            format="png",
            min_zoom=0,
            max_zoom=16,
            estimated_bytes_per_tile=12000,
        ),
        _p(
            id="waymarked-slopes",
            name="Waymarked Trails — Winter Sports",
            description="Overlay of ski / winter sport routes from OpenStreetMap.",
            url_template="https://tile.waymarkedtrails.org/slopes/{z}/{x}/{y}.png",
            attribution="© Waymarked Trails © OpenStreetMap contributors",
            license="ODbL",
            license_url="https://slopes.waymarkedtrails.org",
            offline_allowed=True,
            kind="overlay",
            format="png",
            min_zoom=0,
            max_zoom=16,
            estimated_bytes_per_tile=12000,
        ),
        _p(
            id="esri-world-imagery",
            name="Esri World Imagery (Satellite)",
            description="High-resolution global satellite imagery.",
            url_template="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attribution="Esri, Maxar, Earthstar Geographics",
            license="Esri Terms of Use",
            license_url="https://www.esri.com/en-us/legal/terms/full-master-agreement",
            offline_allowed=False,
            license_note=(
                "Esri's terms permit personal/educational use with attribution but "
                "may restrict bulk caching. Verify your use case before downloading "
                "large satellite datasets or seek licensing from the imagery provider."
            ),
            kind="baselayer",
            format="jpg",
            min_zoom=0,
            max_zoom=19,
            estimated_bytes_per_tile=60000,
        ),
    ]


def load_providers(session: Any = None) -> dict[str, Provider]:
    """Return all providers (built-in + admin-defined customs) keyed by id."""
    providers = {p.id: p for p in builtin_providers()}
    if session is not None:
        for c in get_custom_providers(session):
            try:
                p = Provider(**{**c, "builtin": False, "id": c.get("id") or _slug(c["name"])})
            except KeyError:
                continue
            providers[p.id] = p
    return providers


def get_provider(provider_id: str, session: Any = None) -> Provider | None:
    return load_providers(session).get(provider_id)


def list_providers(session: Any = None) -> list[dict]:
    providers = load_providers(session)
    out = []
    for p in providers.values():
        d = p.to_dict()
        if d["requires_key"]:
            # Figure out whether the admin has set the key in the app settings.
            from ..settings_store import get_setting

            stored = get_setting(session, f"provider_key:{p.id}") if session else None
            d["has_key"] = d["has_key"] or bool(stored)
        out.append(d)
    out.sort(key=lambda d: (d["kind"] != "baselayer", d["name"].lower()))
    return out


def get_provider_key(session: Any, provider_id: str) -> str | None:
    from ..settings_store import get_setting

    stored = get_setting(session, f"provider_key:{provider_id}") if session else None
    os_key = os.environ.get(f"MAPARR_PROVIDER_KEYS_{provider_id.upper().replace('-', '_')}")
    return stored or os_key or None


def _slug(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "custom"
