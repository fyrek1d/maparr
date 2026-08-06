"""Settings management (admin-only), notification config, and system stats."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/settings", tags=["settings"])
