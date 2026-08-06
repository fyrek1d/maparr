"""SQLAlchemy ORM models."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(16), default="user")  # admin | user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    provider: Mapped[str] = mapped_column(String(16), default="local")  # local | oidc | ldap
    provider_sub: Mapped[str] = mapped_column(String(255), default="", index=True)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bookmarks: Mapped[list[Bookmark]] = relationship(back_populates="user", cascade="all, delete-orphan")
    markers: Mapped[list[Marker]] = relationship(back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="user", cascade="all, delete-orphan")


class DownloadRegion(Base):
    """A geographic area (country / state / city / custom box) that can be downloaded."""

    __tablename__ = "download_regions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="custom")  # country | admin1 | city | custom
    iso: Mapped[str] = mapped_column(String(8), default="")
    parent_id: Mapped[str] = mapped_column(String(32), default="")
    bbox: Mapped[list] = mapped_column(JSON, default=list)  # [west, south, east, north]
    centroid: Mapped[list] = mapped_column(JSON, default=list)  # [lon, lat]
    rings: Mapped[list | None] = mapped_column(JSON, nullable=True)  # simplified polygon
    area_km2: Mapped[float] = mapped_column(Float, default=0.0)
    population: Mapped[float] = mapped_column(Float, default=0.0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (UniqueConstraint("slug", "iso", name="uq_region_slug_iso"),)


class Map(Base, TimestampMixin):
    """A downloaded map bundle: one mbtiles file for a region x provider x zoom range."""

    __tablename__ = "maps"
    __table_args__ = (UniqueConstraint("region_id", "provider_id", "min_zoom", "max_zoom",
                                       name="uq_map_region_provider_zoom"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    region_id: Mapped[str] = mapped_column(String(32), index=True)
    region_name: Mapped[str] = mapped_column(String(160), default="")
    provider_id: Mapped[str] = mapped_column(String(64), index=True)
    provider_name: Mapped[str] = mapped_column(String(120), default="")
    layer: Mapped[str] = mapped_column(String(64), default="baselayer")  # baselayer | overlay name
    format: Mapped[str] = mapped_column(String(8), default="png")
    min_zoom: Mapped[int] = mapped_column(Integer, default=0)
    max_zoom: Mapped[int] = mapped_column(Integer, default=14)
    bbox: Mapped[list] = mapped_column(JSON, default=list)  # [w,s,e,n]
    mask: Mapped[list | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|downloading|paused|cancelled|complete|error|imported
    error: Mapped[str] = mapped_column(Text, default="")

    tiles_total: Mapped[int] = mapped_column(Integer, default=0)
    tiles_done: Mapped[int] = mapped_column(Integer, default=0)
    bytes_total: Mapped[int] = mapped_column(Integer, default=0)
    bytes_done: Mapped[int] = mapped_column(Integer, default=0)
    speed: Mapped[float] = mapped_column(Float, default=0.0)
    eta_seconds: Mapped[int] = mapped_column(Integer, default=0)

    mbtiles_path: Mapped[str] = mapped_column(String(500), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), default="")
    integrity_ok: Mapped[bool] = mapped_column(Boolean, default=True)

    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    options: Mapped[dict] = mapped_column(JSON, default=dict)

    overlays: Mapped[list[MapLayer]] = relationship(back_populates="map", cascade="all, delete-orphan")


class MapLayer(Base):
    """A layer enabled/disabled for a given map bundle."""

    __tablename__ = "map_layers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    map_id: Mapped[str] = mapped_column(ForeignKey("maps.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16), default="overlay")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_zoom: Mapped[int] = mapped_column(Integer, default=14)

    map: Mapped[Map] = relationship(back_populates="overlays")


class Bookmark(Base, TimestampMixin):
    __tablename__ = "bookmarks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    zoom: Mapped[int] = mapped_column(Integer, default=10)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    color: Mapped[str] = mapped_column(String(16), default="#e11d48")
    icon: Mapped[str] = mapped_column(String(32), default="pin")
    description: Mapped[str] = mapped_column(Text, default="")
    share_token: Mapped[str] = mapped_column(String(64), default="", index=True)

    user: Mapped[User] = relationship(back_populates="bookmarks")


class Marker(Base, TimestampMixin):
    __tablename__ = "markers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(16), default="#2563eb")
    icon: Mapped[str] = mapped_column(String(32), default="pin")

    user: Mapped[User] = relationship(back_populates="markers")


class GpxTrack(Base, TimestampMixin):
    __tablename__ = "gpx_tracks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    track_type: Mapped[str] = mapped_column(String(16), default="track")  # track | route | waypoint
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    points: Mapped[int] = mapped_column(Integer, default=0)


class Webhook(Base, TimestampMixin):
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), default="")
    events: Mapped[list] = mapped_column(JSON, default=list)  # [] = all
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_delivery_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_delivery_status: Mapped[int] = mapped_column(Integer, default=0)


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    token_hash: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="api_keys")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
