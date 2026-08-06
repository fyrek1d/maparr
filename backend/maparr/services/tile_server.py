"""Tile serving with an LRU in-memory cache."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

from sqlalchemy.orm import Session

from ..db import get_db_session
from ..models import Map
from .logging import log
from .mbtiles import MBTilesReader
from .metrics import TILE_CACHE_HITS, TILE_CACHE_MISSES, TILE_SERVED

CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "pbf": "application/x-protobuf",
}

# Keep a pool of open readers keyed by path (avoids reopening per request).
_reader_pool: dict[str, MBTilesReader] = {}


@dataclass
class TileResult:
    data: bytes
    content_type: str
    map_id: str | None = None
    hit_cache: bool = False


class TileCache:
    """Thread-safe LRU byte cache for decoded tile responses."""

    def __init__(self, max_items: int = 2048, ttl: int = 3600) -> None:
        self.max_items = max_items
        self.ttl = ttl
        self._data: OrderedDict[tuple, tuple[float, TileResult]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: tuple) -> TileResult | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            ts, result = item
            if time.time() - ts > self.ttl:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return result

    def put(self, key: tuple, result: TileResult) -> None:
        with self._lock:
            self._data[key] = (time.time(), result)
            self._data.move_to_end(key)
            while len(self._data) > self.max_items:
                self._data.popitem(last=False)


def _active_maps(session: Session) -> list[Map]:
    return session.query(Map).filter(Map.status.in_(["complete", "imported"])).all()


def find_tile(session: Session, z: int, x: int, y: int,
              map_id: str | None = None, cache: TileCache | None = None,
              base_layer_only: bool = False) -> TileResult | None:
    """Look up a tile across completed maps.

    When ``map_id`` is given only that map is searched. Otherwise the most
    specific base layer (smallest map covering this tile at this zoom) wins,
    and any matching enabled overlay is stacked on top.
    """
    key = ("tile", map_id or "*", z, x, y)
    if cache:
        cached = cache.get(key)
        if cached is not None:
            TILE_CACHE_HITS.inc()
            return cached

    maps = _active_maps(session)
    if not maps:
        TILE_CACHE_MISSES.inc()
        return None

    bbox = _tile_bbox(z, x, y)
    candidates = [m for m in maps if _covers(m, bbox, z)]
    if map_id:
        candidates = [m for m in candidates if m.id == map_id]
    if not candidates:
        TILE_CACHE_MISSES.inc()
        return None

    if base_layer_only:
        candidates = [m for m in candidates if m.layer == "baselayer"]

    # Pick the base layer that is best zoom-matched (smallest max_zoom >= z).
    def _area(m: Map) -> float:
        mw, ms, me, mn = m.bbox
        return (me - mw) * (mn - ms)

    base = None
    for m in sorted(candidates, key=lambda m: (m.layer != "baselayer", m.max_zoom, _area(m))):
        if m.layer == "baselayer":
            base = m
            break
    if base is None:
        base = min(candidates, key=lambda m: m.max_zoom)

    data = _read_tile(base, z, x, y)
    if data is None:
        TILE_CACHE_MISSES.inc()
        return None
    result = TileResult(data=data, content_type=CONTENT_TYPES.get(base.format, "image/png"),
                        map_id=base.id)
    if cache:
        cache.put(key, result)
        TILE_CACHE_MISSES.inc()
    TILE_SERVED.inc()
    return result


def _read_tile(m: Map, z: int, x: int, y: int) -> bytes | None:
    if not m.mbtiles_path:
        return None
    reader = _reader_pool.get(m.mbtiles_path)
    if reader is None:
        try:
            reader = MBTilesReader(m.mbtiles_path).open()
            _reader_pool[m.mbtiles_path] = reader
        except Exception as exc:  # noqa: BLE001
            log.warning("failed to open %s: %s", m.mbtiles_path, exc)
            return None
    try:
        return reader.tile(z, x, y)
    except Exception as exc:  # noqa: BLE001
        log.warning("tile read error in %s: %s", m.mbtiles_path, exc)
        return None


def _tile_bbox(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    from .geometry import tile_to_bbox

    lon0, lat1, lon1, lat0 = tile_to_bbox(x, y, z)
    return (lon0, lat0, lon1, lat1)


def _covers(m: Map, bbox: tuple[float, float, float, float], z: int) -> bool:
    w, s, e, n = bbox
    mw, ms, me, mn = m.bbox
    return w >= mw and e <= me and s >= ms and n <= mn and m.min_zoom <= z <= m.max_zoom


_cache: TileCache | None = None


def get_cache() -> TileCache:
    global _cache
    if _cache is None:
        from ..config import get_settings

        s = get_settings()
        _cache = TileCache(max_items=s.tile_cache_size, ttl=s.tile_cache_ttl)
    return _cache


def clear_reader_pool(path: str | None = None) -> None:
    if path is None:
        _reader_pool.clear()
    else:
        r = _reader_pool.pop(path, None)
        if r:
            r.close()
