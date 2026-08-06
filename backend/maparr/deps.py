"""FastAPI dependencies: database session, current user, RBAC, API keys."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import security
from .db import get_session
from .models import ApiKey, User

bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> User:
    """Resolve the authenticated user from a JWT bearer token or API key."""
    token = None
    if credentials is not None:
        token = credentials.credentials
    elif request.query_params.get("token"):
        token = request.query_params.get("token")

    if not token:
        raise _unauthorized()

    # API keys look like maparr_<random>; JWT is opaque base64url.
    if token.startswith("maparr_"):
        user = _user_from_api_key(session, token)
        if user is None:
            raise _unauthorized("Invalid API key")
        return user

    try:
        payload = security.decode_token(token, security.ACCESS)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token")

    user = session.get(User, payload.get("sub"))
    if user is None:
        raise _unauthorized("User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")
    return user


def _user_from_api_key(session: Session, token: str) -> User | None:
    key_hash = security.hash_api_key(token)
    api_key = session.query(ApiKey).filter(ApiKey.token_hash == key_hash).first()
    if api_key is None:
        return None
    user = session.get(User, api_key.user_id)
    if user is None or not user.is_active:
        return None
    api_key.last_used_at = session.bind.dialect  # noop to keep linters quiet
    from datetime import datetime, timezone

    api_key.last_used_at = datetime.now(timezone.utc)
    session.commit()
    return user


UserDep = Annotated[User, Depends(get_current_user)]


def require_admin(user: UserDep) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required")
    return user


AdminDep = Annotated[User, Depends(require_admin)]


def require_active(user: UserDep) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")
    return user
