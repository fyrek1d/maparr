"""Asynchronous tile download manager with pause/resume/cancel and progress."""

from __future__ import annotations

import asyncio
import datetime as dt
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db_session
from ..models import Map
from ..schemas import MapOut
from . import webhooks as webhook_svc
from .estimator import human_size
from .geometry import count_tiles_by_zoom, point_in_rings, tiles_in_bbox
from .logging import log
from .mbtiles import MBTilesWriter
from .notifications import notify
from .providers import Provider

STATUS_PENDING = "pending"
STATUS_DOWNLOADING = "downloading"
STATUS_PAUSED = "paused"
STATUS_COMPLETE = "complete"
STATUS_CANCELLED = "cancelled"
STATUS_ERROR = "error"

VALID_STATUSES = {STATUS_PENDING, STATUS_DOWNLOADING, STATUS_PAUSED, STATUS_COMPLETE,
                  STATUS_CANCELLED, STATUS_ERROR}


def map_to_out(row: Map) -> MapOut:
    out = MapOut.model_validate(row)
    if out.tiles_total > 0:
        out.percent = round(out.tiles_done / out.tiles_total * 100, 1)
    return out


@dataclass
class DownloadJob:
    map_id: str
    provider: Provider
    bbox: list[float]
    min_zoom: int
    max_zoom: int
    mask: list | None
    fmt: str
    name: str
    path: Path
    api_key: str | None = None
    concurrency: int = 8
    paused: bool = False
    cancelled: bool = False
    error: str = ""
    status: str = STATUS_PENDING
    tiles_total: int = 0
    tiles_done: int = 0
    tiles_skipped: int = 0
    bytes_done: int = 0
    speed: float = 0.0
    eta_seconds: int = 0
    started_at: float = 0.0
    task: asyncio.Task | None = field(default=None, repr=False)
    _resume_event: asyncio.Event = field(default_factory=asyncio.Event)
    _last_db_sync: float = 0.0
    _window: list[tuple[float, int]] = field(default_factory=list)

    @property
    def remaining(self) -> int:
        return max(0, self.tiles_total - self.tiles_done)


class DownloadManager:
    """Runs and tracks tile downloads across the process lifetime."""

    def __init__(self) -> None:
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            settings = get_settings()
            limits = httpx.Limits(max_connections=settings.download_concurrency * 2,
                                  max_keepalive_connections=settings.download_concurrency)
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=httpx.Timeout(settings.download_timeout_seconds),
                follow_redirects=True,
                headers={"User-Agent": settings.download_user_agent},
            )
        return self._client

    def has_job(self, map_id: str) -> bool:
        return map_id in self._jobs

    async def shutdown(self) -> None:
        """Cancel all active jobs on application shutdown."""
        for _job_id, job in list(self._jobs.items()):
            job.cancelled = True
            job._resume_event.set()
            if job.task and job.task is not asyncio.current_task():
                job.task.cancel()
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._jobs.clear()

    def get_job(self, map_id: str) -> DownloadJob | None:
        return self._jobs.get(map_id)

    def active_count(self) -> int:
        return sum(1 for j in self._jobs.values() if j.status in (STATUS_PENDING, STATUS_DOWNLOADING))

    def list_jobs(self) -> list[DownloadJob]:
        return list(self._jobs.values())

    # ------------------------------------------------------------------
    async def start(self, session: Session, map_row: Map) -> DownloadJob:
        """Begin (or resume) a download for a map row.

        Safe to call repeatedly: returns the existing job if one is active.
        """
        from .providers import get_provider, get_provider_key

        if map_id := self._jobs.get(map_row.id):
            return map_id

        provider = get_provider(map_row.provider_id, session)
        if provider is None:
            raise ValueError(f"Unknown provider {map_row.provider_id}")

        settings = get_settings()
        if self.active_count() >= settings.max_active_downloads and map_row.status not in (
            STATUS_DOWNLOADING, STATUS_PAUSED
        ):
            raise RuntimeError("Too many active downloads — pause or wait for another to finish.")

        api_key = get_provider_key(session, provider.id)
        path = Path(map_row.mbtiles_path) if map_row.mbtiles_path else self._map_path(map_row)
        job = DownloadJob(
            map_id=map_row.id,
            provider=provider,
            bbox=list(map_row.bbox),
            min_zoom=map_row.min_zoom,
            max_zoom=map_row.max_zoom,
            mask=map_row.mask,
            fmt=map_row.format,
            name=map_row.name,
            path=path,
            api_key=api_key,
            concurrency=settings.download_concurrency,
            tiles_total=map_row.tiles_total or self._compute_total(map_row),
        )
        self._jobs[map_row.id] = job
        job.task = asyncio.create_task(self._run(job))
        return job

    def _map_path(self, map_row: Map) -> Path:
        settings = get_settings()
        return settings.resolved_data_dir / f"{map_row.id}.mbtiles"

    def _compute_total(self, map_row: Map) -> int:
        by_zoom = count_tiles_by_zoom(map_row.bbox, map_row.min_zoom, map_row.max_zoom)
        return sum(by_zoom.values())

    # ------------------------------------------------------------------
    async def pause(self, map_id: str) -> DownloadJob:
        job = self._jobs.get(map_id)
        if job is None:
            raise KeyError(map_id)
        job.paused = True
        await self._persist(map_id, STATUS_PAUSED)
        self._spawn_events(map_id, "download.paused", {"status": "paused"})
        return job

    async def resume(self, map_id: str) -> DownloadJob:
        job = self._jobs.get(map_id)
        if job is None:
            raise KeyError(map_id)
        job.paused = False
        job._resume_event.set()
        await self._persist(map_id, STATUS_DOWNLOADING)
        self._spawn_events(map_id, "download.resumed", {"status": "resumed"})
        return job

    async def cancel(self, map_id: str, delete_partial: bool | None = None) -> DownloadJob:
        job = self._jobs.get(map_id)
        if job is None:
            raise KeyError(map_id)
        job.cancelled = True
        job._resume_event.set()  # unblock paused loop
        if job.task and job.task is not asyncio.current_task():
            job.task.cancel()
        settings = get_settings()
        if delete_partial is None:
            delete_partial = not settings.download_keep_partial_on_cancel
        if delete_partial:
            try:
                job.path.unlink(missing_ok=True)
                for suffix in ("-wal", "-shm"):
                    job.path.with_name(job.path.name + suffix).unlink(missing_ok=True)
            except OSError:
                pass
        await self._persist(map_id, STATUS_CANCELLED)
        self._spawn_events(map_id, "download.cancelled",
                           {"tiles_downloaded": job.tiles_done, "deleted_partial": delete_partial})
        self._jobs.pop(map_id, None)
        return job

    # ------------------------------------------------------------------
    async def _run(self, job: DownloadJob) -> None:
        job._resume_event = asyncio.Event()
        job._resume_event.set()
        job.started_at = time.time()
        await self._persist(job.map_id, STATUS_DOWNLOADING, started=True)
        self._spawn_events(job.map_id, "download.started", {"tiles_total": job.tiles_total})

        writer = MBTilesWriter(job.path, create=True)
        sem = asyncio.Semaphore(job.concurrency)
        errors_since_success = 0
        try:
            existing: dict[int, set[tuple[int, int]]] = {}
            for z in range(job.min_zoom, job.max_zoom + 1):
                existing[z] = set()
            # Load already-present tiles so resume skips them.
            try:
                with open(job.path, "rb"):
                    pass
                for z in range(job.min_zoom, job.max_zoom + 1):
                    existing[z] = self._existing_tiles(job, z)
            except OSError:
                pass

            for z in range(job.min_zoom, job.max_zoom + 1):
                x0, y0, x1, y1 = tiles_in_bbox(job.bbox, z)
                for y in range(y0, y1 + 1):
                    for x in range(x0, x1 + 1):
                        if job.cancelled:
                            raise _JobCancelled()
                        if job.paused:
                            job._resume_event.clear()
                            await job._resume_event.wait()
                            if job.cancelled:
                                raise _JobCancelled()
                        if (x, y) in existing[z]:
                            job.tiles_skipped += 1
                            continue
                        if job.mask:
                            lon, lat = _tile_center(x, y, z)
                            if not point_in_rings(lon, lat, job.mask):
                                job.tiles_skipped += 1
                                continue
                        async with sem:
                            if job.cancelled:
                                raise _JobCancelled()
                            data = await self._fetch(job, z, x, y)
                        if data is None:
                            errors_since_success += 1
                            job.tiles_skipped += 1
                            if errors_since_success > 100:
                                raise RuntimeError(
                                    "Too many consecutive tile errors — the tile server may be "
                                    "unreachable or rate limiting. Check connectivity and try again."
                                )
                            continue
                        errors_since_success = 0
                        job.tiles_done += 1
                        job.bytes_done += len(data)
                        writer.add(z, x, y, data)
                        await self._maybe_sync(job)

            writer.finish(self._metadata(job))
            job.speed = 0.0
            job.eta_seconds = 0
            await self._persist(job.map_id, STATUS_COMPLETE, finished=True)
            self._spawn_events(job.map_id, "download.completed", self._job_payload(job))
            await notify(f"Map download complete: {job.name}",
                         f"{job.tiles_done} tiles, {human_size(job.bytes_done)}", "info")
        except _JobCancelled:
            writer.close()
            return
        except asyncio.CancelledError:
            writer.close()
            raise
        except Exception as exc:  # noqa: BLE001
            job.error = str(exc)
            log.error("download failed for %s: %s", job.name, exc)
            writer.close()
            await self._persist(job.map_id, STATUS_ERROR)
            self._spawn_events(job.map_id, "download.failed", {"error": job.error})
            await notify(f"Map download failed: {job.name}", job.error, "error")
        finally:
            writer.close()
            self._jobs.pop(job.map_id, None)

    # ------------------------------------------------------------------
    def _existing_tiles(self, job: DownloadJob, z: int) -> set[tuple[int, int]]:
        import sqlite3

        try:
            conn = sqlite3.connect(str(job.path))
            rows = conn.execute(
                "SELECT tile_column, tile_row FROM tiles WHERE zoom_level=?", (z,)
            ).fetchall()
            conn.close()
            return {(int(r[0]), int(r[1])) for r in rows}
        except sqlite3.Error:
            return set()

    async def _fetch(self, job: DownloadJob, z: int, x: int, y: int) -> bytes | None:
        url = job.provider.render(z, x, y, sub=(x + y) % max(len(job.provider.resolution_order), 1),
                                  api_key=job.api_key)
        settings = get_settings()
        for attempt in range(settings.download_retries + 1):
            try:
                resp = await self._get_client().get(url)
                if resp.status_code == 200 and resp.content:
                    return resp.content
                if resp.status_code in (403, 404, 410):
                    return None  # genuinely missing tile
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", "2") or 2)
                    await asyncio.sleep(min(retry_after, 15))
                    continue
                # 5xx etc: retry with backoff
            except httpx.HTTPError:
                pass
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(settings.download_retry_backoff * (2**attempt))
        return None

    def _metadata(self, job: DownloadJob) -> dict[str, str]:
        w, s, e, n = job.bbox
        return {
            "name": job.name,
            "format": job.fmt,
            "bounds": f"{w},{s},{e},{n}",
            "minzoom": str(job.min_zoom),
            "maxzoom": str(job.max_zoom),
            "type": "overlay" if job.provider.kind == "overlay" else "baselayer",
            "version": "1",
            "description": f"Downloaded with Maparr from {job.provider.name}",
            "attribution": job.provider.attribution,
            "generator": "Maparr",
            "scheme": "xyz",
            "maparr_provider": job.provider.id,
        }

    # ------------------------------------------------------------------
    async def _maybe_sync(self, job: DownloadJob) -> None:
        now = time.time()
        if now - job._last_db_sync < 1.0:
            return
        job._last_db_sync = now
        # speed window (last 10s)
        job._window.append((now, job.bytes_done))
        job._window = [s for s in job._window if now - s[0] <= 10]
        if len(job._window) >= 2:
            dt_ = job._window[-1][0] - job._window[0][0]
            db_ = job._window[-1][1] - job._window[0][1]
            if dt_ > 0:
                job.speed = db_ / dt_
        if job.speed > 0 and job.remaining > 0 and job.tiles_done > 0:
            avg_bytes = job.bytes_done / job.tiles_done
            remaining_bytes = avg_bytes * job.remaining
            job.eta_seconds = int(remaining_bytes / job.speed)
        await self._persist(job.map_id, STATUS_DOWNLOADING)

    def _spawn_events(self, map_id: str, event: str, payload: dict) -> None:
        async def _fire():
            await webhook_svc.dispatch(event, payload)

        asyncio.ensure_future(_fire())

    def _job_payload(self, job: DownloadJob) -> dict[str, Any]:
        return {
            "map_id": job.map_id,
            "name": job.name,
            "tiles_total": job.tiles_total,
            "tiles_done": job.tiles_done,
            "bytes_done": job.bytes_done,
            "status": job.status,
        }

    # ------------------------------------------------------------------
    async def _persist(self, map_id: str, status: str, started: bool = False,
                       finished: bool = False) -> None:
        job = self._jobs.get(map_id)
        session = get_db_session()
        try:
            row = session.get(Map, map_id)
            if row is None:
                return
            if started:
                row.started_at = dt.datetime.now(dt.UTC)
                row.paused_at = None
            row.status = status
            if status == STATUS_PAUSED:
                row.paused_at = dt.datetime.now(dt.UTC)
            elif status == STATUS_DOWNLOADING and row.paused_at is not None:
                row.paused_at = None
            row.tiles_total = job.tiles_total if job else row.tiles_total
            row.tiles_done = job.tiles_done if job else row.tiles_done
            row.bytes_done = job.bytes_done if job else row.bytes_done
            row.speed = job.speed if job else 0.0
            row.eta_seconds = job.eta_seconds if job else 0
            if finished:
                row.completed_at = dt.datetime.now(dt.UTC)
                row.error = ""
                from pathlib import Path as P

                if job:
                    row.file_size = job.path.stat().st_size if job.path.exists() else 0
                else:
                    p = P(row.mbtiles_path)
                    row.file_size = p.stat().st_size if p.exists() else 0
                try:
                    from .mbtiles import MBTilesReader

                    reader = MBTilesReader(row.mbtiles_path).open()
                    row.checksum = reader.checksum()
                    reader.close()
                except Exception:
                    pass
            elif status == STATUS_ERROR:
                row.error = job.error if job else "unknown error"
            session.commit()
        finally:
            session.close()


class _JobCancelled(Exception):
    pass


def _tile_center(x: int, y: int, z: int) -> tuple[float, float]:
    from .geometry import tile_to_bbox

    lon0, lat0, lon1, lat1 = tile_to_bbox(x, y, z)
    return (lon0 + lon1) / 2.0, (lat0 + lat1) / 2.0


_manager: DownloadManager | None = None


def get_manager() -> DownloadManager:
    global _manager
    if _manager is None:
        _manager = DownloadManager()
    return _manager
