"""Key/value settings stored in the database.

These settings are administrator-managed and override environment defaults at
runtime (e.g. OIDC providers, notification targets, custom tile providers).
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .models import Setting

PREFIX = "maparr:"


def get_setting(session: Session, key: str, default: Any = None) -> Any:
    row = session.get(Setting, PREFIX + key)
    if row is None:
        return default
    try:
        return json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return row.value


def set_setting(session: Session, key: str, value: Any) -> None:
    row = session.get(Setting, PREFIX + key)
    payload = json.dumps(value) if not isinstance(value, str) else value
    if row is None:
        session.add(Setting(key=PREFIX + key, value=payload))
    else:
        row.value = payload
    session.commit()


def delete_setting(session: Session, key: str) -> bool:
    row = session.get(Setting, PREFIX + key)
    if row is not None:
        session.delete(row)
        session.commit()
        return True
    return False


def all_settings(session: Session) -> dict[str, Any]:
    rows = session.query(Setting).filter(Setting.key.like(PREFIX + "%")).all()
    out: dict[str, Any] = {}
    for r in rows:
        key = r.key[len(PREFIX):]
        try:
            out[key] = json.loads(r.value)
        except (json.JSONDecodeError, TypeError):
            out[key] = r.value
    return out


# --- Structured settings helpers ----------------------------------------------

OIDC_KEY = "oidc_providers"
CUSTOM_PROVIDERS_KEY = "custom_providers"
NOTIFY_KEY = "notification_config"
LDAP_KEY = "ldap_config"


def get_oidc_providers(session: Session) -> list[dict]:
    return get_setting(session, OIDC_KEY, [])


def get_custom_providers(session: Session) -> list[dict]:
    return get_setting(session, CUSTOM_PROVIDERS_KEY, [])


def get_notify_config(session: Session) -> dict:
    return get_setting(session, NOTIFY_KEY, {}) or {}


def get_ldap_config(session: Session) -> dict:
    return get_setting(session, LDAP_KEY, {}) or {}
