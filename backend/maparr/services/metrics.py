"""Prometheus metrics."""

from __future__ import annotations

import prometheus_client as prom

NAMESPACE = "maparr"

TILE_SERVED = prom.Counter(
    f"{NAMESPACE}_tiles_served_total", "Tiles served from local storage", ["format"]
)
TILE_CACHE_HITS = prom.Counter(f"{NAMESPACE}_tile_cache_hits_total", "Tile cache hits")
TILE_CACHE_MISSES = prom.Counter(f"{NAMESPACE}_tile_cache_misses_total", "Tile cache misses")
DOWNLOADS_STARTED = prom.Counter(f"{NAMESPACE}_downloads_started_total", "Downloads started")
DOWNLOADS_COMPLETED = prom.Counter(f"{NAMESPACE}_downloads_completed_total", "Downloads completed")
DOWNLOADS_FAILED = prom.Counter(f"{NAMESPACE}_downloads_failed_total", "Downloads failed")
DOWNLOAD_TILES_TOTAL = prom.Counter(f"{NAMESPACE}_download_tiles_total", "Tiles downloaded")
DOWNLOAD_BYTES_TOTAL = prom.Counter(f"{NAMESPACE}_download_bytes_total", "Bytes downloaded")
HTTP_REQUESTS = prom.Counter(
    f"{NAMESPACE}_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
ACTIVE_DOWNLOADS = prom.Gauge(f"{NAMESPACE}_active_downloads", "Currently active downloads")
MAPS_TOTAL = prom.Gauge(f"{NAMESPACE}_maps_total", "Total maps stored")
STORAGE_BYTES = prom.Gauge(f"{NAMESPACE}_storage_bytes", "Total bytes of map storage")
GEOSEARCH_REQUESTS = prom.Counter(f"{NAMESPACE}_geosearch_requests_total", "Geocoding searches")


def set_storage_gauge(bytes_total: int) -> None:
    STORAGE_BYTES.set(bytes_total)


def set_maps_gauge(count: int) -> None:
    MAPS_TOTAL.set(count)


def set_active_downloads(count: int) -> None:
    ACTIVE_DOWNLOADS.set(count)


def generate_metrics() -> str:
    return prom.generate_latest().decode("utf-8")
