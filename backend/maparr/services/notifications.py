"""Optional outbound notifications (ntfy.sh and generic webhook)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..config import get_settings
from ..settings_store import get_notify_config
from .logging import log

LEVELS = {"info": "info", "warn": "warning", "error": "error"}


async def notify(title: str, message: str, level: str = "info", session=None) -> None:
    """Send a notification through configured channels (best effort)."""
    cfg = get_notify_config(session) if session else get_notify_config()
    env = get_settings().notifications
    tasks = []

    ntfy_url = cfg.get("ntfy_url") or env.ntfy_url
    ntfy_topic = cfg.get("ntfy_topic") or env.ntfy_topic
    ntfy_token = cfg.get("ntfy_token") or env.ntfy_token
    if ntfy_url and ntfy_topic:
        tasks.append(_ntfy(ntfy_url, ntfy_topic, ntfy_token, title, message, level))

    webhook_url = cfg.get("webhook_url") or env.webhook_url
    if webhook_url:
        tasks.append(_generic(webhook_url, title, message, level))

    if tasks:
        await asyncio.gather(*(t for t in tasks), return_exceptions=True)


async def _ntfy(url: str, topic: str, token: str, title: str, message: str, level: str) -> None:
    target = url.rstrip("/") + "/" + topic
    headers = {"Title": title, "Priority": {"error": "high", "warn": "default", "info": "default"}[level]}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(target, content=message, headers=headers, timeout=10.0)
            log.debug("notification ntfy -> %s (%s)", target, resp.status_code)
    except httpx.HTTPError as exc:
        log.warning("notification ntfy failed: %s", exc)


async def _generic(url: str, title: str, message: str, level: str) -> None:
    payload: dict[str, Any] = {"title": title, "message": message, "level": level}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            log.debug("notification webhook -> %s (%s)", url, resp.status_code)
    except httpx.HTTPError as exc:
        log.warning("notification webhook failed: %s", exc)
