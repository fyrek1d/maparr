"""Settings management (admin-only), notification config, and system stats."""

from __future__ import annotations

import datetime as dt
from typing import List
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import AdminDep, SessionDep
from ..models import Map, User, Webhook
from ..schemas import (
    NotificationConfigUpdate,
    NotificationTestResult,
    SettingUpdate,
    SystemStats,
)
from ..services import maintenance as svc_maintenance
from ..services.backup import list_backups, create_backup, restore_backup, delete_backup
from ..services.notifications import notify
from ..settings_store import get_setting, set_setting, all_settings, delete_setting

router = APIRouter(prefix="/api/settings", tags=["settings"])