"""Pydantic request/response schemas for the REST API."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(default="", max_length=255)
    password: str = Field(min_length=8, max_length=255)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=255)
    role: str | None = Field(default=None, pattern="^(admin|user)$")
    is_active: bool | None = None


class UserOut(ORMModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    provider: str
    last_login_at: dt.datetime | None = None
    created_at: dt.datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=lambda: ["read"])


class ApiKeyOut(ORMModel):
    id: str
    name: str
    scopes: list[str]
    created_at: dt.datetime
    last_used_at: dt.datetime | None = None


class ApiKeyCreated(ApiKeyOut):
    token: str  # shown exactly once


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=255)


# --- Regions ------------------------------------------------------------------

class RegionOut(BaseModel):
    id: str
    slug: str
    name: str
    kind: str
    iso: str
    parent_id: str
    bbox: list[float]
    centroid: list[float]
    area_km2: float
    population: float
    meta: dict = Field(default_factory=dict)


class RegionSearchResult(BaseModel):
    id: str | None
    slug: str | None
    name: str
    kind: str
    iso: str
    country: str = ""
    bbox: list[float]
    centroid: list[float]
    area_km2: float = 0.0
    population: float = 0.0


# --- Providers ---------------------------------------------------------------

class ProviderOut(BaseModel):
    id: str
    name: str
    description: str = ""
    kind: str = "baselayer"
    format: str = "png"
    min_zoom: int
    max_zoom: int
    subdomains: list[str] = Field(default_factory=list)
    attribution: str = ""
    license: str = ""
    license_url: str = ""
    offline_allowed: bool = True
    license_note: str = ""
    requires_key: bool = False
    has_key: bool = False
    estimated_bytes_per_tile: int = 16000
    builtin: bool = True
    url_template: str = ""


class CustomProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url_template: str = Field(min_length=1, max_length=500)
    subdomains: list[str] = Field(default_factory=list)
    attribution: str = ""
    license: str = ""
    kind: str = Field(default="baselayer", pattern="^(baselayer|overlay)$")
    format: str = Field(default="png", pattern="^(png|webp|jpg)$")
    min_zoom: int = 0
    max_zoom: int = 18
    estimated_bytes_per_tile: int = 16000


class ProviderKeyUpdate(BaseModel):
    key: str = Field(min_length=1, max_length=500)


# --- Map / download -----------------------------------------------------------

class ZoomRange(BaseModel):
    min_zoom: int = Field(ge=0, le=22)
    max_zoom: int = Field(ge=0, le=22)

    @field_validator("max_zoom")
    @classmethod
    def _check(cls, v, info):
        if info.data.get("min_zoom") is not None and v < info.data["min_zoom"]:
            raise ValueError("max_zoom must be >= min_zoom")
        return v


class DownloadCreate(BaseModel):
    provider_id: str
    region_id: str
    region_name: str = ""
    bbox: list[float] = Field(min_length=4, max_length=4)
    min_zoom: int = Field(ge=0, le=22, default=0)
    max_zoom: int = Field(ge=0, le=22, default=14)
    name: str = ""
    mask_to_region: bool = True
    options: dict = Field(default_factory=dict)

    @field_validator("max_zoom")
    @classmethod
    def _check_zoom(cls, v, info):
        if info.data.get("min_zoom") is not None and v < info.data["min_zoom"]:
            raise ValueError("max_zoom must be >= min_zoom")
        return v


class EstimateRequest(DownloadCreate):
    pass


class DownloadEstimate(BaseModel):
    tiles: int
    bytes_estimate: int
    bytes_estimate_high: int
    human_size: str
    by_zoom: list[dict]
    notes: list[str] = Field(default_factory=list)


class MapOut(ORMModel):
    id: str
    name: str
    region_id: str
    region_name: str
    provider_id: str
    provider_name: str
    layer: str
    format: str
    min_zoom: int
    max_zoom: int
    bbox: list[float]
    status: str
    error: str
    tiles_total: int
    tiles_done: int
    bytes_total: int
    bytes_done: int
    speed: float
    eta_seconds: int
    file_size: int
    checksum: str
    integrity_ok: bool
    started_at: dt.datetime | None
    completed_at: dt.datetime | None
    paused_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime
    percent: float = 0.0


class MapDetail(MapOut):
    overlays: list[MapLayerOut] = Field(default_factory=list)


class MapLayerOut(ORMModel):
    id: str
    map_id: str
    name: str
    kind: str
    enabled: bool
    max_zoom: int


class MapLayerUpdate(BaseModel):
    enabled: bool
    max_zoom: int | None = None


class MapImport(BaseModel):
    path: str = Field(min_length=1)
    name: str = ""
    region_name: str = ""
    min_zoom: int | None = None
    max_zoom: int | None = None
    overlay: bool = False


class StorageBreakdown(BaseModel):
    total_bytes: int
    total_human: str
    maps: list[dict]


class IntegrityResult(BaseModel):
    map_id: str
    name: str
    ok: bool
    tiles: int
    errors: list[str] = Field(default_factory=list)


# --- Bookmarks / markers / gpx ---------------------------------------------------

class BookmarkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    zoom: int = Field(ge=0, le=22, default=10)
    is_favorite: bool = False
    color: str = "#e11d48"
    description: str = ""


class BookmarkUpdate(BaseModel):
    name: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    zoom: int | None = Field(default=None, ge=0, le=22)
    is_favorite: bool | None = None
    color: str | None = None
    description: str | None = None


class BookmarkOut(ORMModel):
    id: str
    name: str
    lat: float
    lon: float
    zoom: int
    is_favorite: bool
    color: str
    description: str
    share_token: str
    created_at: dt.datetime


class BookmarkShare(BaseModel):
    share_token: str


class MarkerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    description: str = ""
    color: str = "#2563eb"
    icon: str = "pin"


class MarkerUpdate(BaseModel):
    name: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    description: str | None = None
    color: str | None = None
    icon: str | None = None


class MarkerOut(ORMModel):
    id: str
    name: str
    lat: float
    lon: float
    description: str
    color: str
    icon: str
    created_at: dt.datetime


class GpxImportResult(BaseModel):
    tracks: list[dict]
    routes: list[dict]
    waypoints: list[dict]


# --- Search -----------------------------------------------------------------

class SearchResult(BaseModel):
    name: str
    kind: str
    display_name: str
    lat: float
    lon: float
    bbox: list[float] | None = None
    population: float = 0.0
    country: str = ""
    admin1: str = ""


class ReverseGeocodeResult(BaseModel):
    name: str
    kind: str
    display_name: str
    lat: float
    lon: float
    distance_km: float


# --- Webhooks ---------------------------------------------------------------

class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=500)
    secret: str = ""
    events: list[str] = Field(default_factory=list)
    is_active: bool = True


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    secret: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookOut(ORMModel):
    id: str
    name: str
    url: str
    events: list[str]
    is_active: bool
    last_delivery_at: dt.datetime | None
    last_delivery_status: int
    created_at: dt.datetime


class WebhookTestResult(BaseModel):
    status: int
    ok: bool
    latency_ms: int
    message: str = ""


# --- Settings ---------------------------------------------------------------

class SettingUpdate(BaseModel):
    key: str
    value: str


class OnboardingStatus(BaseModel):
    setup_complete: bool
    users_exist: bool
    settings_configured: bool
    next_steps: list[str] = Field(default_factory=list)


class OnboardingCreateAdmin(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = ""
    password: str = Field(min_length=8, max_length=255)


class NotificationConfigUpdate(BaseModel):
    ntfy_url: str = ""
    ntfy_topic: str = "maparr"
    ntfy_token: str = ""
    webhook_url: str = ""
    webhook_template: str = ""


class NotificationTestResult(BaseModel):
    ok: bool
    detail: str = ""


class MaintenanceResult(BaseModel):
    ok: bool
    action: str
    detail: str = ""
    removed_bytes: int = 0
    freed_bytes: int = 0


# --- Health / misc --------------------------------------------------------------

class HealthStatus(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    downloads_active: int
    storage_bytes: int
    maps_count: int
    details: dict = Field(default_factory=dict)


class SystemStats(BaseModel):
    maps_count: int
    total_bytes: int
    by_provider: list[dict]
    by_region: list[dict]
    active_downloads: int
    tiles_served: int
    tile_cache_hit_rate: float
    db_size_bytes: int
    disk_free_bytes: int
    uptime_seconds: float


MapDetail.model_rebuild()
