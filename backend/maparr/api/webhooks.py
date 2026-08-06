"""Webhook subscription management."""

from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, HTTPException

from ..deps import AdminDep, SessionDep
from ..models import Webhook
from ..schemas import WebhookCreate, WebhookOut, WebhookTestResult, WebhookUpdate
from ..services.webhooks import list_event_types

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("/events")
def events(admin: AdminDep):
    return list_event_types()


@router.get("", response_model=list[WebhookOut])
def list_webhooks(session: SessionDep, admin: AdminDep):
    return session.query(Webhook).order_by(Webhook.created_at.desc()).all()


@router.post("", response_model=WebhookOut, status_code=201)
def create_webhook(payload: WebhookCreate, session: SessionDep, admin: AdminDep):
    wh = Webhook(**payload.model_dump())
    session.add(wh)
    session.commit()
    session.refresh(wh)
    return wh


@router.patch("/{webhook_id}", response_model=WebhookOut)
def update_webhook(webhook_id: str, payload: WebhookUpdate, session: SessionDep, admin: AdminDep):
    wh = session.get(Webhook, webhook_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(wh, field, value)
    session.commit()
    session.refresh(wh)
    return wh


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(webhook_id: str, session: SessionDep, admin: AdminDep):
    wh = session.get(Webhook, webhook_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    session.delete(wh)
    session.commit()
    return None


@router.post("/{webhook_id}/test", response_model=WebhookTestResult)
async def test_webhook(webhook_id: str, session: SessionDep, admin: AdminDep):
    wh = session.get(Webhook, webhook_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(wh.url, json={"event": "webhook.test", "data": {"ok": True}})
            status = resp.status_code
            ok = status < 400
            message = "delivered"
    except httpx.HTTPError as exc:
        status, ok, message = 0, False, str(exc)
    latency_ms = int((time.monotonic() - started) * 1000)
    return WebhookTestResult(status=status, ok=ok, latency_ms=latency_ms, message=message)
