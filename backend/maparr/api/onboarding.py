"""Onboarding and initial setup."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import security
from ..deps import AdminDep, SessionDep
from ..models import User
from ..schemas import OnboardingCreateAdmin, OnboardingStatus

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatus)
def status(session: SessionDep = None, admin: AdminDep = None):
    users_exist = session.query(User).count() > 0
    setup_complete = users_exist
    next_steps = []
    if not users_exist:
        next_steps.append("Create an administrator account")
    if not setup_complete:
        next_steps.append("Configure providers and storage paths")
    return OnboardingStatus(
        setup_complete=setup_complete,
        users_exist=users_exist,
        settings_configured=True,
        next_steps=next_steps,
    )


@router.post("/admin", response_model=OnboardingStatus, status_code=201)
def create_admin(payload: OnboardingCreateAdmin, session: SessionDep = None, admin: AdminDep = None):
    if session.query(User).count() > 0:
        raise HTTPException(status_code=400, detail="Admin already exists")
    user = User(
        username=payload.username,
        email=payload.email,
        role="admin",
        password_hash=security.hash_password(payload.password),
        provider="local",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return status(session, admin)