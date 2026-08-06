"""Backup / restore of the Maparr data directory (DB, settings, mbtiles)."""

from __future__ import annotations

import datetime as dt
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from ..config import get_settings
from .logging import log
from .mbtiles import MBTilesReader


def _stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def create_backup(include_maps: bool = True) -> dict[str, Any]:
    """Snapshot config dir (app DB) and optionally map files into a backup dir."""
    settings = get_settings()
    backup_root = settings.resolved_backup_dir
    backup_dir = backup_root / f"maparr-{_stamp()}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 1. App SQLite database (config dir).
    db_path = _db_path(settings)
    if db_path and db_path.exists():
        target = backup_dir / "maparr.db"
        _copy_sqlite(db_path, target)
    else:
        (backup_dir / "maparr.db").touch()

    # 2. Map files (mbtiles) - hardlink when on the same filesystem to save space.
    if include_maps:
        maps_dir = backup_dir / "maps"
        maps_dir.mkdir(exist_ok=True)
        copied = 0
        for mbt in sorted(settings.resolved_data_dir.glob("*.mbtiles")):
            dest = maps_dir / mbt.name
            try:
                dest.hardlink_to(mbt)
            except OSError:
                shutil.copy2(mbt, dest)
            copied += 1
    else:
        copied = 0

    total = sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file())
    manifest = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "version": "0.1.0",
        "maps_included": copied,
        "total_bytes": total,
    }
    (backup_dir / "manifest.json").write_text(
        __import__("json").dumps(manifest, indent=2)
    )
    log.info("backup created at %s (%d maps, %d bytes)", backup_dir, copied, total)
    return {"path": str(backup_dir), "maps": copied, "bytes": total,
            "created_at": manifest["created_at"]}


def list_backups() -> list[dict]:
    settings = get_settings()
    root = settings.resolved_backup_dir
    out = []
    if root.exists():
        for d in sorted(root.iterdir(), reverse=True):
            if not d.is_dir() or not d.name.startswith("maparr-"):
                continue
            manifest = {}
            mf = d / "manifest.json"
            if mf.exists():
                manifest = __import__("json").loads(mf.read_text())
            total = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            out.append({
                "name": d.name,
                "path": str(d),
                "created_at": manifest.get("created_at", ""),
                "maps": manifest.get("maps_included", 0),
                "bytes": total,
            })
    out.sort(key=lambda b: b["name"], reverse=True)
    return out


def restore_backup(name: str, restore_maps: bool = True) -> dict[str, Any]:
    settings = get_settings()
    src = settings.resolved_backup_dir / name
    if not src.is_dir():
        raise FileNotFoundError(f"backup {name} not found")

    restored_db = False
    db_target = _db_path(settings)
    db_src = src / "maparr.db"
    if db_target and db_src.exists() and db_src.stat().st_size > 0:
        _copy_sqlite(db_src, db_target)
        restored_db = True

    restored_maps = 0
    if restore_maps:
        maps_src = src / "maps"
        if maps_src.is_dir():
            for mbt in maps_src.glob("*.mbtiles"):
                shutil.copy2(mbt, settings.resolved_data_dir / mbt.name)
                restored_maps += 1

    log.info("restored backup %s (db=%s maps=%d)", name, restored_db, restored_maps)
    return {"name": name, "restored_db": restored_db, "restored_maps": restored_maps}


def delete_backup(name: str) -> None:
    settings = get_settings()
    target = settings.resolved_backup_dir / name
    if target.is_dir() and target.name.startswith("maparr-"):
        shutil.rmtree(target)


def prune_backups(keep_days: int | None = None) -> int:
    """Delete backups older than ``keep_days`` (default from settings)."""
    settings = get_settings()
    keep_days = keep_days or settings.backup_keep_days
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=keep_days)
    removed = 0
    for b in list_backups():
        try:
            created = dt.datetime.fromisoformat(b["created_at"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
        if created < cutoff:
            delete_backup(b["name"])
            removed += 1
    return removed


def _db_path(settings) -> Path | None:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        rel = url[len("sqlite:///"):]
        p = Path(rel)
        if not p.is_absolute():
            p = settings.resolve_dir(settings.config_dir) / p
        return p
    return None


def _copy_sqlite(src: Path, dest: Path) -> None:
    """Copy a SQLite file safely (source may have open WAL)."""
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    # Use sqlite backup API when source file is the live DB.
    try:
        src_conn = sqlite3.connect(str(src))
        dest_conn = sqlite3.connect(str(tmp))
        src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()
        tmp.replace(dest)
    except sqlite3.Error:
        tmp.unlink(missing_ok=True)
        shutil.copy2(src, dest)
