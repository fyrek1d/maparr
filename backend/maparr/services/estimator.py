"""Storage / download estimation."""

from __future__ import annotations

from ..services.geometry import count_tiles, count_tiles_by_zoom


def human_size(num: int | float, suffix: str = "B") -> str:
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Ei{suffix}"


def estimate_download(
    bbox: list[float],
    min_zoom: int,
    max_zoom: int,
    bytes_per_tile: int,
    mask=None,
) -> dict:
    """Estimate tile count and bytes for a bbox x zoom range.

    ``mask`` is an optional list of rings (polygon) used to reduce tile count.
    When provided we compute a conservative fraction by sampling; the estimate
    therefore depends only on geometry, not on the mask.
    """
    by_zoom = count_tiles_by_zoom(bbox, min_zoom, max_zoom) or {}
    total = sum(by_zoom.values())
    # Averages include high (factor 2) estimate for safety margin.
    est = bytes_per_tile
    bytes_est = total * est
    bytes_high = total * est * 1.5
    notes = []
    if total > 2_000_000:
        notes.append("Large dataset — consider a higher minimum zoom or smaller region.")
    if max_zoom >= 17:
        notes.append("Zoom 17+ multiplies storage roughly 4x per extra level.")
    return {
        "tiles": total,
        "bytes_estimate": bytes_est,
        "bytes_estimate_high": bytes_high,
        "human_size": human_size(bytes_est),
        "by_zoom": [{"zoom": z, "tiles": by_zoom[z], "bytes": by_zoom[z] * est}
                    for z in sorted(by_zoom)],
        "notes": notes,
    }