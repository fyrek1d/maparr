"""User management (admin-only) and API keys."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import security
from ..deps import AdminDep, SessionDep, UserDep
from ..models import ApiKey, User
from ..schemas import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyOut,
    UserCreate,
    UserOut,
    UserUpdate,
)
from ..services.webhooks import dispatch

router = APIRouter(prefix="/api/users", tags=["users"])


def _trigger(event: str, payload: dict) -> None:
    import asyncio

    async def _fire():
        await dispatch(event, payload)

    asyncio.ensure_future(_fire())


@router.get("", response_model=list[UserOut])
def list_users(session: SessionDep, admin: AdminDep):
    return session.query(User).order_by(User.created_at).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, session: SessionDep, admin: AdminDep):
    if session.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=payload.username, email=payload.email, role=payload.role,
                password_hash=security.hash_password(payload.password), provider="local")
    session.add(user)
    session.commit()
    session.refresh(user)
    _trigger("user.created", {"user_id": user.id, "username": user.username})
    return user


@router.get("/me", response_model=UserOut)
def me(user: UserDep):
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, session: SessionDep, admin: AdminDep):
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None:
        user.role = payload.role
    if payload.email is not None:
        user.email = payload.email
    if payload.password is not None:
        user.password_hash = security.hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    session.commit()
    session.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, session: SessionDep, admin: AdminDep):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return None


# --- API keys ---------------------------------------------------------------

@router.get("/me/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(session: SessionDep, user: UserDep):
    return session.query(ApiKey).filter(ApiKey.user_id == user.id).all()


@router.post("/me/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(payload: ApiKeyCreate, session: SessionDep, user: UserDep):
    from ..config import get_settings

    settings = get_settings()
    count = session.query(ApiKey).filter(ApiKey.user_id == user.id).count()
    if count >= settings.max_api_keys_per_user:
        raise HTTPException(status_code=400, detail="Too many API keys")
    token = security.generate_api_key()
    key = ApiKey(user_id=user.id, name=payload.name, scopes=payload.scopes,
                 token_hash=security.hash_api_key(token))
    session.add(key)
    session.commit()
    session.refresh(key)
    return ApiKeyCreated(**ApiKeyOut.model_validate(key).model_dump(), token=token)


@router.delete("/me/api-keys/{key_id}", status_code=204)
def delete_api_key(key_id: str, session: SessionDep, user: UserDep):
    key = session.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    session.delete(key)
    session.commit()
    return None
