"""Webhook dispatch with HMAC signing."""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import hmac
import json
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db_session
from ..models import Webhook
from .logging import log

ALL_EVENTS = (
    "download.started",
    "download.progress",
    "download.completed",
    "download.failed",
    "download.cancelled",
    "download.paused",
    "download.resumed",
    "map.imported",
    "map.deleted",
    "region.updated",
    "backup.created",
    "backup.restored",
    "maintenance.completed",
    "user.created",
    "system.health",
)


def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _load_webhooks(session: Session) -> list[Webhook]:
    return session.query(Webhook).filter(Webhook.is_active.is_(True)).all()


async def _deliver(client: httpx.AsyncClient, webhook: Webhook, event: str,
                  payload: dict[str, Any]) -> None:
    body = json.dumps({"event": event, "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "data": payload}).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "Maparr/0.1"}
    if webhook.secret:
        headers["X-Maparr-Signature"] = "sha256=" + _sign(body, webhook.secret)
    started = time.monotonic()
    try:
        resp = await client.post(webhook.url, content=body, headers=headers, timeout=15.0)
        status = resp.status_code
    except httpx.HTTPError:
        status = 0
    latency_ms = int((time.monotonic() - started) * 1000)
    session = get_db_session()
    try:
        row = session.get(Webhook, webhook.id)
        if row:
            row.last_delivery_at = dt.datetime.now(dt.timezone.utc)
            row.last_delivery_status = status
            session.commit()
    finally:
        session.close()
    log.debug("webhook %s -> %s (%s in %sms)", event, webhook.url, status, latency_ms)


async def dispatch(event: str, payload: dict[str, Any]) -> None:
    """Fire an event to all matching webhooks (fire-and-forget)."""
    session = get_db_session()
    try:
        webhooks = _load_webhooks(session)
        # Also record notifications (ntfy etc.) without blocking.
        targets = [w for w in webhooks if not w.events or event in w.events]
    finally:
        session.close()

    if not targets:
        return
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(_deliver(client, w, event, payload) for w in targets))


def list_event_types() -> list[str]:
    return list(ALL_EVENTS)
