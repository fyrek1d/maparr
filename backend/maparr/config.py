"""Application configuration loaded from environment variables and .env files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotificationSettings(BaseSettings):
    """Optional outbound notification targets."""

    ntfy_url: str = ""
    ntfy_topic: str = "maparr"
    ntfy_token: str = ""
    webhook_url: str = ""
    webhook_headers: dict[str, str] = Field(default_factory=dict)
    webhook_template: str = ""


class LdapSettings(BaseSettings):
    """Optional LDAP / Active Directory authentication."""

    enabled: bool = False
    url: str = "ldap://localhost:389"
    bind_dn: str = ""
    bind_password: str = ""
    user_base_dn: str = ""
    user_filter: str = "(uid={username})"
    user_attr_map: dict[str, str] = Field(default_factory=lambda: {"username": "uid", "email": "mail"})
    default_role: str = "user"


class Settings(BaseSettings):
    """Maparr runtime configuration.

    Every field maps to ``MAPARR_<FIELD>`` environment variables. Sensitive
    values should be supplied via environment or a secrets file, never
    committed to a repository.
    """

    model_config = SettingsConfigDict(
        env_prefix="MAPARR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Paths -----------------------------------------------------------
    data_dir: Path = Path("data/maps")
    config_dir: Path = Path("data")
    backup_dir: Path = Path("data/backups")
    tmp_dir: Path = Path("data/tmp")

    # --- Database ---------------------------------------------------------
    database_url: str = "sqlite:///./data/maparr.db"

    # --- Security ---------------------------------------------------------
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 30
    allow_registration: bool = False
    cookie_secure: bool = True
    max_api_keys_per_user: int = 10

    # --- CORS ---------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # --- Logging -------------------------------------------------------------
    log_level: str = "info"
    json_logs: bool = False

    # --- Downloads -----------------------------------------------------------
    download_concurrency: int = 8
    download_timeout_seconds: float = 20.0
    download_retries: int = 3
    download_retry_backoff: float = 1.5
    download_user_agent: str = "Maparr/0.1.0 (+https://github.com/maparr/maparr)"
    download_keep_partial_on_cancel: bool = True
    download_max_redirects: int = 5
    max_active_downloads: int = 3

    # --- Tile serving ---------------------------------------------------------
    tile_cache_size: int = 2048
    tile_cache_ttl: int = 3600
    tile_max_age: int = 86400

    # --- Geocoding ------------------------------------------------------------
    geocoder_max_results: int = 12
    geocoder_max_distance_km: float = 250.0

    # --- Observability ----------------------------------------------------------
    metrics_enabled: bool = True

    # --- Authentication backends ------------------------------------------------
    ldap: LdapSettings = LdapSettings()
    notifications: NotificationSettings = NotificationSettings()

    # --- Maintenance / backups ---------------------------------------------------
    backup_keep_days: int = 30
    maintenance_interval_seconds: int = 3600
    integrity_check_interval_seconds: int = 86400

    # --- Storage ------------------------------------------------------------------
    max_map_bytes: int = 512 * 1024 * 1024 * 1024  # 512 GiB safety cap

    # --- Misc ---------------------------------------------------------------------
    onboarding_required: bool = True
    server_hostname: str = "localhost"
    public_base_url: str = ""

    # --- First admin (created during onboarding if no users exist) ------------------
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = ""
    bootstrap_admin_email: str = "admin@localhost"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    def resolve_dir(self, p: Path) -> Path:
        return p.expanduser().resolve()

    @property
    def resolved_data_dir(self) -> Path:
        return self.resolve_dir(self.data_dir)

    @property
    def resolved_config_dir(self) -> Path:
        return self.resolve_dir(self.config_dir)

    @property
    def resolved_backup_dir(self) -> Path:
        return self.resolve_dir(self.backup_dir)

    @property
    def resolved_tmp_dir(self) -> Path:
        return self.resolve_dir(self.tmp_dir)

    def ensure_dirs(self) -> None:
        for d in (self.resolved_data_dir, self.resolved_config_dir,
                  self.resolved_backup_dir, self.resolved_tmp_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
