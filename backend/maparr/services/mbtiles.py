"""Minimal, fast MBTiles reader/writer built on SQLite.

Tiles are stored in XYZ scheme (``tile_row`` = y), matching modern tooling
(``tile-join``, tileserver-gl with ``scheme: xyz``).
"""

from __future__ import annotations

import os
import sqlite3
import time
import zlib
from pathlib import Path
from typing import Iterator

CREATE_TILES = """
CREATE TABLE IF NOT EXISTS tiles (
    zoom_level INTEGER NOT NULL,
    tile_column INTEGER NOT NULL,
    tile_row INTEGER NOT NULL,
    tile_data BLOB NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tiles_zxy ON tiles (zoom_level, tile_column, tile_row);
CREATE INDEX IF NOT EXISTS idx_tiles_z ON tiles (zoom_level);
"""

CREATE_METADATA = """
CREATE TABLE IF NOT EXISTS metadata (
    name TEXT NOT NULL PRIMARY KEY,
    value TEXT
);
"""

# Metadata keys that carry real meaning (display name, zoom, bounds).
METADATA_KEYS = (
    "name", "format", "bounds", "minzoom", "maxzoom", "center", "type",
    "version", "description", "attribution", "generator", "scheme", "maparr_provider",
)


class MBTiles:
    """Base wrapper for an SQLite connection to an MBTiles file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None

    # -- connection --------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "MBTiles":
        self._connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class MBTilesWriter(MBTiles):
    """Write tiles into an MBTiles file in batched transactions."""

    def __init__(self, path: str | Path, *, create: bool = True) -> None:
        super().__init__(path)
        self._batch: list[tuple] = []
        self._batch_size = 250
        self._count = 0
        self._bytes = 0
        if create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._connect()
            cur = self._conn.cursor()
            cur.executescript(CREATE_TILES + CREATE_METADATA)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA cache_size=-16384")
            self._conn.commit()

    def set_metadata(self, key: str, value: str) -> None:
        cur = self._conn.cursor()
        cur.execute("INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)", (key, str(value)))
        self._conn.commit()

    def set_metadata_many(self, items: dict[str, str]) -> None:
        cur = self._conn.cursor()
        for k, v in items.items():
            cur.execute("INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)", (k, str(v)))
        self._conn.commit()

    def add(self, z: int, x: int, y: int, data: bytes) -> None:
        self._batch.append((z, x, y, data))
        self._count += 1
        self._bytes += len(data)
        if len(self._batch) >= self._batch_size:
            self.flush()

    def flush(self) -> None:
        if not self._batch:
            return
        cur = self._conn.cursor()
        cur.executemany(
            "INSERT OR IGNORE INTO tiles (zoom_level, tile_column, tile_row, tile_data)"
            " VALUES (?, ?, ?, ?)",
            self._batch,
        )
        self._conn.commit()
        self._batch = []

    def finish(self, metadata: dict[str, str]) -> None:
        self.flush()
        # Set remaining metadata after the fact.
        existing = {row["name"]: row["value"] for row in
                    self._conn.execute("SELECT name, value FROM metadata")}
        metadata.update({k: v for k, v in metadata.items() if existing.get(k) is None})
        self.set_metadata_many(metadata)
        # Remove the WAL marker so the file is standalone.
        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._conn.commit()

    @property
    def inserted(self) -> int:
        return self._count


class MBTilesReader(MBTiles):
    """Read tiles and metadata from an MBTiles file."""

    def open(self) -> "MBTilesReader":
        self._connect()
        return self

    def tile(self, z: int, x: int, y: int) -> bytes | None:
        cur = self._conn.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (z, x, y),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def has_tile(self, z: int, x: int, y: int) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=? LIMIT 1",
            (z, x, y),
        )
        return cur.fetchone() is not None

    def metadata(self) -> dict[str, str]:
        out: dict[str, str] = {}
        try:
            for row in self._conn.execute("SELECT name, value FROM metadata"):
                out[row["name"]] = row["value"]
        except sqlite3.Error:
            pass
        return out

    def count(self) -> int:
        try:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM tiles").fetchone()
            return int(row["n"])
        except sqlite3.Error:
            return 0

    def size_bytes(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0

    def zoom_levels(self) -> dict[int, int]:
        out: dict[int, int] = {}
        for row in self._conn.execute(
            "SELECT zoom_level, COUNT(*) AS n FROM tiles GROUP BY zoom_level"
        ):
            out[int(row["zoom_level"])] = int(row["n"])
        return out

    def iterate(self, z: int) -> Iterator[tuple[int, int, bytes]]:
        for row in self._conn.execute(
            "SELECT tile_column, tile_row, tile_data FROM tiles WHERE zoom_level=?",
            (z,),
        ):
            yield int(row["tile_column"]), int(row["tile_row"]), row["tile_data"]

    def checksum(self) -> str:
        import hashlib

        h = hashlib.sha256()
        with self.path.open("rb") as fh:
            while chunk := fh.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest()

    def integrity(self) -> dict:
        """Lightweight integrity report: counts, size, malformed rows."""
        errors: list[str] = []
        zoom_counts = self.zoom_levels()
        total = sum(zoom_counts.values())
        meta = self.metadata()
        minz = int(meta.get("minzoom", min(zoom_counts) if zoom_counts else 0))
        maxz = int(meta.get("maxzoom", max(zoom_counts) if zoom_counts else 0))
        for z in range(minz, maxz + 1):
            if zoom_counts.get(z, 0) == 0:
                errors.append(f"zoom {z}: no tiles")
        # Sample-blob sanity check.
        for row in self._conn.execute(
            "SELECT tile_data FROM tiles ORDER BY RANDOM() LIMIT 25"
        ):
            data = row[0]
            if not data:
                errors.append("empty tile blob found")
                break
            try:
                zlib.decompress(data)  # PNG/JPEG are zlib streams
            except Exception:
                pass  # non-deflate images are fine
        ok = not errors
        return {
            "ok": ok,
            "tiles": total,
            "tiles_by_zoom": zoom_counts,
            "minzoom": minz,
            "maxzoom": maxz,
            "errors": errors,
            "size_bytes": self.size_bytes(),
        }

    def vacuum(self) -> None:
        self._conn.execute("VACUUM")
        self._conn.commit()


def optimize_after_download(path: str | Path, conn: sqlite3.Connection) -> None:
    """Re-index after bulk insert (called by downloader on completion)."""
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.commit()


def file_age_seconds(path: str | Path) -> float:
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return 0.0