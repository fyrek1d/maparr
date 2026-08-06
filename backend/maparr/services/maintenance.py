"""Scheduled maintenance tasks (integrity checks, cleanup, storage stats)."""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any

from ..config import get_settings
from ..db import get_db_session
from ..models import Map
from .backup import prune_backups
from .logging import log
from .mbtiles import MBTilesReader
from .metrics import set_maps_gauge, set_storage_gauge
from .tile_server import clear_reader_pool

CHECKING = object()


class MaintenanceLoop:
    """Runs periodic maintenance while the application is up."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run())
            log.debug("maintenance loop started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (TimeoutError, asyncio.CancelledError):
                self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        settings = get_settings()
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=settings.maintenance_interval_seconds)
            except TimeoutError:
                pass
            if self._stop.is_set():
                break
            try:
                await asyncio.to_thread(self.tick)
            except Exception as exc:  # noqa: BLE001
                log.error("maintenance tick failed: %s", exc)

    # -- one tick ---------------------------------------------------------
    def tick(self) -> dict[str, Any]:
        settings = get_settings()
        report: dict[str, Any] = {"ok": True}

        # Storage gauges.
        session = get_db_session()
        try:
            maps = session.query(Map).filter(
                Map.status.in_(["complete", "imported"])
            ).all()
            set_maps_gauge(len(maps))
            total = sum(m.file_size for m in maps)
            set_storage_gauge(total)
        finally:
            session.close()

        # Prune old backups.
        try:
            pruned = prune_backups()
            report["pruned_backups"] = pruned
        except Exception as exc:  # noqa: BLE001
            report["prune_error"] = str(exc)

        # Temp cleanup (older than 24h).
        cleaned = 0
        tmp_dir = settings.resolved_tmp_dir
        if tmp_dir.exists():
            cutoff = dt.datetime.now().timestamp() - 86400
            for f in tmp_dir.iterdir():
                try:
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        f.unlink()
                        cleaned += 1
                except OSError:
                    pass
        report["cleaned_temp_files"] = cleaned

        # Refresh tile reader pool to drop stale handles.
        clear_reader_pool()
        return report

    # -- ad-hoc integrity --------------------------------------------------
    def integrity_check(self, map_id: str | None = None) -> list[dict]:
        session = get_db_session()
        try:
            q = session.query(Map)
            if map_id:
                q = q.filter(Map.id == map_id)
            maps = q.all()
            results = []
            for m in maps:
                if not m.mbtiles_path:
                    continue
                try:
                    reader = MBTilesReader(m.mbtiles_path).open()
                    rep = reader.integrity()
                    reader.close()
                    m.integrity_ok = rep["ok"]
                    if m.status in ("complete", "imported") and m.tiles_done == 0:
                        m.tiles_done = rep["tiles"]
                    session.commit()
                    results.append({"map_id": m.id, "name": m.name, "ok": rep["ok"],
                                    "tiles": rep["tiles"], "errors": rep["errors"]})
                except Exception as exc:  # noqa: BLE001
                    results.append({"map_id": m.id, "name": m.name, "ok": False,
                                    "tiles": 0, "errors": [str(exc)]})
            return results
        finally:
            session.close()


_maintenance: MaintenanceLoop | None = None


def get_maintenance() -> MaintenanceLoop:
    global _maintenance
    if _maintenance is None:
        _maintenance = MaintenanceLoop()
    return _maintenance
