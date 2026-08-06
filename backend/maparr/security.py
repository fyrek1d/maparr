"""Password hashing, JWT tokens and API-key handling."""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from typing import Any

import bcrypt
import jwt

from .config import get_settings

ACCESS = "access"
REFRESH = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _now() -> int:
    return int(dt.datetime.now(dt.UTC).timestamp())


def create_token(user_id: str, token_type: str = ACCESS, extra: dict | None = None) -> str:
    settings = get_settings()
    if token_type == REFRESH:
        lifetime = dt.timedelta(days=settings.refresh_token_days)
    else:
        lifetime = dt.timedelta(minutes=settings.access_token_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": token_type,
        "iat": _now(),
        "exp": _now() + int(lifetime.total_seconds()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected token type {expected_type}")
    return payload


def make_token_pair(user_id: str, role: str) -> dict[str, str]:
    return {
        "access_token": create_token(user_id, ACCESS, {"role": role}),
        "refresh_token": create_token(user_id, REFRESH),
        "token_type": "bearer",
        "expires_in": get_settings().access_token_minutes * 60,
    }


def hash_api_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"maparr_{secrets.token_urlsafe(32)}"


def constant_time_compare(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)
