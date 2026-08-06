"""Authentication endpoints: local login, refresh, OIDC, LDAP."""

from __future__ import annotations

import datetime as dt

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import or_

from .. import security
from ..config import get_settings
from ..deps import SessionDep, UserDep
from ..models import User
from ..schemas import (
    ChangePassword,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from ..services.auth_backends import get_oidc, ldap_authenticate, ldap_default_role
from ..services.logging import log
from ..settings_store import get_ldap_config, get_oidc_providers

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, session: SessionDep, response: Response):
    user = session.query(User).filter(
        or_(User.username == payload.username, User.email == payload.username)
    ).first()

    if user is not None and user.provider in ("local", ""):
        if not security.verify_password(payload.password, user.password_hash):
            user = None
    elif user is None and _ldap_available():
        info = ldap_authenticate(get_ldap_config(session), payload.username, payload.password)
        if info:
            user = session.query(User).filter(User.provider == "ldap",
                                             User.provider_sub == payload.username).first()
            if user is None:
                user = User(username=payload.username, email=info.get("email", ""),
                            provider="ldap", provider_sub=payload.username,
                            role=ldap_default_role(get_ldap_config(session)),
                            password_hash="")
                session.add(user)
                session.commit()
                session.refresh(user)
        else:
            user = None

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.last_login_at = dt.datetime.now(dt.UTC)
    session.commit()
    _maybe_set_cookie(response, security.make_token_pair(user.id, user.role))
    return _token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, response: Response, session: SessionDep):
    try:
        claims = security.decode_token(payload.refresh_token, security.REFRESH)
    except pyjwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid refresh token") from exc
    user = session.get(User, claims.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    pair = security.make_token_pair(user.id, user.role)
    _maybe_set_cookie(response, pair)
    return _token_response(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("maparr_access", path="/")
    response.delete_cookie("maparr_refresh", path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: UserDep):
    return user


@router.post("/change-password")
def change_password(payload: ChangePassword, user: UserDep, session: SessionDep):
    if user.provider not in ("local", ""):
        raise HTTPException(status_code=400, detail="Password is managed by an external provider")
    if not security.verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = security.hash_password(payload.new_password)
    session.commit()
    return {"ok": True}


@router.get("/oidc/providers")
def oidc_providers(session: SessionDep):
    return get_oidc().providers(get_oidc_providers(session))


@router.get("/oidc/login/{provider_id}")
async def oidc_login(provider_id: str, request: Request, session: SessionDep):
    cfg = get_oidc_providers(session)
    try:
        url = await get_oidc().build_login_url(cfg, provider_id, _base_url(request))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown OIDC provider") from exc
    return {"redirect_url": url}


@router.get("/oidc/callback")
async def oidc_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    session: SessionDep = None,
    response: Response = None,
):
    try:
        info = await get_oidc().exchange(get_oidc_providers(session), code, state, _base_url(request))
    except (ValueError, Exception) as exc:  # noqa: BLE001
        log.warning("oidc callback failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"OIDC authentication failed: {exc}") from exc

    user = session.query(User).filter(User.provider == "oidc",
                                      User.provider_sub == info["sub"]).first()
    if user is None:
        # Try to match on email, otherwise create.
        user = None
        if info.get("email"):
            user = session.query(User).filter(User.email == info["email"]).first()
        if user is None:
            user = User(username=info["username"], email=info.get("email", ""),
                        provider="oidc", provider_sub=info["sub"], password_hash="")
            session.add(user)
            session.commit()
            session.refresh(user)
    user.last_login_at = dt.datetime.now(dt.UTC)
    session.commit()
    pair = security.make_token_pair(user.id, user.role)
    _maybe_set_cookie(response, pair)
    return _token_response(user)


def _ldap_available() -> bool:
    settings = get_settings()
    return settings.ldap.enabled or True  # config stored in DB may enable it


def _token_response(user: User) -> dict:
    return security.make_token_pair(user.id, user.role)


def _maybe_set_cookie(response: Response, pair: dict) -> None:
    settings = get_settings()
    response.set_cookie("maparr_access", pair["access_token"], httponly=True,
                        secure=settings.cookie_secure, samesite="lax",
                        max_age=pair["expires_in"])
    response.set_cookie("maparr_refresh", pair["refresh_token"], httponly=True,
                        secure=settings.cookie_secure, samesite="lax",
                        max_age=get_settings().refresh_token_days * 86400)


def _base_url(request: Request) -> str:
    settings = get_settings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")
